import sys
import os
from typing import Optional, List
import typer
import click

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

from ace import __version__
from ace.ui.display import (
    console,
    print_info,
    print_success,
    print_warning,
    show_error_panel,
    show_warning_panel,
    show_commit_message,
    spinner,
)

from typer.core import TyperGroup

class NaturalLanguageGroup(TyperGroup):
    def parse_args(self, ctx, args):
        subcommand_names = list(self.commands.keys())
        
        # Check if any argument matches a registered subcommand name
        has_subcommand = False
        for arg in args:
            if not arg.startswith("-"):
                if arg in subcommand_names:
                    has_subcommand = True
                break
                
        if not has_subcommand and args:
            # Separate option flags from query arguments
            option_flags = [arg for arg in args if arg.startswith("-")]
            query_args = [arg for arg in args if not arg.startswith("-")]
            
            # Let Click parse only the option flags for the main group
            res = super().parse_args(ctx, option_flags)
            # Store the query arguments in ctx.args for the main callback to consume
            ctx.args = query_args
            return res
            
        return super().parse_args(ctx, args)



app = typer.Typer(
    name="ace",
    help="Ace — AI-Powered Git Copilot. Talk to Git in plain English.",
    no_args_is_help=False,
    cls=NaturalLanguageGroup,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)




def version_callback(value: bool):
    if value:
        console.print(f"Ace version: [bold cyan]{__version__}[/bold cyan]")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show what would be done, don't execute"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed AI reasoning"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Show the version and exit."
    ),
):
    try:
        from ace.utils.update_checker import check_for_updates
        check_for_updates()
    except Exception:
        pass

    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.intent_parser import IntentParser
    from ace.ai.llm_factory import get_llm, LLMConfigurationError
    from ace.core.safety import SafetyChecker
    from ace.ui.prompts import confirm
    # Intercept subcommand if the user typed an English sentence (e.g. 'ace add and commit')
    intercepted_query = None
    ALL_INTERCEPT_SUBCOMMANDS = (
        "add", "stage", "commit", "review", "explain", "resolve", "search",
        "undo", "workspace", "ws", "standup", "blame", "pr", "squash", "ignore", "doctor"
    )
    if ctx.invoked_subcommand in ALL_INTERCEPT_SUBCOMMANDS:
        import sys
        sub_cmd = ctx.invoked_subcommand
        sub_idx = -1
        for idx, arg in enumerate(sys.argv[1:], start=1):
            if arg == sub_cmd:
                sub_idx = idx
                break
        if sub_idx != -1:
            sub_args = sys.argv[sub_idx + 1:]
            # Do NOT intercept if flag arguments like -m, --message, -b, etc. are passed directly to the subcommand
            has_message_flag = any(a in ("-m", "--message", "-b", "--branch") for a in sys.argv)
            nl_indicators = {
                "and", "then", "with", "also"
            }
            # Only intercept if explicit multi-action conjunctions are present and message flags are absent
            if not has_message_flag and any(arg.lower() in nl_indicators for arg in sub_args):
                query_parts = []
                for arg in sys.argv[1:]:
                    if arg.startswith("-"):
                        continue
                    query_parts.append(arg)
                intercepted_query = " ".join(query_parts)


    if intercepted_query:
        query = intercepted_query
    elif ctx.invoked_subcommand is not None:
        from ace.core.config import get_config
        config = get_config()
        if ctx.invoked_subcommand in config.aliases and ctx.invoked_subcommand != "alias":
            _execute_alias(ctx.invoked_subcommand, config.aliases[ctx.invoked_subcommand])
            raise typer.Exit(code=0)
        return
    else:
        if not ctx.args:
            # No query and no subcommand, Typer will show help
            console.print(ctx.get_help())
            raise typer.Exit()

        first_arg = ctx.args[0].lower().strip()
        from ace.core.config import get_config
        config = get_config()
        if first_arg in config.aliases and first_arg != "alias":
            _execute_alias(first_arg, config.aliases[first_arg])
            raise typer.Exit(code=0)

        query = " ".join(ctx.args)

    # ------------------------------------------------------------------
    # Natural Language Command Execution Loop
    # ------------------------------------------------------------------
    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    # Initialize parser
    parser = IntentParser(git_ops)

    try:
        with spinner("Analyzing request..."):
            parsed = parser.parse_intent(query, offline=offline)
    except Exception as e:
        show_error_panel(f"Failed to parse request: {e}", "AI Error")
        raise typer.Exit(code=1)

    commands = parsed.get("commands", [])
    explanation = parsed.get("explanation", "")
    risk_level = parsed.get("risk_level", "safe")

    if not commands:
        print_warning("No Git commands planned.")
        show_warning_panel(f"No actionable Git commands generated for: '{query}'\n{explanation}", "Empty Plan")
        return

    # Display plan to user
    from ace.ui.display import show_plan
    show_plan(commands, [explanation] + [""] * (len(commands) - 1))

    if dry_run:
        print_info("Dry-run mode: execution skipped.")
        return

    # Evaluate safety for the full plan
    execute_plan = True
    highest_risk = risk_level
    risk_descriptions = []

    for cmd in commands:
        r_level, r_desc, _ = SafetyChecker.analyze_command(cmd)
        if r_level == "destructive":
            highest_risk = "destructive"
            risk_descriptions.append(f"[bold]{cmd}[/bold]\n{r_desc}")
        elif r_level == "moderate" and highest_risk != "destructive":
            highest_risk = "moderate"

    from ace.core.config import get_config
    config = get_config()

    if highest_risk == "destructive" and config.safety.confirm_destructive and not yes:
        desc_text = "\n\n".join(risk_descriptions)
        show_warning_panel(f"The plan contains destructive operations:\n\n{desc_text}", "Destructive Operation Warning")
        execute_plan = confirm("Are you sure you want to execute these commands?", default=False)
    elif not yes:
        execute_plan = confirm("Execute plan?", default=True)

    if not execute_plan:
        print_info("Execution aborted.")
        return

    # Execute commands and capture output
    outputs = []
    for cmd in commands:
        print_info(f"Executing: {cmd}")
        if cmd.startswith("ace "):
            subcmd = cmd[4:].strip()
            if subcmd == "commit":
                try:
                    commit_cmd(offline=offline)
                    outputs.append("Smart commit executed successfully.")
                except Exception as e:
                    show_error_panel(f"Failed to run smart commit: {e}", "Ace Error")
                    raise typer.Exit(code=1)
            elif subcmd.startswith("review"):
                try:
                    review_cmd(all_changes=True, offline=offline)
                    outputs.append("Code review completed.")
                except Exception as e:
                    show_error_panel(f"Failed to run code review: {e}", "Ace Error")
                    raise typer.Exit(code=1)
            else:
                try:
                    import subprocess
                    import sys
                    import shlex
                    args = shlex.split(cmd)[1:]
                    res_proc = subprocess.run(
                        [sys.executable, "-m", "ace"] + args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8"
                    )
                    if res_proc.returncode != 0:
                        raise Exception(res_proc.stderr or res_proc.stdout)
                    outputs.append(res_proc.stdout)
                except Exception as e:
                    show_error_panel(f"Failed to execute command '{cmd}': {e}", "Execution Error")
                    raise typer.Exit(code=1)
        else:
            git_args = cmd[4:] if cmd.startswith("git ") else cmd
            try:
                res = git_ops.execute(git_args)
                outputs.append(res)
            except Exception as e:
                show_error_panel(f"Failed to execute command '{cmd}': {e}", "Execution Error")
                raise typer.Exit(code=1)

    # Summarization flow for read-only history queries
    combined_output = "\n".join(outputs)
    if highest_risk == "safe" and combined_output.strip() and not any(c.startswith("ace ") for c in commands):
        from ace.ai.history_analyzer import HistoryAnalyzer
        from rich.markdown import Markdown
        analyzer = HistoryAnalyzer(git_ops)
        
        try:
            with spinner("Analyzing result and summarizing..."):
                summary = analyzer.summarize_query(query, commands[0], combined_output, offline=offline)
            console.print()
            console.print(Markdown(summary))
            console.print()
        except Exception:
            # Fallback to printing raw output
            console.print(combined_output)
    else:
        # Just print raw outputs for moderate/destructive actions
        for out in outputs:
            if out.strip():
                console.print(out)
                
    print_success("Plan executed successfully!")
    raise typer.Exit(code=0)

