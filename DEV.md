## Development and Release Process

### Versioning

This project consists of two Python packages that must be kept in version sync:
- `mcp-client-for-ollama`: The main package
- `ollmcp`: The CLI package that depends on the main package

### Bumping Versions

To update versions for both packages simultaneously, use the provided script:

```bash
# For patch version (0.1.0 -> 0.1.1)
python scripts/bump_version.py patch

# For minor version (0.1.0 -> 0.2.0)
python scripts/bump_version.py minor

# For major version (0.1.0 -> 1.0.0)
python scripts/bump_version.py major

# For custom version
python scripts/bump_version.py custom --version X.Y.Z

# Preview changes without applying them
python scripts/bump_version.py patch --dry-run
```

The script automatically updates versions in:
- Main package `pyproject.toml`
- CLI package `pyproject.toml`
- `__init__.py` files
- CLI package dependency on main package

### Release Process

This project uses GitHub Actions for automated testing, building, publishing, and releasing:

1. **CI Workflow**:
   - Runs automatically on pushes to `main` and pull requests
   - Tests both packages with multiple Python versions
   - Checks package builds
   - Verifies version consistency across all files

2. **Release Workflow**:
   - Triggered by pushing a version tag (e.g., `v0.1.11`) or manually from GitHub
   - Extracts the version from project files
   - Builds and publishes both packages to PyPI
   - Creates a GitHub release with informative release notes

To create a new release:

1. Update versions using the bump script:
   ```bash
   python scripts/bump_version.py [patch|minor|major]
   ```

2. Commit the changes:
   ```bash
   git add -A
   git commit -m "chore(release): bump version to X.Y.Z"
   ```

3. Push the changes and create a tag:
   ```bash
   git tag -a vX.Y.Z -m "Version X.Y.Z"
   git push origin main --tags
   ```

4. The GitHub Actions workflow will automatically:
   - Build both packages
   - Publish to PyPI
   - Create a release on GitHub

Alternatively, you can manually trigger the release workflow from the GitHub Actions tab after pushing the version changes.
