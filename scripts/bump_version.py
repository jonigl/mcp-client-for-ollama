#!/usr/bin/env python3
"""
Version bumper for MCP Client for Ollama

This script bumps the version number in both the main package and the CLI package,
ensuring they stay in sync.
"""

import argparse
import os
import re
from pathlib import Path


def regenerate_uvlock(directory):
    """Regenerate the uv.lock file in the specified directory."""
    import subprocess
    try:
        subprocess.run(["uv", "lock"], cwd=directory, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print(f"Warning: Failed to regenerate uv.lock in {directory}")
        return False

def check_version_consistency(files):
    """Check if versions are consistent across all files."""
    versions = {}


    # Check pyproject.toml files
    for name, file_path in files.items():
        if "pyproject" in name and file_path.exists():
            try:
                versions[str(file_path)] = read_version(file_path)
            except ValueError:
                versions[str(file_path)] = "VERSION NOT FOUND"

    # Check __init__.py files
    for name, file_path in files.items():
        if "init" in name and file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
                if match:
                    versions[str(file_path)] = match.group(1)
                else:
                    versions[str(file_path)] = "VERSION NOT FOUND"
            except Exception:
                versions[str(file_path)] = "ERROR READING FILE"

    # Check if all versions match
    unique_versions = set(v for v in versions.values()
                        if v not in ["VERSION NOT FOUND", "ERROR READING FILE"])

    return unique_versions, versions

def read_version(file_path):
    """Read the current version from a pyproject.toml file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Use regex to find the version line
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not find version in {file_path}")


def bump_version(version, bump_type):
    """Bump a version number based on semantic versioning."""
    major, minor, patch = map(int, version.split('.'))

    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def update_version_in_file(file_path, new_version):
    """Update the version in a pyproject.toml file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Replace version in the version line - using a lambda for safe replacement
    version_pattern = re.compile(r'(version\s*=\s*)"([^"]+)"')
    updated_content = version_pattern.sub(lambda m: f'{m.group(1)}"{new_version}"', content)

    # Also update any dependency on the main package (for the CLI package)
    dep_pattern = re.compile(r'("mcp-client-for-ollama==)([^"]+)"')
    updated_content = dep_pattern.sub(lambda m: f'{m.group(1)}{new_version}"', updated_content)

    with open(file_path, 'w') as f:
        f.write(updated_content)


def update_version_in_init(init_path, new_version):
    """Update the __version__ in __init__.py files."""
    if os.path.exists(init_path):
        with open(init_path, 'r') as f:
            content = f.read()

        # Replace version in __version__ = "x.y.z" - using lambda for safe replacement
        version_pattern = re.compile(r'(__version__\s*=\s*)"([^"]+)"')
        updated_content = version_pattern.sub(lambda m: f'{m.group(1)}"{new_version}"', content)

        with open(init_path, 'w') as f:
            f.write(updated_content)


def main():
    parser = argparse.ArgumentParser(description="Bump version for MCP Client for Ollama packages")
    parser.add_argument(
        "bump_type",
        choices=["patch", "minor", "major", "custom"],
        help="The type of version bump to perform following semantic versioning, or 'custom' to specify a specific version"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--version",
        help="Custom version to set when using the 'custom' bump type"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force version bump even if inconsistencies are detected"
    )
    args = parser.parse_args()

    # Get repo root directory
    repo_root = Path(__file__).parent.parent.absolute()

    # Define paths
    files = {
        "main_pyproject": repo_root / "pyproject.toml",
        "cli_pyproject": repo_root / "cli-package" / "pyproject.toml",
        "main_init": repo_root / "mcp_client_for_ollama" / "__init__.py",
        "cli_init": repo_root / "cli-package" / "ollmcp" / "__init__.py"
    }

     # Calculate and check versions for consistency
    print("Checking version consistency across files...")
    unique_versions, all_versions = check_version_consistency(files)

    if len(unique_versions) > 1:
        print("\nWARNING: Version inconsistency detected!")
        print("The following files have different versions:")
        for file_path, version in all_versions.items():
            print(f"  - {file_path}: {version}")

        if not args.force:
            print("\nOperation aborted. Use --force to proceed with version bump despite inconsistencies.")
            return
        print("\nProceeding with version bump despite inconsistencies (--force flag used).")
    else:
        print("\nAll files have consistent versions.")

    # Read current version from main package
    main_pyproject = repo_root / "pyproject.toml"


    # Read current version
    current_version = read_version(main_pyproject)
    print(f"Current version: {current_version}")

    # Calculate new version
    if args.bump_type == "custom":
        if not args.version:
            parser.error("--version is required when using 'custom' bump type")
        new_version = args.version
        # Check if version is valid
        if not re.match(r'^\d+\.\d+\.\d+$', new_version):
            parser.error(f"Invalid version format: {new_version}. Expected format: X.Y.Z")
    else:
        new_version = bump_version(current_version, args.bump_type)

    print(f"New version: {new_version}")

    if args.dry_run:
        print("Dry run - no changes made.")
        return

    # Update versions
    print(f"Updating main package version in {main_pyproject}")
    update_version_in_file(main_pyproject, new_version)

    print(f"Updating CLI package version in {files['cli_pyproject']}")
    update_version_in_file(files['cli_pyproject'], new_version)

    # Update __version__ in __init__.py files if they exist
    print(f"Checking for __init__.py files...")
    update_version_in_init(files['main_init'], new_version)
    update_version_in_init(files['cli_init'], new_version)

    # Regenerate uv.lock files
    print("Regenerating uv.lock files...")
    regenerate_uvlock(repo_root)

    print(f"Version bump complete! {current_version} -> {new_version}")
    print("\nNext steps:")
    print("1. Commit the changes on the bump branch:")
    print("   git add -A")
    print(f"   git commit -m 'chore(release): bump version to {new_version}'")
    print("   Push the branch and create a pull request to main.")
    print("2. After PR is merged, checkout main branch and pull the latest changes.")
    print(f"3. Create a tag: git tag -a v{new_version} -m \"Version {new_version}\"")
    print("4. Push changes: git push && git push --tags")
    print("5. Build and publish the packages will be done automatically by CI/CD pipeline.")


if __name__ == "__main__":
    main()
