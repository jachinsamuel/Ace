# Contributing to Ace

Thank you for your interest in contributing to Ace! This project is an open-source, AI-powered Git Copilot, and we welcome contributions of all forms—bug reports, feature requests, documentation improvements, and code changes.

Please read through these guidelines to understand how you can participate and help make Ace better.

---

## 🛠️ Setting Up the Development Environment

Ace is written in Python ($>=3.11$) and uses standard packaging tools. Follow these steps to set up your local development environment:

1. **Fork and Clone the Repository**
   Fork the repository on GitHub and clone your fork locally:
   ```bash
   git clone https://github.com/your-username/Ace.git
   cd Ace
   ```

2. **Set Up a Virtual Environment**
   Create and activate a virtual environment to isolate project dependencies:
   ```bash
   # Create environment
   python -m venv .venv

   # Activate on Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1

   # Activate on Windows (CMD)
   .\.venv\Scripts\activate.bat

   # Activate on macOS / Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   Install the package in editable mode along with development dependencies:
   ```bash
   pip install -e .[dev]
   ```

4. **Verify the Installation**
   Run the CLI directly to ensure everything is set up correctly:
   ```bash
   ace --help
   ```

---

## 🧪 Testing Guidelines

Ace uses **pytest** for unit and integration testing. We require all code changes to be accompanied by corresponding tests, and all existing tests must pass before a pull request can be merged.

* **Run the complete test suite:**
  ```bash
  pytest
  ```
* **Run tests with coverage report:**
  ```bash
  pytest --cov=ace
  ```

Test files are located in the [tests/](file:///d:/Projects/Ace/tests) directory. If you are adding a new feature or command, please create a new test file under `tests/test_<feature_name>.py`.

---

## 🎨 Code Style and Standards

We maintain high code quality standards to keep the codebase clean, readable, and maintainable.

### Linting and Formatting
We use **Ruff** for fast linting and formatting.
* **Run linting checks:**
  ```bash
  ruff check
  ```
* **Auto-fix linting errors:**
  ```bash
  ruff check --fix
  ```
* **Format the code:**
  ```bash
  ruff format
  ```

Ensure that both `ruff check` and `ruff format --check` pass without errors before committing.

---

## 💬 Commit Message Convention

We follow the **Conventional Commits** specification for clear, readable, and automated changelogs. Commit messages should be structured as follows:

```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
* `feat`: A new user-facing feature.
* `fix`: A bug fix.
* `docs`: Documentation changes only.
* `style`: Code style changes (formatting, missing semi-colons, no functional changes).
* `refactor`: A code change that neither fixes a bug nor adds a feature.
* `test`: Adding missing tests or correcting existing tests.
* `chore`: Updating build tasks, package manager configs, version bumps, etc.

### Example
```text
feat(cli): add doctor command to diagnose repository state
```

---

## 🚀 The Pull Request Process

1. **Create a branch** for your work from `master` (or `main`):
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Implement your changes**, write tests, and ensure code styles pass.
3. **Commit your work** using conventional commit messages.
4. **Push the branch** to your GitHub fork:
   ```bash
   git push origin feat/your-feature-name
   ```
5. **Open a Pull Request** against the main repository. Fill out the PR template with clear descriptions of what changes were made and why.
6. **Address Review Feedback**: Maintainers will review your PR and may request changes. Be prepared to update your PR based on suggestions.

---

## ⚠️ Important Release Rule
> [!IMPORTANT]
> **Do not push git release tags (e.g. `v0.2.x`) to the main GitHub repository.** Package release tagging is handled strictly by project maintainers. Only push code changes via your pull requests.
