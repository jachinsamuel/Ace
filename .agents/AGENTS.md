# Custom Rules for Ace Workspace

Whenever a new version of Ace is created (e.g., version incremented in `pyproject.toml` or when releasing a new tag), we must build the package and publish the updated release to PyPI (pip) so that users can install the latest package.

## Publishing Steps
1. Increment the version number in [pyproject.toml](file:///d:/Ace/pyproject.toml).
2. Clean previous build artifacts from `dist/`.
3. Build the wheel and source distribution:
   ```bash
   python -m build
   ```
   *(or using `hatch build` / `poetry build` as appropriate)*
4. Upload the built packages to PyPI using twine:
   ```bash
   twine upload dist/*
   ```