@app.command(name="commit", help="Generate a smart commit message from staged changes and commit.")
def commit_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
    format_override: Optional[str] = typer.Option(
        None, "--format", "-f", help="Override commit format (conventional, simple, detailed)"
    ),
    prepare: Optional[str] = typer.Option(None, "--prepare", help="Path to commit message template file (hook mode)"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.core.config import get_config
    from ace.ai.commit_generator import CommitGenerator, NoStagedChangesError
    from ace.ai.llm_factory import get_llm, LLMConfigurationError
    from ace.ui.prompts import confirm, prompt_action

    if not isinstance(format_override, str):
        format_override = None
    if not isinstance(prepare, str):
        prepare = None
    if not isinstance(offline, bool):
        offline = False

    # Initialize GitOps
    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    config = get_config()
    format_type = format_override or config.commit.format

    # Stage checking and generation
    generator = CommitGenerator(git_ops)
    
    if prepare:
        try:
            get_llm(offline_override=offline)
            msg = generator.generate_message(format_type=format_type, offline=offline)
            with open(prepare, "w", encoding="utf-8") as f:
                f.write(msg)
            raise typer.Exit(code=0)
        except (typer.Exit, typer.Abort):
            raise
        except NoStagedChangesError:
            raise typer.Exit(code=0)
        except Exception as e:
            show_error_panel(f"Hook failed to generate commit message: {e}", "Ace Hook Error")
            raise typer.Exit(code=1)
            
    msg = None
    
    while True:
        if not msg:
            try:
                get_llm(offline_override=offline)
                with spinner("Analyzing changes and generating commit message..."):
                    msg = generator.generate_message(format_type=format_type, offline=offline)
            except NoStagedChangesError as e:
                staged_files = []
                try:
                    staged_files = git_ops.get_status().get("staged", [])
                except Exception:
                    pass

                if staged_files:
                    show_warning_panel(
                        f"{str(e)}\n\n[bold]Tip:[/bold] Use [command]git commit -m \"message\"[/command] to commit these changes manually, or add content to the files.",
                        "Empty Staged Diff"
                    )
                else:
                    show_warning_panel(
                        f"{str(e)}\n\n[bold]Tip:[/bold] Stage your files first: [command]git add <files>[/command]",
                        "No Staged Changes"
                    )
                raise typer.Exit(code=0)
            except LLMConfigurationError as e:
                show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
                raise typer.Exit(code=1)
            except Exception as e:
                show_error_panel(f"Failed to generate commit message: {e}", "AI Error")
                raise typer.Exit(code=1)

        show_commit_message(msg)

        # Prompt user for action
        options = {
            "\r": ("Accept & Commit", "Use this message and commit"),
            "e": ("Edit", "Open message in editor"),
            "r": ("Regenerate", "Generate a new message"),
            "c": ("Switch format", "Switch to conventional/simple/detailed"),
            "s": ("Skip", "Abort commit process"),
        }
        
        choice = prompt_action(options, default_key="\r")
        
        if choice == "\r":
            # Commit changes
            try:
                result = git_ops.commit(msg, sign=config.commit.sign)
                print_success("Committed changes successfully!")
                console.print(f"[dim]{result}[/dim]")
                break
            except Exception as e:
                show_error_panel(f"Failed to commit: {e}", "Git Commit Error")
                raise typer.Exit(code=1)
                
        elif choice == "e":
            # Edit in editor
            edited = click.edit(msg)
            if edited is not None and edited.strip():
                msg = edited.strip()
            else:
                print_info("No edits made or empty message. Keeping previous message.")
                
        elif choice == "r":
            # Force regeneration on next iteration
            msg = None
            
        elif choice == "c":
            # Switch format
            console.print("\n[bold]Select commit format:[/bold]")
            console.print("  [1] Conventional Commits (default)")
            console.print("  [2] Simple (one-liner)")
            console.print("  [3] Detailed (multi-paragraph)")
            
            format_choice = typer.prompt("Choose option", default="1")
            if format_choice == "1":
                format_type = "conventional"
            elif format_choice == "2":
                format_type = "simple"
            elif format_choice == "3":
                format_type = "detailed"
            msg = None  # Force regenerate in new format
            
        elif choice == "s":
            console.print("[yellow]Commit aborted.[/yellow]")
            raise typer.Exit(code=0)

    # Post commit flow: Pushing
    # Detect remote tracking branch
    upstream = git_ops.get_upstream_tracking()
    current_branch = git_ops.get_current_branch()
    
    if not current_branch:
        # Detached HEAD, don't ask to push
        return

    remotes = git_ops.get_remotes()
    if not remotes:
        print_info("No remotes configured. Skipping push.")
        return

    # Check ahead/behind if tracking remote exists
    ab = git_ops.get_ahead_behind()
    ahead = ab.get("ahead", 0)
    
    # If we just committed, we are at least 1 commit ahead (or more if local commits were unpushed)
    if not upstream:
        # Resolve remote to use
        selected_remote = remotes[0]
        if len(remotes) > 1:
            default_rem = "origin" if "origin" in remotes else remotes[0]
            console.print("\n[bold]Select remote to push to:[/bold]")
            for idx, rem in enumerate(remotes, 1):
                console.print(f"  [{idx}] {rem}")
            choice_idx = typer.prompt("Choose option", default="1")
            try:
                choice_num = int(choice_idx) - 1
                if 0 <= choice_num < len(remotes):
                    selected_remote = remotes[choice_num]
                else:
                    selected_remote = default_rem
            except ValueError:
                selected_remote = default_rem

        # Prompt to set upstream
        if confirm(f"No upstream remote branch set for '{current_branch}'. Push and set upstream to '{selected_remote}/{current_branch}'?", default=True):
            try:
                with spinner(f"Pushing '{current_branch}' to {selected_remote} and setting upstream..."):
                    push_res = git_ops.push(remote=selected_remote, branch=current_branch, set_upstream=True)
                print_success("Pushed and set upstream branch successfully!")
                console.print(f"[dim]{push_res}[/dim]")
            except Exception as e:
                from ace.ai.push_resolver import handle_push_failure
                handle_push_failure(git_ops, str(e), remote=selected_remote, branch=current_branch, offline=offline)
    else:
        # Upstream exists
        msg_push = f"Push to upstream branch '{upstream}'? (Your branch is {ahead} commit(s) ahead of remote)"
        if confirm(msg_push, default=True):
            remote_name = upstream.split("/")[0] if "/" in upstream else "origin"
            try:
                with spinner(f"Pushing to {upstream}..."):
                    push_res = git_ops.push(remote=remote_name)
                print_success("Pushed to remote successfully!")
                console.print(f"[dim]{push_res}[/dim]")
            except Exception as e:
                from ace.ai.push_resolver import handle_push_failure
                handle_push_failure(git_ops, str(e), remote=remote_name, branch=current_branch, offline=offline)


@app.command(name="setup", help="Initial configuration wizard for Ace.")
def setup_cmd():
    import click
    from ace.ui.banner import animate_fire_banner
    from ace.core.config import get_config, save_config, DEFAULT_CONFIG_PATH
    from ace.ui.prompts import confirm
    
    click.clear()
    try:
        animate_fire_banner(duration_seconds=1.2)
    except Exception:
        pass
        
    console.print("[bold orange3]Welcome to Ace AI Git Copilot Setup![/bold orange3] 🚀\n")
    console.print("Configure your preferences and AI provider step-by-step.\n")
    
    config = get_config()

    # Provider select
    console.print("[bold]Select your AI Provider:[/bold]")
    console.print("  [bold cyan]1[/bold cyan] -> NVIDIA API Endpoints (Cloud)")
    console.print("  [bold cyan]2[/bold cyan] -> Ollama (Local Models)")
    console.print("  [bold cyan]3[/bold cyan] -> OpenAI (GPT-4o, etc.)")
    console.print("  [bold cyan]4[/bold cyan] -> Anthropic (Claude)")
    console.print("  [bold cyan]5[/bold cyan] -> Custom OpenAI-Compatible (Groq, OpenRouter, etc.)")
    console.print("")

    provider_map = {
        "1": "nvidia",
        "2": "ollama",
        "3": "openai",
        "4": "anthropic",
        "5": "custom",
    }
    provider_reverse_map = {v: k for k, v in provider_map.items()}
    default_choice = provider_reverse_map.get(config.ai.provider, "1")

    choice = typer.prompt("Enter choice (1-5)", default=default_choice)
    choice_clean = choice.strip().lower()

    if choice_clean in provider_map:
        provider = provider_map[choice_clean]
    elif choice_clean in provider_reverse_map:
        provider = choice_clean
    else:
        print_warning("Invalid choice. Defaulting to NVIDIA.")
        provider = "nvidia"
        
    config.ai.provider = provider
    console.print(f"Selected Provider: [bold cyan]{provider.upper()}[/bold cyan]\n")
    
    # NVIDIA setup
    if provider == "nvidia":
        nvidia_key = typer.prompt("Enter your NVIDIA API Key", default=config.ai.nvidia_api_key, hide_input=True)
        config.ai.nvidia_api_key = nvidia_key
        nvidia_model = typer.prompt("NVIDIA LLM Model name", default=config.ai.nvidia_model)
        config.ai.nvidia_model = nvidia_model
        
    # Ollama setup
    elif provider == "ollama":
        ollama_url = typer.prompt("Ollama server URL", default=config.ai.ollama_url)
        config.ai.ollama_url = ollama_url
        ollama_model = typer.prompt("Ollama model name", default=config.ai.ollama_model)
        config.ai.ollama_model = ollama_model

    # OpenAI setup
    elif provider == "openai":
        openai_key = typer.prompt("Enter your OpenAI API Key", default=config.ai.openai_api_key, hide_input=True)
        config.ai.openai_api_key = openai_key
        openai_model = typer.prompt("OpenAI LLM Model name", default=config.ai.openai_model)
        config.ai.openai_model = openai_model

    # Anthropic setup
    elif provider == "anthropic":
        anthropic_key = typer.prompt("Enter your Anthropic API Key", default=config.ai.anthropic_api_key, hide_input=True)
        config.ai.anthropic_api_key = anthropic_key
        anthropic_model = typer.prompt("Anthropic LLM Model name", default=config.ai.anthropic_model)
        config.ai.anthropic_model = anthropic_model

    # Custom setup
    elif provider == "custom":
        custom_base = typer.prompt("Custom API Base URL (e.g., https://api.groq.com/openai/v1)", default=config.ai.custom_api_base)
        config.ai.custom_api_base = custom_base
        custom_key = typer.prompt("Enter your Custom API Key", default=config.ai.custom_api_key, hide_input=True)
        config.ai.custom_api_key = custom_key
        custom_model = typer.prompt("Custom LLM Model name", default=config.ai.custom_model)
        config.ai.custom_model = custom_model
        
    console.print("\n[bold]Select Output Language:[/bold]")
    console.print("  [bold cyan]1[/bold cyan] -> English (Default)")
    console.print("  [bold cyan]2[/bold cyan] -> Simplified Chinese (简体中文)")
    console.print("  [bold cyan]3[/bold cyan] -> Traditional Chinese (繁體中文)")
    console.print("  [bold cyan]4[/bold cyan] -> Spanish (Español)")
    console.print("  [bold cyan]5[/bold cyan] -> French (Français)")
    console.print("  [bold cyan]6[/bold cyan] -> German (Deutsch)")
    console.print("  [bold cyan]7[/bold cyan] -> Japanese (日本語)")
    console.print("  [bold cyan]8[/bold cyan] -> Custom ISO Language Code (e.g. hi, ru, ko)")
    console.print("")

    lang_map = {
        "1": "en",
        "2": "zh-CN",
        "3": "zh-TW",
        "4": "es",
        "5": "fr",
        "6": "de",
        "7": "ja",
    }
    lang_choice = typer.prompt("Enter language choice (1-8)", default="1")
    if lang_choice.strip() in lang_map:
        config.ai.language = lang_map[lang_choice.strip()]
    elif lang_choice.strip() == "8":
        custom_lang = typer.prompt("Enter ISO language code (e.g., hi, ru, ko)", default="en")
        config.ai.language = custom_lang.strip()
    else:
        config.ai.language = lang_choice.strip()

    console.print("\n[bold]Configure Commit Preferences:[/bold]")
    # Commit pref setup
    commit_format = typer.prompt("Default commit format (conventional, simple, detailed)", default=config.commit.format)
    if commit_format.lower().strip() in ("conventional", "simple", "detailed"):
        config.commit.format = commit_format.lower().strip()
        
    sign_commits = confirm("Should Ace sign commits by default (GPG/SSH)?", default=config.commit.sign)
    config.commit.sign = sign_commits

    use_emoji = confirm("Should Ace use emojis in commit messages by default?", default=config.commit.emoji)
    config.commit.emoji = use_emoji
    
    # Save config
    try:
        save_config(config)
        print_success(f"Configuration saved successfully to {DEFAULT_CONFIG_PATH}")
    except Exception as e:
        show_error_panel(str(e), "Save Configuration Error")

@app.command(name="config", help="View the current active configuration.")
def config_cmd():
    from ace.core.config import get_config, DEFAULT_CONFIG_PATH
    from ace.utils.i18n import get_language_name
    from rich.table import Table

    config = get_config()
    
    table = Table(title="Ace Active Configuration", show_header=True, header_style="bold orange3")
    table.add_column("Section")
    table.add_column("Setting")
    table.add_column("Value")
    
    # Mask API key helper
    def mask_key(k: str) -> str:
        return k[:8] + "..." if k else "Not set"
    
    # Add items
    table.add_row("AI", "Provider", config.ai.provider)
    lang_code = getattr(config.ai, "language", "en")
    table.add_row("AI", "Output Language", f"{lang_code} ({get_language_name(lang_code)})")
    table.add_row("AI", "NVIDIA API Key", mask_key(config.ai.nvidia_api_key))
    table.add_row("AI", "NVIDIA Model", config.ai.nvidia_model)
    table.add_row("AI", "Ollama URL", config.ai.ollama_url)
    table.add_row("AI", "Ollama Model", config.ai.ollama_model)
    table.add_row("AI", "OpenAI API Key", mask_key(config.ai.openai_api_key))
    table.add_row("AI", "OpenAI Model", config.ai.openai_model)
    table.add_row("AI", "Anthropic API Key", mask_key(config.ai.anthropic_api_key))
    table.add_row("AI", "Anthropic Model", config.ai.anthropic_model)
    table.add_row("AI", "Custom API Base URL", config.ai.custom_api_base or "Not set")
    table.add_row("AI", "Custom API Key", mask_key(config.ai.custom_api_key))
    table.add_row("AI", "Custom Model", config.ai.custom_model or "Not set")
    
    table.add_row("Commit", "Default Format", config.commit.format)
    table.add_row("Commit", "Sign Commits", str(config.commit.sign))
    table.add_row("Commit", "Use Emoji", str(config.commit.emoji))
    
    table.add_row("Review", "Severity Threshold", config.review.severity)
    
    table.add_row("Safety", "Confirm Destructive", str(config.safety.confirm_destructive))
    table.add_row("Safety", "Auto Stash", str(config.safety.auto_stash))
    
    console.print(table)
    print_info(f"Config file located at: {DEFAULT_CONFIG_PATH}")

@app.command(name="review", help="AI code review of staged, unstaged, or branch changes.")
def review_cmd(
    file: Optional[str] = typer.Argument(None, help="Specific file to review"),
    all_changes: bool = typer.Option(False, "--all", "-a", help="Review all uncommitted changes (staged + unstaged)"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Review all changes against a base branch/commit"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
    strict: bool = typer.Option(False, "--strict", help="Fail with exit code 1 if critical issues are found"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm, LLMConfigurationError

    if not isinstance(file, str):
        file = None
    if not isinstance(all_changes, bool):
        all_changes = False
    if not isinstance(branch, str):
        branch = None
    if not isinstance(strict, bool):
        strict = False
    if not isinstance(offline, bool):
        offline = False

    # Initialize GitOps
    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    # Resolve diff contents
    diff_text = ""
    
    if file:
        # Review specific file (staged + unstaged)
        staged_f = git_ops.repo.git.diff("--staged", file)
        unstaged_f = git_ops.repo.git.diff(file)
        diff_text = staged_f + "\n" + unstaged_f
        desc = f"changes in file '{file}'"
    elif branch:
        # Review changes against base branch
        try:
            diff_text = git_ops.get_branch_diff(branch)
            desc = f"changes in current branch against '{branch}'"
        except Exception as e:
            show_error_panel(f"Failed to get branch diff against '{branch}': {e}", "Git Error")
            raise typer.Exit(code=1)
    elif all_changes:
        # Review staged + unstaged changes
        try:
            diff_text = git_ops.repo.git.diff("HEAD")
        except Exception:
            # Fallback if no commits exist
            diff_text = git_ops.repo.git.diff()
        desc = "all uncommitted changes (staged + unstaged)"
    else:
        # Default: review staged changes only
        diff_text = git_ops.get_staged_diff()
        desc = "staged changes"

    if not diff_text.strip():
        show_warning_panel(f"No changes detected to review for {desc}.", "Empty Diff")
        raise typer.Exit(code=0)

    # Run AI review
    from ace.ai.code_reviewer import CodeReviewer
    from ace.ui.display import show_review
    
    reviewer = CodeReviewer(git_ops)
    
    try:
        get_llm(offline_override=offline)
        with spinner(f"Analyzing {desc} and reviewing code..."):
            findings, score = reviewer.review_diff(diff_text, offline=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)
    except Exception as e:
        show_error_panel(f"Code review failed: {e}", "AI Error")
        raise typer.Exit(code=1)

    show_review(findings, score)
    
    if strict:
        critical_count = sum(1 for f in findings if f.get("severity", "info").lower() == "critical")
        if critical_count > 0:
            raise typer.Exit(code=1)

@app.command(name="resolve", help="AI-assisted merge conflict resolution.")
def resolve_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from ace.ui.prompts import confirm, prompt_action
    from rich.panel import Panel

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    conflicts = git_ops.get_conflicts()
    if not conflicts:
        print_success("No merge conflicts detected! Your workspace is clean.")
        raise typer.Exit(code=0)

    console.print(f"\n[bold yellow]🔀 Merge conflicts found in {len(conflicts)} file(s):[/bold yellow]")
    for f in conflicts:
        console.print(f"  - {f}")
    console.print()

    from ace.ai.conflict_resolver import ConflictResolver
    resolver = ConflictResolver(git_ops)

    for file_path in conflicts:
        console.print(f"\n[bold orange3]Resolving conflicts in: {file_path}[/bold orange3]")
        
        try:
            get_llm(offline_override=offline)
            with spinner(f"Analyzing conflicts in {file_path}..."):
                suggestions = resolver.get_suggestions(file_path, offline=offline)
        except Exception as e:
            show_error_panel(f"Failed to parse conflicts for {file_path}: {e}", "Error")
            continue

        if not suggestions:
            print_warning(f"No conflict markers found in {file_path}. Skipping.")
            continue

        replacements = []
        skip_file = False

        for idx, sugg in enumerate(suggestions, 1):
            console.print(f"\n[bold]Conflict {idx}/{len(suggestions)} in {file_path}:[/bold]")
            
            # Print HEAD
            console.print("[bold cyan]<<<<<<< HEAD (Your Changes)[/bold cyan]")
            console.print(sugg["head"])
            console.print("[bold cyan]=======[/bold cyan]")
            
            # Print Incoming
            console.print(sugg["incoming"])
            console.print("[bold cyan]>>>>>>> (Incoming Changes)[/bold cyan]\n")
            
            # Print AI suggestion
            console.print("[bold orange3]🧠 AI Suggestion:[/bold orange3] Keep incoming/HEAD or merged?")
            console.print(f"   [dim]{sugg['explanation']}[/dim]")
            console.print("\n[dim]Suggested Merged Content:[/dim]")
            console.print(Panel(sugg["suggested_merged"], border_style="dim"))
            console.print()

            options = {
                "\r": ("Accept AI suggestion", "Use the AI merged block"),
                "h": ("Keep HEAD", "Keep your local changes"),
                "i": ("Keep incoming", "Keep the incoming changes"),
                "m": ("Manual edit", "Open editor to customize merged block"),
                "s": ("Skip", "Leave this conflict block unresolved"),
            }
            
            choice = prompt_action(options, default_key="\r")
            
            if choice == "\r":
                replacements.append((sugg["full_block"], sugg["suggested_merged"]))
                print_success("AI suggestion accepted.")
            elif choice == "h":
                replacements.append((sugg["full_block"], sugg["head"]))
                print_success("Keeping HEAD changes.")
            elif choice == "i":
                replacements.append((sugg["full_block"], sugg["incoming"]))
                print_success("Keeping incoming changes.")
            elif choice == "m":
                edited = click.edit(sugg["suggested_merged"])
                if edited is not None:
                    replacements.append((sugg["full_block"], edited.strip()))
                    print_success("Applied manual edit.")
                else:
                    replacements.append((sugg["full_block"], sugg["suggested_merged"]))
                    print_warning("No edits made. Accepted AI suggestion.")
            elif choice == "s":
                print_warning("Conflict block skipped.")
                skip_file = True
                break

        if not skip_file and replacements:
            try:
                resolver.apply_resolution(file_path, replacements)
                print_success(f"Successfully resolved conflicts in {file_path}!")
                
                # Prompt to stage
                if confirm(f"Stage resolved file '{file_path}' (git add)?", default=True):
                    git_ops.execute(f"add {file_path}")
                    print_success(f"Staged {file_path}.")
            except Exception as e:
                show_error_panel(f"Failed to apply resolutions to {file_path}: {e}", "Error")

@app.command(name="changelog", help="Generate a markdown changelog from commits.")
def changelog_cmd(
    from_ref: Optional[str] = typer.Option(None, "--from", help="Starting tag or commit hash"),
    to_ref: Optional[str] = typer.Option(None, "--to", help="Ending tag or commit hash (defaults to HEAD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="File to write the generated changelog to"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm, LLMConfigurationError

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.ai.changelog_generator import ChangelogGenerator
    generator = ChangelogGenerator(git_ops)

    try:
        get_llm(offline_override=offline)
        with spinner("Analyzing commits and generating changelog..."):
            changelog_md = generator.generate_changelog(from_ref, to_ref, offline=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)
    except Exception as e:
        title = "Git Error" if "ChangelogGeneratorError" in str(type(e)) or "Cmd('git')" in str(e) or "Invalid starting revision" in str(e) or "Invalid ending revision" in str(e) else "AI Error"
        show_error_panel(f"Failed to generate changelog: {e}", title)
        raise typer.Exit(code=1)

    # Show or write to file
    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(changelog_md)
            print_success(f"Changelog successfully written to {output}!")
        except Exception as e:
            show_error_panel(f"Failed to write changelog to {output}: {e}", "File Error")
            raise typer.Exit(code=1)
    else:
        # Print to console
        from rich.markdown import Markdown
        console.print()
        console.print(Markdown(changelog_md))
        console.print()

@app.command(name="stats", help="Show contribution statistics and repository overview.")
def stats_cmd():
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from rich.table import Table
    from rich import box
    from rich.panel import Panel

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.ai.history_analyzer import HistoryAnalyzer
    analyzer = HistoryAnalyzer(git_ops)
    
    with spinner("Gathering repository statistics..."):
        stats = analyzer.get_repo_stats()

    if not stats:
        show_warning_panel("No commit history found to generate statistics.", "Empty Repository")
        raise typer.Exit(code=0)

    # 1. Overview Panels
    info_table = Table.grid(padding=1)
    info_table.add_column(style="bold cyan", justify="right")
    info_table.add_column()
    info_table.add_row("Total Commits:", f"[bold white]{stats['total_commits']}[/bold white]")
    info_table.add_row("Active Branches:", f"[bold white]{stats['total_branches']}[/bold white]")
    info_panel = Panel(info_table, title="[bold white]Repository Info[/bold white]", border_style="cyan", expand=False)

    changes_table = Table.grid(padding=1)
    changes_table.add_column(style="bold yellow", justify="right")
    changes_table.add_column()
    changes_table.add_row("Staged:", f"[bold green]{stats['staged_count']} files[/bold green]")
    changes_table.add_row("Unstaged:", f"[bold yellow]{stats['unstaged_count']} files[/bold yellow]")
    changes_table.add_row("Untracked:", f"[bold red]{stats['untracked_count']} files[/bold red]")
    changes_panel = Panel(changes_table, title="[bold white]Workspace Changes[/bold white]", border_style="yellow", expand=False)

    from rich.columns import Columns
    console.print(Columns([info_panel, changes_panel]))
    console.print()

    # 2. Contributors Table (Enhanced with Line changes)
    contrib_table = Table(title="Top Contributors", show_header=True, header_style="bold spring_green3", box=box.ROUNDED)
    contrib_table.add_column("Author", style="bold white")
    contrib_table.add_column("Commits", justify="right")
    contrib_table.add_column("Lines Added/Deleted", justify="center")
    contrib_table.add_column("Activity Bar", justify="left")

    total_commits = stats["total_commits"]
    lines_info = stats.get("lines_per_author", {})
    
    for author, count in stats["contributors"][:10]: # Top 10
        pct = (count / total_commits) * 100
        bar_len = int(pct / 5) # 20 blocks max
        
        # Color bar based on activity levels
        color = "spring_green3" if pct >= 50 else ("orange3" if pct >= 20 else "deep_sky_blue1")
        bar = f"[{color}]" + "█" * bar_len + f"[/{color}][grey37]" + "░" * (20 - bar_len) + "[/grey37]"
        
        la = lines_info.get(author, {"added": 0, "deleted": 0})
        lines_str = f"[green]+{la['added']}[/green]/[red]-{la['deleted']}[/red]"
        contrib_table.add_row(author, f"{count} ({pct:.1f}%)", lines_str, bar)

    console.print(contrib_table)
    console.print()

    # 3. File Extension Distribution Table
    ext_info = stats.get("extension_counts", {})
    if ext_info:
        ext_table = Table(title="File Extension Distribution (Top 5)", show_header=True, header_style="bold gold1", box=box.ROUNDED)
        ext_table.add_column("Extension", style="bold white")
        ext_table.add_column("Files Count", justify="right")
        ext_table.add_column("Percentage Bar")
        
        total_files = sum(ext_info.values())
        for ext, count in ext_info.items():
            pct = (count / total_files) * 100 if total_files else 0
            bar_len = int(pct / 5) # 20 blocks max
            bar = "[gold1]" + "█" * bar_len + "[/gold1][grey37]" + "░" * (20 - bar_len) + "[/grey37]"
            ext_table.add_row(ext, str(count), bar)
            
        console.print(ext_table)
        console.print()

    # 4. Activity Timeline Table (Last 14 Days)
    timeline = stats.get("timeline", [])
    if timeline:
        max_commits_day = max([item[1] for item in timeline]) or 1
        timeline_table = Table(title="Commit Activity (Last 14 Days)", show_header=True, header_style="bold medium_purple1", box=box.ROUNDED)
        timeline_table.add_column("Date", style="bold white")
        timeline_table.add_column("Commits", justify="right")
        timeline_table.add_column("Activity Graph")
        
        for date_str, count in timeline:
            if count > 0:
                bar_len = int((count / max_commits_day) * 20)
                bar_len = max(1, bar_len)
                bar = "[medium_purple1]" + "█" * bar_len + "[/medium_purple1]"
            else:
                bar = "[grey37]·[/grey37]"
                
            timeline_table.add_row(date_str, str(count), bar)
            
        console.print(timeline_table)
        console.print()


@app.command(name="doctor", help="Run diagnostics on repository state and get AI-assisted recovery recommendations.")
def doctor_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    if not isinstance(offline, bool):
        offline = False

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.core.diagnostics import GitDiagnostics
    from ace.ai.prompts.doctor import DOCTOR_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from langchain_core.messages import SystemMessage, HumanMessage
    from rich.markdown import Markdown
    import json

    diagnostics = GitDiagnostics(git_ops)
    
    with spinner("Analyzing repository state..."):
        report = diagnostics.run_diagnostics()

    console.print()
    if not report["has_issues"]:
        print_success("All checks passed! Your Git repository is healthy and in a normal state.")
        if not report["dirty_files"]["staged"] and not report["dirty_files"]["unstaged"] and not report["dirty_files"]["untracked"]:
            console.print("  [dim]No lock files, large files, or pending merges/rebases found. Workspace is clean.[/dim]")
            raise typer.Exit(code=0)
            
    # Print diagnostic summary table
    table = Table(
        title="🩺 Git Diagnostics Status Report",
        show_header=True,
        header_style="bold #FF6D00",
        box=box.ROUNDED,
        border_style="#FF6D00"
    )
    table.add_column("Category", style="bold white")
    table.add_column("Status", justify="left")
    
    # Detached head status
    table.add_row(
        "Branch Head",
        "[bold green]OK[/bold green] (Branch: " + (report["sync_status"]["branch"]) + ")"
        if not report["detached_head"]
        else "[bold red]Detached HEAD[/bold red]"
    )
    
    # Operation state
    op_in_progress = report["operation_state"]["in_progress"]
    table.add_row(
        "Operation State",
        "[bold yellow]" + report["operation_state"]["type"].upper() + " in progress[/bold yellow]"
        if op_in_progress
        else "[bold green]Normal[/bold green]"
    )
    
    # Lock files
    table.add_row(
        "Process Lock Files",
        "[bold red]Lock files found[/bold red]"
        if report["locks"]
        else "[bold green]None[/bold green]"
    )
    
    # Large files
    table.add_row(
        "Large Untracked Files",
        "[bold red]Large files detected[/bold red]"
        if report["large_files"]
        else "[bold green]None[/bold green]"
    )
    
    # Workspace status
    dirty = report["dirty_files"]
    dirty_desc = f"[green]staged: {dirty['staged']}[/green] | [yellow]unstaged: {dirty['unstaged']}[/yellow] | [dim]untracked: {dirty['untracked']}[/dim]"
    table.add_row("Working Directory", dirty_desc)
    
    console.print(table)
    console.print()

    # Now call LLM for recommendations
    try:
        llm = get_llm(offline_override=offline)
        from ace.core.config import get_config
        from ace.utils.i18n import get_language_instruction
        lang_inst = get_language_instruction(get_config().ai.language)
        
        diagnostics_json = json.dumps(report, indent=2)
        usr_prompt = USER_PROMPT_TEMPLATE.format(diagnostics_json=diagnostics_json)
        
        messages = [
            SystemMessage(content=DOCTOR_SYSTEM_PROMPT + lang_inst),
            HumanMessage(content=usr_prompt)
        ]
        
        with spinner("Consulting repository doctor..."):
            response = llm.invoke(messages)
            
        console.print(Panel(
            Markdown(response.content.strip()),
            title="[bold white]🩺 AI Diagnostics & Recovery Report[/bold white]",
            border_style="#00D5FF",
            box=box.ROUNDED,
            expand=False,
            padding=(1, 2)
        ))
    except Exception as e:
        show_error_panel(f"Failed to generate recovery report: {e}", "Doctor Error")
        raise typer.Exit(code=1)


@app.command(name="explain", help="Explain a Git command, flag, concept, or error in plain English.")
def explain_cmd(
    query: str = typer.Argument(..., help="Git command, option, error, or concept to explain"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.ai.prompts.explain import EXPLAIN_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from ace.ai.llm_factory import get_llm, LLMConfigurationError
    from ace.core.config import get_config
    from ace.utils.i18n import get_language_instruction
    from langchain_core.messages import SystemMessage, HumanMessage
    from rich.markdown import Markdown

    # Resolve LLM
    try:
        llm = get_llm(offline_override=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)

    lang_inst = get_language_instruction(get_config().ai.language)
    usr_prompt = USER_PROMPT_TEMPLATE.format(query=query)
    messages = [
        SystemMessage(content=EXPLAIN_SYSTEM_PROMPT + lang_inst),
        HumanMessage(content=usr_prompt)
    ]

    try:
        with spinner(f"Explaining '{query}'..."):
            response = llm.invoke(messages)
        explanation = response.content.strip()
        console.print()
        console.print(Markdown(explanation))
        console.print()
    except Exception as e:
        show_error_panel(f"Failed to generate explanation: {e}", "AI Error")
        raise typer.Exit(code=1)

@app.command(name="undo", help="Smart undo (figures out what to undo and resets safely).")
def undo_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm, LLMConfigurationError
    from ace.core.safety import SafetyChecker
    from ace.ui.prompts import confirm

    if not isinstance(offline, bool):
        offline = False

    # Initialize GitOps
    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    # 1. Fetch reflog (last 10 entries)
    try:
        reflog = git_ops.execute("reflog -10")
    except Exception:
        reflog = "No reflog available (empty repository)."

    # 2. Fetch git state
    from ace.core.context import RepoContext
    context_builder = RepoContext(git_ops)
    git_state_info = context_builder.check_merge_rebase_state()
    git_state_desc = "Normal"
    if git_state_info["in_progress"]:
        git_state_desc = f"{git_state_info['type'].upper()} ({git_state_info['detail']})"

    status = git_ops.get_status()
    staged = ", ".join(status["staged"]) or "None"
    unstaged = ", ".join(status["unstaged"]) or "None"

    # 3. Call LLM to plan undo
    from ace.ai.prompts.undo import UNDO_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from ace.core.config import get_config
    from ace.utils.i18n import get_language_instruction
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.utils.json_utils import extract_json

    # Resolve LLM
    try:
        llm = get_llm(offline_override=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)

    lang_inst = get_language_instruction(get_config().ai.language)
    usr_prompt = USER_PROMPT_TEMPLATE.format(
        git_state=git_state_desc,
        staged_files=staged,
        unstaged_files=unstaged,
        reflog_entries=reflog
    )

    messages = [
        SystemMessage(content=UNDO_SYSTEM_PROMPT + lang_inst),
        HumanMessage(content=usr_prompt)
    ]

    try:
        with spinner("Analyzing state to plan undo..."):
            response = llm.invoke(messages)
        parsed = extract_json(response.content)
    except Exception as e:
        show_error_panel(f"Failed to plan undo: {e}", "AI Error")
        raise typer.Exit(code=1)

    commands = parsed.get("commands", [])
    explanation = parsed.get("explanation", "")

    if not commands:
        print_info("Nothing to undo or state is already clean.")
        console.print(f"Explanation: {explanation}")
        raise typer.Exit(code=0)

    # Show the proposed undo plan
    from ace.ui.display import show_plan
    show_plan(commands, [explanation] + [""] * (len(commands) - 1))

    # Safety checks
    highest_risk = "safe"
    risk_details = []
    safer_alts = []
    
    for cmd in commands:
        r_level, r_desc, alt = SafetyChecker.analyze_command(cmd)
        if r_level == "destructive":
            highest_risk = "destructive"
            risk_details.append(f"[bold red]Command:[/] {cmd}\n[bold red]Risk:[/] {r_desc}")
            if alt:
                safer_alts.append(f"[bold green]Safer Alternative:[/] {alt}")
        elif r_level == "moderate" and highest_risk != "destructive":
            highest_risk = "moderate"

    # Confirmation flow
    if highest_risk == "destructive":
        show_warning_panel(
            "\n\n".join(risk_details) + ("\n\n" + "\n".join(safer_alts) if safer_alts else ""),
            "⚠️ DESTRUCTIVE UNDO OPERATION DETECTED"
        )
        if not confirm("Are you sure you want to execute these destructive undo commands?", default=False):
            print_info("Undo aborted.")
            raise typer.Exit(code=0)
    else:
        # Ask confirmation for moderate/safe undo commands (defaults to Yes)
        if not confirm("Do you want to execute this undo plan?", default=True):
            print_info("Undo aborted.")
            raise typer.Exit(code=0)

    # Execute
    for cmd in commands:
        print_info(f"Executing: {cmd}")
        if cmd.startswith("git "):
            git_args = cmd[4:]
        else:
            git_args = cmd
            
        try:
            res = git_ops.execute(git_args)
            if res.strip():
                console.print(res)
        except Exception as e:
            show_error_panel(f"Failed to execute command '{cmd}': {e}", "Execution Error")
            raise typer.Exit(code=1)

    print_success("Undo plan executed successfully!")

@app.command(name="dash", help="Interactive terminal dashboard for repository management.")
def dash_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.ui.dashboard import show_dashboard
    show_dashboard(git_ops, offline=offline)

@app.command(name="pr", help="Generate a pull request description from branch changes.")
def pr_cmd(
    base: Optional[str] = typer.Option(None, "--base", "-b", help="Base branch/commit to compare against (defaults to remote tracking or 'main')"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="File to write the generated PR description to"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    if not isinstance(base, str):
        base = None
    if not isinstance(output, str):
        output = None
    if not isinstance(offline, bool):
        offline = False

    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from rich.panel import Panel

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    # If base is not specified, try to find upstream tracking or fall back to main/master
    if not base:
        tracking = git_ops.get_upstream_tracking()
        if tracking:
            base = tracking
        else:
            branches = git_ops.get_branches()
            if "main" in branches:
                base = "main"
            elif "master" in branches:
                base = "master"
            else:
                base = "main"

    from ace.ai.pr_drafter import PRDrafter
    drafter = PRDrafter(git_ops)

    try:
        with spinner(f"Generating PR description against base branch '{base}'..."):
            pr_data = drafter.draft_pr(base, offline=offline)
    except Exception as e:
        title = "Git Error" if "Cmd('git')" in str(e) or "git log" in str(e) or "exit code" in str(e) else "AI Error"
        show_error_panel(f"Failed to generate PR description: {e}", title)
        raise typer.Exit(code=1)

    title = pr_data.get("title", "Pull Request")
    body = pr_data.get("body", "")

    full_markdown = f"# PR: {title}\n\n{body}"

    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                f.write(full_markdown)
            print_success(f"PR description successfully written to {output}!")
        except Exception as e:
            show_error_panel(f"Failed to write PR to {output}: {e}", "File Error")
            raise typer.Exit(code=1)
    else:
        from rich.markdown import Markdown
        console.print()
        console.print(Panel(f"[bold cyan]Proposed PR Title:[/bold cyan]\n{title}", border_style="cyan"))
        console.print()
        console.print(Markdown(body))
        console.print()

@app.command(name="search", help="Semantic commit search using natural language.")
def search_cmd(
    query: str = typer.Argument(..., help="Search query (e.g. 'nvidia credential fix')"),
    limit: int = typer.Option(50, "--limit", "-l", help="Number of recent commits to search"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from rich.table import Table

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.ai.history_analyzer import HistoryAnalyzer
    analyzer = HistoryAnalyzer(git_ops)

    try:
        get_llm(offline_override=offline)
        with spinner(f"Semantically searching last {limit} commits for '{query}'..."):
            results = analyzer.semantic_search(query, limit=limit, offline=offline)
    except Exception as e:
        show_error_panel(f"Search failed: {e}", "AI Error")
        raise typer.Exit(code=1)

    matches = results.get("matches", [])
    if not matches:
        print_warning("No matching commits found.")
        raise typer.Exit(code=0)

    table = Table(title=f"Semantic Search Results for '{query}'", show_header=True, header_style="bold orange3")
    table.add_column("Commit", style="dim", width=8)
    table.add_column("Summary", style="bold green")
    table.add_column("Match Explanation")

    for match in matches:
        table.add_row(match.get("hexsha", "")[:7], match.get("summary", ""), match.get("reason", ""))

    console.print()
    console.print(table)
    console.print()

    from ace.ui.prompts import prompt_select, confirm
    
    if confirm("Would you like to select a commit to inspect/checkout?", default=False):
        options = []
        for match in matches:
            options.append(f"{match.get('hexsha', '')[:7]} - {match.get('summary', '')}")
            
        selected_idx = prompt_select(options, prompt_text="Select commit number to inspect")
        if selected_idx != -1:
            selected_match = matches[selected_idx]
            selected_sha = selected_match.get("hexsha", "")
            
            console.print(f"\nSelected Commit: [bold]{selected_sha}[/bold]")
            
            # Show options loop
            while True:
                console.print("\n[bold]Select action:[/bold]")
                def _key(k: str, desc: str) -> None:
                    from rich.text import Text
                    console.print(Text.assemble(
                        ("  ", ""), (f"[{k}]", "bold #00D5FF"), (f"  {desc}", "#BDBDBD")
                    ))
                _key("d", "View diff of this commit")
                _key("c", "Checkout this commit (detached HEAD)")
                _key("b", "Create and switch to a new branch here")
                _key("s", "Skip / Quit")

                action = click.getchar().lower().strip()
                console.print(action)
                console.print()
                
                if action in ("s", "q", ""):
                    break
                elif action == "d":
                    try:
                        diff_data = git_ops.repo.git.show(selected_sha)
                        from ace.ui.display import show_diff
                        show_diff(diff_data)
                    except Exception as e:
                        show_error_panel(f"Failed to fetch diff: {e}", "Git Error")
                elif action == "c":
                    try:
                        with spinner(f"Checking out commit {selected_sha[:7]}..."):
                            git_ops.execute(f"checkout {selected_sha}")
                        print_success(f"Checked out {selected_sha[:7]} (detached HEAD state).")
                        break
                    except Exception as e:
                        show_error_panel(f"Checkout failed: {e}", "Git Error")
                        break
                elif action == "b":
                    branch_name = click.prompt("Enter new branch name")
                    if branch_name.strip():
                        try:
                            with spinner(f"Creating branch '{branch_name}' at {selected_sha[:7]}..."):
                                git_ops.execute(f"checkout -b {branch_name} {selected_sha}")
                            print_success(f"Successfully created and switched to branch '{branch_name}'!")
                            break
                        except Exception as e:
                            show_error_panel(f"Failed to create branch: {e}", "Git Error")
                            break

def _execute_alias(alias_name: str, expanded_cmd: str):
    import shlex
    import subprocess
    from rich.text import Text
    from ace.core.git_ops import GitOps

    console.print(Text.assemble(
        ("⚡ Running custom shortcut: ", "bold #00D5FF"),
        (f"ace {alias_name}", "bold white"),
        (f" → {expanded_cmd}", "dim #9E9E9E")
    ))
    console.print()

    sub_commands = [c.strip() for c in expanded_cmd.split("&&") if c.strip()]
    for sub in sub_commands:
        if sub.startswith("ace "):
            sub_args = shlex.split(sub[4:])
            try:
                app(sub_args)
            except SystemExit as e:
                if e.code != 0:
                    raise typer.Exit(code=e.code)
            except Exception as e:
                show_error_panel(f"Alias command '{sub}' failed: {e}", "Alias Execution Error")
                raise typer.Exit(code=1)
        elif sub.startswith("git "):
            try:
                git_ops = GitOps()
                with spinner(f"Executing: {sub}..."):
                    res = git_ops.execute(sub[4:])
                print_success(f"Executed: {sub}")
                if res.strip():
                    console.print(f"[dim]{res}[/dim]")
            except Exception as e:
                show_error_panel(f"Git command '{sub}' failed: {e}", "Alias Execution Error")
                raise typer.Exit(code=1)
        else:
            res = subprocess.run(sub, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                print_success(f"Executed: {sub}")
                if res.stdout.strip():
                    console.print(f"[dim]{res.stdout.strip()}[/dim]")
            else:
                show_error_panel(f"Command '{sub}' failed: {res.stderr.strip()}", "Alias Execution Error")
                raise typer.Exit(code=1)

@app.command(name="alias", help="Manage custom command shortcuts and natural language workflows.")
def alias_cmd(
    action: Optional[str] = typer.Argument(None, help="Action: 'list' (or 'ls'), 'add', 'remove' (or 'rm')"),
    name: Optional[str] = typer.Argument(None, help="Name of the alias (e.g. 'ship', 'wip')"),
    command: Optional[str] = typer.Argument(None, help="Command string to execute (e.g. 'git add . && ace commit -y')"),
):
    from ace.core.config import get_config, save_config
    from rich.table import Table
    from rich import box

    config = get_config()
    act = (action or "list").lower().strip()

    if act in ("list", "ls"):
        aliases = config.aliases
        if not aliases:
            print_info("No custom aliases defined. Add one using: ace alias add <name> \"<command>\"")
            return

        table = Table(title="Ace Custom Shortcuts & Aliases", box=box.ROUNDED, show_header=True, header_style="bold #FF6D00")
        table.add_column("Alias", style="bold cyan", min_width=12)
        table.add_column("Command / Workflow", style="white")
        table.add_column("Usage Example", style="dim italic")

        for alias_name, alias_cmd_str in aliases.items():
            table.add_row(alias_name, alias_cmd_str, f"ace {alias_name}")

        console.print(table)
        console.print()

    elif act == "add":
        if not name or not command:
            show_error_panel("Usage: ace alias add <name> \"<command_string>\"", "Input Error")
            raise typer.Exit(code=1)

        config.set_alias(name, command)
        save_config(config)
        print_success(f"Successfully added shortcut '{name}' -> '{command}'!")
        console.print(f"[dim]Run it anytime with: [bold cyan]ace {name}[/bold cyan][/dim]")

    elif act in ("remove", "rm", "delete"):
        if not name:
            show_error_panel("Usage: ace alias remove <name>", "Input Error")
            raise typer.Exit(code=1)

        if config.remove_alias(name):
            save_config(config)
            print_success(f"Successfully removed shortcut '{name}'.")
        else:
            print_warning(f"No alias found named '{name}'.")

    else:
        show_error_panel(f"Unknown action '{action}'. Valid actions: list, add, remove.", "Input Error")
        raise typer.Exit(code=1)


@app.command(name="ignore", help="Smart gitignore generation and template addition.")
def ignore_cmd(
    query: str = typer.Argument(..., help="What to ignore (e.g. 'node_modules', 'temp files')"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from ace.ui.prompts import confirm
    from rich.panel import Panel

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.ai.gitignore_generator import GitignoreGenerator
    generator = GitignoreGenerator(git_ops)

    try:
        get_llm(offline_override=offline)
        with spinner(f"Generating .gitignore rules for '{query}'..."):
            res = generator.generate_rules(query, offline=offline)
    except Exception as e:
        show_error_panel(f"Failed to generate rules: {e}", "AI Error")
        raise typer.Exit(code=1)

    rules = res.get("rules", "")
    explanation = res.get("explanation", "")

    if not rules.strip():
        print_warning("No new rules needed.")
        console.print(f"Explanation: {explanation}")
        raise typer.Exit(code=0)

    console.print(Panel(rules, title="[bold yellow]Proposed .gitignore Rules[/bold yellow]", border_style="yellow"))
    console.print(f"\n[bold]Explanation:[/bold] {explanation}\n")

    if confirm("Append these rules to your .gitignore?", default=True):
        gitignore_path = os.path.join(git_ops.working_dir, ".gitignore")
        try:
            prepend_newline = False
            if os.path.exists(gitignore_path) and os.path.getsize(gitignore_path) > 0:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content and not content.endswith("\n"):
                        prepend_newline = True

            with open(gitignore_path, "a", encoding="utf-8") as f:
                if prepend_newline:
                    f.write("\n")
                f.write(rules + "\n")
            print_success("Rules successfully appended to .gitignore!")
        except Exception as e:
            show_error_panel(f"Failed to update .gitignore: {e}", "File Error")
            raise typer.Exit(code=1)
    else:
        print_info("Cancelled. No changes made.")

@app.command(name="help", help="Show user guide and help information on how to use Ace.")
def help_cmd():
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from ace.ui.banner import get_fire_banner_static
    
    # 1. Header with static gradient banner
    console.print(get_fire_banner_static())
    
    # Intro
    console.print("[bold orange3]Ace AI Git Copilot — Help & User Guide[/bold orange3] 🚀")
    console.print("Ace is your AI-powered companion for Git. You can control Git either by running specific commands or by talking to Git in plain English!\n")
    
    # 2. Natural Language Usage Section
    nl_text = Text.from_markup(
        "[bold white]How to talk to Ace in Plain English:[/bold white]\n"
        "Simply type your request as a quoted string after [bold cyan]ace[/bold cyan]. For example:\n"
        "  [bold green]ace \"add all python files and commit\"[/bold green]\n"
        "  [bold green]ace \"show me commits from yesterday\"[/bold green]\n"
        "  [bold green]ace \"undo last commit but keep my changes staged\"[/bold green]\n\n"
        "Ace will analyze your request and repository state, formulate a command plan, explain what it will do, assess safety risks, and execute it upon your confirmation."
    )
    console.print(Panel(nl_text, title="🗣️  Natural Language Interface", border_style="orange3", expand=False))
    console.print()
    
    # 3. Core Commands Table
    table = Table(title="Core Ace Commands", show_header=True, header_style="bold orange3")
    table.add_column("Command", style="cyan bold")
    table.add_column("Description", style="white")
    table.add_column("Usage Example", style="dim italic")
    
    table.add_row("setup", "Run the configuration wizard to set up AI provider credentials", "ace setup")
    table.add_row("config", "View active configuration values and API settings", "ace config")
    table.add_row("dash", "Open the interactive terminal dashboard for repository management", "ace dash")
    table.add_row("commit", "Analyze staged changes and generate a high-quality smart commit", "ace commit")
    table.add_row("review", "Perform AI-powered code review of staged, unstaged, or branch changes", "ace review --all")
    table.add_row("resolve", "AI-assisted interactive merge conflict resolution", "ace resolve")
    table.add_row("stats", "Display contribution stats, file distributions, and activity graph", "ace stats")
    table.add_row("changelog", "Generate a markdown changelog between commits or tags", "ace changelog --from v1.0.0")
    table.add_row("explain", "Explain a Git command, concept, flag, or error in plain English", "ace explain \"git rebase --onto\"")
    table.add_row("undo", "Smart undo that analyzes state and safely reverts the last action", "ace undo")
    table.add_row("doctor", "Run repository diagnostics and get AI-assisted recovery advice", "ace doctor")
    table.add_row("hook", "Install or uninstall pre-commit and prepare-commit-msg Git hooks", "ace hook install")
    table.add_row("squash", "AI-assisted automated commit squashing and history clean up", "ace squash")
    table.add_row("pr", "Draft a detailed pull request description from branch differences", "ace pr -b main")
    table.add_row("search", "Perform a semantic commit search of recent commit history", "ace search \"auth fix\"")
    table.add_row("ignore", "Generate gitignore rules and append them to .gitignore", "ace ignore \"temp log files\"")
    table.add_row("add / stage", "Stage files in the repository index to prepare for committing", "ace add .")
    
    console.print(table)
    console.print()
    
    # 4. Global options and tips
    tips_text = Text.from_markup(
        "💡 [bold orange3]Tips & Tricks:[/bold orange3]\n"
        "• [bold]Dry Run[/bold]: Use [bold cyan]--dry-run[/bold cyan] or [bold cyan]-d[/bold cyan] with natural language queries to see the plan without executing.\n"
        "• [bold]Auto-Yes[/bold]: Use [bold cyan]--yes[/bold cyan] or [bold cyan]-y[/bold cyan] to automatically skip execution confirmations (except destructive operations).\n"
        "• [bold]Offline Mode[/bold]: Use [bold cyan]--offline[/bold cyan] to force Ace to run fallback local queries using Ollama.\n"
        "• [bold]Safety First[/bold]: Ace automatically flags destructive actions (like [red]git reset --hard[/red] or force-pushes) and demands manual approval."
    )
    console.print(Panel(tips_text, border_style="dim", expand=False))

@app.command(name="add", help="Stage files (git add) to prepare for commit.")
def add_cmd(
    files: List[str] = typer.Argument(..., help="Files or patterns to stage (use '.' to stage all changes)"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    quoted_files = [f'"{f}"' if " " in f and not (f.startswith('"') or f.startswith("'")) else f for f in files]
    files_str = " ".join(quoted_files)
    try:
        with spinner(f"Staging changes for: {files_str}..."):
            res = git_ops.execute(f"add {files_str}")
        print_success(f"Successfully staged: {files_str}")
        if res.strip():
            console.print(res)
    except Exception as e:
        show_error_panel(f"Failed to stage files: {e}", "Git Error")
        raise typer.Exit(code=1)

@app.command(name="stage", help="Stage files (git add) to prepare for commit.")
def stage_cmd(
    files: List[str] = typer.Argument(..., help="Files or patterns to stage (use '.' to stage all changes)"),
):
    add_cmd(files)

@app.command(name="squash", help="AI-assisted automated commit squashing and history clean up.")
def squash_cmd(
    base: Optional[str] = typer.Option(None, "--base", "-b", help="Base branch/commit to squash against (defaults to remote tracking or 'main')"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    if not isinstance(base, str):
        base = None
    if not isinstance(offline, bool):
        offline = False

    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from ace.ui.prompts import confirm
    from rich.table import Table
    from rich import box

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    if not base:
        tracking = git_ops.get_upstream_tracking()
        if tracking:
            base = tracking.split("/")[0] if "/" in tracking else tracking
        else:
            branches = git_ops.get_branches()
            if "main" in branches:
                base = "main"
            elif "master" in branches:
                base = "master"
            else:
                base = "main"

    from ace.ai.rebase_helper import RebaseHelper
    helper = RebaseHelper(git_ops)
    
    with spinner(f"Analyzing local commits against '{base}'..."):
        commits = helper.get_local_commits(base)
        
    if not commits:
        print_success(f"No local commits found ahead of '{base}'. History is clean.")
        raise typer.Exit(code=0)

    try:
        get_llm(offline_override=offline)
        with spinner("Analyzing history for squash and cleanup actions..."):
            parsed = helper.analyze_commits(commits, offline=offline)
    except Exception as e:
        show_error_panel(f"Rebase analysis failed: {e}", "AI Error")
        raise typer.Exit(code=1)

    recommendations = parsed.get("recommendations", [])
    explanation = parsed.get("explanation", "")

    if not recommendations:
        print_info("No squashing recommendations generated.")
        console.print(f"Explanation: {explanation}")
        raise typer.Exit(code=0)

    # Show proposed squash plan table
    table = Table(
        title="🧠 Proposed Commit Squash Plan",
        show_header=True,
        header_style="bold #FF6D00",
        box=box.ROUNDED,
        border_style="#FF6D00"
    )
    table.add_column("Commit", style="dim", width=8)
    table.add_column("Action", style="bold")
    table.add_column("Current Summary")
    table.add_column("Reworded Summary (if any)", style="italic green")

    for rec in recommendations:
        action = rec.get("action", "pick").lower()
        if action == "pick":
            action_styled = "[green]pick[/green]"
        elif action == "squash":
            action_styled = "[yellow]squash[/yellow]"
        elif action == "reword":
            action_styled = "[cyan]reword[/cyan]"
        elif action == "drop":
            action_styled = "[red]drop[/red]"
        else:
            action_styled = action
            
        new_msg = rec.get("new_message") or ""
        table.add_row(
            rec.get("hexsha", "")[:7],
            action_styled,
            rec.get("summary", ""),
            new_msg
        )

    console.print()
    console.print(table)
    console.print(f"\n[bold]Reasoning:[/bold] {explanation}\n")

    if confirm("Do you want to execute this squash plan?", default=True):
        try:
            with spinner("Running automated rebase/squash..."):
                res = helper.run_auto_rebase(base, recommendations)
            print_success("History squashed and cleaned successfully!")
            if res.strip():
                console.print(f"[dim]{res}[/dim]")
        except Exception as e:
            show_error_panel(f"Failed to execute rebase/squash: {e}", "Git Rebase Error")
            raise typer.Exit(code=1)
    else:
        print_info("Squash aborted.")

@app.command(name="hook", help="Install or uninstall AI-powered pre-commit or prepare-commit-msg Git hooks.")
def hook_cmd(
    action: str = typer.Argument(..., help="Action to perform: 'install' or 'uninstall'"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    from ace.core.hooks import GitHooksManager
    manager = GitHooksManager(git_ops)

    if action.strip().lower() == "install":
        with spinner("Installing pre-commit code reviewer hook..."):
            p1 = manager.install_pre_commit()
        with spinner("Installing prepare-commit-msg generator hook..."):
            p2 = manager.install_prepare_commit_msg()
            
        print_success("Ace Git hooks installed successfully!")
        console.print(f"  - pre-commit: [dim]{p1}[/dim]")
        console.print(f"  - prepare-commit-msg: [dim]{p2}[/dim]")
        
    elif action.strip().lower() == "uninstall":
        with spinner("Removing Ace Git hooks..."):
            manager.uninstall_all()
        print_success("Ace Git hooks uninstalled successfully.")
    else:
        show_error_panel("Invalid action. Use 'install' or 'uninstall'.", "Usage Error")
        raise typer.Exit(code=1)

@app.command(name="workspace", help="Monitor status of multiple repositories and navigate between them.")
def workspace_cmd(
    path: Optional[str] = typer.Argument(
        None, help="Custom directory to scan (defaults to sibling projects scan)"
    ),
):
    from pathlib import Path
    import os
    import sys
    import subprocess
    from rich.table import Table
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ui.display import console, print_info, print_success, print_warning, print_error
    from ace.ui.prompts import prompt_select, prompt_action

    # 1. Determine target directory to scan
    if path:
        scan_dir = Path(path).resolve()
    else:
        # Smart default
        cwd = Path(os.getcwd()).resolve()
        if (cwd / ".git").exists():
            scan_dir = cwd.parent
        else:
            scan_dir = cwd

    if not scan_dir.exists() or not scan_dir.is_dir():
        print_error(f"Directory not found: {scan_dir}")
        raise typer.Exit(code=1)

    print_info(f"Scanning workspace directory: [bold]{scan_dir}[/bold]")

    # 2. Find git repositories
    repos_found = []
    try:
        for child in sorted(scan_dir.iterdir()):
            if not child.is_dir():
                continue
            # Basic validation that it's a git repo
            if (child / ".git").exists() or (child / "gitdir").exists() or child.name.endswith(".git"):
                try:
                    git_ops = GitOps(str(child))
                    repos_found.append((child, git_ops))
                except Exception:
                    pass
    except Exception as e:
        print_error(f"Failed to scan directory: {e}")
        raise typer.Exit(code=1)

    if not repos_found:
        print_warning(f"No active Git repositories found in: {scan_dir}")
        return

    # 3. Build Status Table
    table = Table(
        title=f"[bold white]Workspace Summary: {scan_dir.name}[/bold white]",
        title_style="bold",
        border_style="#FF6D00",
        expand=True,
    )
    table.add_column("[bold #00D5FF]#[/bold #00D5FF]", justify="right", width=4)
    table.add_column("Repository", style="bold white")
    table.add_column("Branch", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("Sync", justify="center")

    display_options = []
    for idx, (repo_path, git_ops) in enumerate(repos_found, 1):
        repo_name = repo_path.name
        
        # Branch
        branch_name = git_ops.get_current_branch() or "Detached HEAD"
        
        # Status counts
        status = git_ops.get_status()
        staged = len(status.get("staged", []))
        unstaged = len(status.get("unstaged", []))
        untracked = len(status.get("untracked", []))
        
        if staged == 0 and unstaged == 0 and untracked == 0:
            status_desc = "[bold green]Clean[/bold green]"
        else:
            parts = []
            if staged > 0:
                parts.append(f"[bold #00E676]+{staged}[/bold #00E676]")
            if unstaged > 0:
                parts.append(f"[bold #FFD600]~{unstaged}[/bold #FFD600]")
            if untracked > 0:
                parts.append(f"[bold #FF1744]?{untracked}[/bold #FF1744]")
            status_desc = " ".join(parts)

        # Sync offsets
        ab = git_ops.get_ahead_behind()
        ahead = ab.get("ahead", 0)
        behind = ab.get("behind", 0)
        tracking = git_ops.get_upstream_tracking()
        
        if not tracking:
            sync_desc = "[#666666]No Upstream[/#666666]"
        elif ahead == 0 and behind == 0:
            sync_desc = "[bold green]Up-to-date[/bold green]"
        elif ahead > 0 and behind == 0:
            sync_desc = f"[bold #00D5FF]Ahead {ahead}[/bold #00D5FF]"
        elif behind > 0 and ahead == 0:
            sync_desc = f"[bold #FFD600]Behind {behind}[/bold #FFD600]"
        else:
            sync_desc = f"[bold #FF1744]Diverged (A{ahead}, B{behind})[/bold #FF1744]"

        table.add_row(
            str(idx),
            repo_name,
            branch_name,
            status_desc,
            sync_desc
        )
        display_options.append(repo_name)

    console.print()
    console.print(table)
    console.print()

    # 4. Prompt selection
    selected_idx = prompt_select(
        display_options,
        prompt_text="  Select repository number to manage (or 'q' to quit)",
        default="q"
    )
    
    if selected_idx < 0:
        print_info("Exit workspace monitor.")
        return

    selected_path, _ = repos_found[selected_idx]

    # 5. Prompt action choice
    console.print(f"\n[bold white]  Choose action for [bold cyan]{selected_path.name}[/bold cyan]:[/bold white]")
    action_options = {
        "d": ("Dashboard", "Open interactive TUI dashboard"),
        "s": ("Shell", "Spawn an interactive shell in project directory"),
        "c": ("Command", "Execute an ace natural-language command"),
        "q": ("Quit", "Cancel action and exit")
    }
    
    action = prompt_action(action_options, default_key="d")
    
    if action == "d":
        print_success(f"Launching dashboard in {selected_path.name}...")
        console.print()
        try:
            subprocess.run([sys.executable, "-m", "ace", "dash"], cwd=str(selected_path))
        except Exception as e:
            print_error(f"Failed to launch dashboard: {e}")
            
    elif action == "s":
        shell = os.environ.get("SHELL")
        if not shell:
            if sys.platform == "win32":
                shell = "powershell.exe"
            else:
                shell = "/bin/bash"
                
        print_success(f"Opening interactive shell in {selected_path.name}...")
        print_info("Type 'exit' to return to Ace workspace monitor.")
        console.print()
        
        try:
            subprocess.run([shell], cwd=str(selected_path))
            print_success("Returned to Ace workspace.")
        except Exception as e:
            print_error(f"Failed to open shell: {e}")
            
    elif action == "c":
        query = typer.prompt("  Enter command for this repo")
        if query.strip():
            print_success(f"Running command: {query}")
            console.print()
            try:
                subprocess.run([sys.executable, "-m", "ace", query], cwd=str(selected_path))
            except Exception as e:
                print_error(f"Failed to run command: {e}")

@app.command(name="ws", help="Alias for 'workspace' command.")
def ws_cmd(
    path: Optional[str] = typer.Argument(
        None, help="Custom directory to scan"
    ),
):
    workspace_cmd(path)

@app.command(name="standup", help="Generate a professional daily standup update based on your recent commits.")
def standup_cmd(
    days: int = typer.Option(1, "--days", "-d", help="Number of days of history to scan"),
    all_authors: bool = typer.Option(False, "--all", "-a", help="Include commits from all authors (defaults to current user only)"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from ace.ai.history_analyzer import HistoryAnalyzer
    from rich.markdown import Markdown
    from rich.panel import Panel
    import pathlib

    current_dir = pathlib.Path(".")
    repos_found = []

    # 1. Try active repository in current folder
    try:
        git_ops = GitOps()
        repos_found.append((current_dir.resolve().name, git_ops))
    except NotAGitRepositoryError:
        # Fallback: scan immediate subdirectories for sibling repositories
        try:
            for child in sorted(current_dir.iterdir()):
                if child.is_dir() and ((child / ".git").exists() or (child / "gitdir").exists() or child.name.endswith(".git")):
                    try:
                        repos_found.append((child.name, GitOps(str(child))))
                    except Exception:
                        pass
        except Exception:
            pass

    if not repos_found:
        show_error_panel("Not a git repository (or any of the parent directories).", "Git Error")
        raise typer.Exit(code=1)

    # 2. Gather commits from all resolved repositories
    all_commits = []
    since_arg = f"{days} days ago"

    # We need a primary git_ops instance to initialize HistoryAnalyzer
    primary_git_ops = repos_found[0][1]

    for repo_name, git_ops in repos_found:
        author_name = None
        if not all_authors:
            try:
                author_name = git_ops.repo.git.config("user.name")
            except Exception:
                pass
        
        try:
            repo_commits = git_ops.get_log(since=since_arg, author=author_name)
            for c in repo_commits:
                c["repo_name"] = repo_name
                all_commits.append(c)
        except Exception:
            pass

    if not all_commits:
        author_msg = "your" if not all_authors else "any"
        scope_msg = "this repository" if len(repos_found) == 1 else f"{len(repos_found)} repositories in this directory"
        print_warning(f"No recent commits found from {author_msg} author in {scope_msg} in the last {days} day(s).")
        raise typer.Exit(code=0)

    analyzer = HistoryAnalyzer(primary_git_ops)

    try:
        get_llm(offline_override=offline)
        with spinner(f"Analyzing {len(all_commits)} commits across {len(repos_found)} repo(s) and generating standup..."):
            standup_report = analyzer.generate_standup(all_commits, offline=offline)
    except Exception as e:
        show_error_panel(f"Failed to generate standup: {e}", "AI Error")
        raise typer.Exit(code=1)

    console.print()
    console.print(Panel(
        Markdown(standup_report),
        title="[bold green]AI Daily Standup Report[/bold green]",
        border_style="#00E676",
        padding=(1, 2)
    ))
    console.print()

@app.command(name="blame", help="AI-powered Git blame: analyze who wrote a line, when, and explain WHY they wrote it.")
def blame_cmd(
    file: str = typer.Argument(..., help="Path to the file to inspect"),
    line: int = typer.Argument(..., help="Line number to inspect"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.core.git_ops import GitOps, NotAGitRepositoryError
    from ace.ai.llm_factory import get_llm
    from ace.ai.history_analyzer import HistoryAnalyzer
    from rich.markdown import Markdown
    from rich.panel import Panel
    import pathlib

    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    # 1. Resolve path and verify it exists
    filepath = pathlib.Path(file)
    if not filepath.exists() or not filepath.is_file():
        show_error_panel(f"File '{file}' does not exist or is not a regular file.", "Input Error")
        raise typer.Exit(code=1)

    # 2. Retrieve the line content
    try:
        file_lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
        if line < 1 or line > len(file_lines):
            show_error_panel(f"Line number {line} is out of bounds for '{file}' (total lines: {len(file_lines)}).", "Input Error")
            raise typer.Exit(code=1)
        line_content = file_lines[line - 1].strip()
    except Exception as e:
        show_error_panel(f"Failed to read file: {e}", "Read Error")
        raise typer.Exit(code=1)

    # 3. Run git blame for this line
    try:
        quoted_file = f'"{file}"' if " " in file and not (file.startswith('"') or file.startswith("'")) else file
        blame_output = git_ops.execute(f"blame -L {line},{line} -- {quoted_file}")
        parts = blame_output.strip().split()
        if not parts:
            raise ValueError("Blame output is empty.")
        commit_hash = parts[0]
        commit_hash = commit_hash.lstrip("^")
    except Exception as e:
        show_error_panel(f"Failed to execute git blame: {e}", "Git Error")
        raise typer.Exit(code=1)

    # 4. Get commit details and full diff patch
    try:
        commit = git_ops.repo.commit(commit_hash)
        commit_info = {
            "hexsha": commit.hexsha,
            "author": commit.author.name,
            "date": commit.committed_datetime.isoformat(),
            "summary": commit.summary,
            "message": commit.message,
        }
        commit_show_output = git_ops.execute(f"show -p {commit_hash} -- {file}")
    except Exception as e:
        show_error_panel(f"Failed to fetch commit details for '{commit_hash}': {e}", "Git Error")
        raise typer.Exit(code=1)

    # 5. Run LLM blame analysis
    analyzer = HistoryAnalyzer(git_ops)

    try:
        get_llm(offline_override=offline)
        with spinner(f"Analyzing commit history for line {line}..."):
            blame_analysis = analyzer.analyze_blame(
                file=file,
                line=line,
                commit_info=commit_info,
                commit_show_output=commit_show_output,
                line_content=line_content,
                offline=offline
            )
    except Exception as e:
        show_error_panel(f"Failed to analyze blame: {e}", "AI Error")
        raise typer.Exit(code=1)

    console.print()
    console.print(Panel(
        Markdown(blame_analysis),
        title=f"[bold cyan]AI Blame Analysis: {file}:{line}[/bold cyan]",
        border_style="#00D5FF",
        padding=(1, 2)
    ))
    console.print()

if __name__ == "__main__":
    app()




