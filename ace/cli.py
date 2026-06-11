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

from rich.table import Table
from rich.panel import Panel
from rich import box
from ace import __version__
from ace.core.config import get_config, save_config, DEFAULT_CONFIG_PATH
from ace.core.git_ops import GitOps, NotAGitRepositoryError
from ace.ai.commit_generator import CommitGenerator, NoStagedChangesError
from ace.ai.llm_factory import get_llm, LLMConfigurationError
from ace.ai.intent_parser import IntentParser
from ace.core.safety import SafetyChecker
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
from ace.ui.prompts import confirm, prompt_action

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
    if ctx.invoked_subcommand is not None:
        # A subcommand was invoked, let it execute
        return
        
    if not ctx.args:
        # No query and no subcommand, Typer will show help
        console.print(ctx.get_help())
        raise typer.Exit()

    query = " ".join(ctx.args)

    # Initialize GitOps
    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    console.print(f"🧠 Understanding request: [italic]\"{query}\"[/italic]...")
    parser = IntentParser(git_ops)

    try:
        get_llm(offline_override=offline)
        with spinner("Planning Git commands..."):
            parsed = parser.parse_intent(query, offline=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)
    except Exception as e:
        show_error_panel(f"Failed to plan commands: {e}", "AI Error")
        raise typer.Exit(code=1)

    commands = parsed.get("commands", [])
    explanation = parsed.get("explanation", "")

    if not commands:
        print_warning("No Git commands planned.")
        console.print(f"\n[bold]Explanation:[/bold] {explanation}\n")
        raise typer.Exit(code=0)

    # Show the proposed plan
    from ace.ui.display import show_plan
    # Fill explanations list of matching length
    show_plan(commands, [explanation] + [""] * (len(commands) - 1))

    # Evaluate safety for all planned commands
    highest_risk = "safe"
    risk_details = []
    safer_alts = []
    
    for cmd in commands:
        r_level, r_desc, alt = SafetyChecker.analyze_command(cmd)
        if r_level == "destructive":
            highest_risk = "destructive"
            risk_details.append(f"[bold red]Command:[/bold] {cmd}\n[bold red]Risk:[/bold] {r_desc}")
            if alt:
                safer_alts.append(f"[bold green]Safer Alternative:[/bold] {alt}")
        elif r_level == "moderate" and highest_risk != "destructive":
            highest_risk = "moderate"

    # Handle dry run
    if dry_run:
        print_info("Dry-run mode: execution skipped.")
        raise typer.Exit(code=0)

    # Confirmation flow
    if highest_risk == "destructive":
        if yes:
            print_warning("Executing destructive commands due to --yes flag.")
        else:
            show_warning_panel(
                "\n\n".join(risk_details) + ("\n\n" + "\n".join(safer_alts) if safer_alts else ""),
                "⚠️ DESTRUCTIVE OPERATION DETECTED"
            )
            if not confirm("Are you sure you want to execute these destructive commands?", default=False):
                print_info("Execution aborted.")
                raise typer.Exit(code=0)
    elif highest_risk == "moderate":
        if not yes:
            if not confirm("Do you want to execute this plan?", default=True):
                print_info("Execution aborted.")
                raise typer.Exit(code=0)
    # Safe commands execute directly

    # Execute commands
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
                    res = git_ops.execute(cmd)
                    outputs.append(res)
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
    if highest_risk == "safe" and combined_output.strip():
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

@app.command(name="commit", help="Generate a smart commit message from staged changes and commit.")
def commit_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
    format_override: Optional[str] = typer.Option(
        None, "--format", "-f", help="Override commit format (conventional, simple, detailed)"
    ),
):
    if not isinstance(format_override, str):
        format_override = None

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
    msg = None
    
    while True:
        if not msg:
            try:
                get_llm(offline_override=offline)
                with spinner("Analyzing changes and generating commit message..."):
                    msg = generator.generate_message(format_type=format_type, offline=offline)
            except NoStagedChangesError as e:
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
                show_error_panel(f"Push failed: {e}", "Git Push Error")
    else:
        # Upstream exists
        msg_push = f"Push to upstream branch '{upstream}'? (Your branch is {ahead} commit(s) ahead of remote)"
        if confirm(msg_push, default=True):
            try:
                # Find the remote name from upstream (e.g. 'origin/main' -> 'origin')
                remote_name = upstream.split("/")[0] if "/" in upstream else "origin"
                with spinner(f"Pushing to {upstream}..."):
                    push_res = git_ops.push(remote=remote_name)
                print_success("Pushed to remote successfully!")
                console.print(f"[dim]{push_res}[/dim]")
            except Exception as e:
                show_error_panel(f"Push failed: {e}", "Git Push Error")

@app.command(name="setup", help="Initial configuration wizard for Ace.")
def setup_cmd():
    import click
    from ace.ui.banner import animate_fire_banner
    
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
):
    if not isinstance(file, str):
        file = None
    if not isinstance(branch, str):
        branch = None

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

@app.command(name="resolve", help="AI-assisted merge conflict resolution.")
def resolve_cmd(
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
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
        show_error_panel(f"Failed to generate changelog: {e}", "AI Error")
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


@app.command(name="explain", help="Explain a Git command, flag, concept, or error in plain English.")
def explain_cmd(
    query: str = typer.Argument(..., help="Git command, option, error, or concept to explain"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
    from ace.ai.prompts.explain import EXPLAIN_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    from langchain_core.messages import SystemMessage, HumanMessage
    from rich.markdown import Markdown

    # Resolve LLM
    try:
        llm = get_llm(offline_override=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)

    usr_prompt = USER_PROMPT_TEMPLATE.format(query=query)
    messages = [
        SystemMessage(content=EXPLAIN_SYSTEM_PROMPT),
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
    from langchain_core.messages import SystemMessage, HumanMessage
    from ace.utils.json_utils import extract_json

    # Resolve LLM
    try:
        llm = get_llm(offline_override=offline)
    except LLMConfigurationError as e:
        show_error_panel(f"{str(e)}\n\nRun [bold]ace setup[/bold] to configure your AI credentials.", "Configuration Error")
        raise typer.Exit(code=1)

    usr_prompt = USER_PROMPT_TEMPLATE.format(
        git_state=git_state_desc,
        staged_files=staged,
        unstaged_files=unstaged,
        reflog_entries=reflog
    )

    messages = [
        SystemMessage(content=UNDO_SYSTEM_PROMPT),
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
            risk_details.append(f"[bold red]Command:[/bold] {cmd}\n[bold red]Risk:[/bold] {r_desc}")
            if alt:
                safer_alts.append(f"[bold green]Safer Alternative:[/bold] {alt}")
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
        show_error_panel(f"Failed to generate PR description: {e}", "AI Error")
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

@app.command(name="ignore", help="Smart gitignore generation and template addition.")
def ignore_cmd(
    query: str = typer.Argument(..., help="What to ignore (e.g. 'node_modules', 'temp files')"),
    offline: bool = typer.Option(False, "--offline", help="Force Ollama offline mode"),
):
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
    try:
        git_ops = GitOps()
    except NotAGitRepositoryError as e:
        show_error_panel(str(e), "Git Error")
        raise typer.Exit(code=1)

    files_str = " ".join(files)
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

if __name__ == "__main__":
    app()




