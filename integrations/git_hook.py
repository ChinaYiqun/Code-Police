"""
Git Hook Integration for CodePolice
Implements pre-commit hook to enforce code quality checks
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


class GitHookManager:
    """
    Manages Git pre-commit hook installation/uninstallation
    """
    HOOK_PATH = Path(".git/hooks/pre-commit")
    BACKUP_PATH = Path(".git/hooks/pre-commit.bak")

    @classmethod
    def install(cls) -> None:
        """Install CodePolice pre-commit hook"""
        try:
            # Backup existing hook if exists
            if cls.HOOK_PATH.exists():
                cls.HOOK_PATH.rename(cls.BACKUP_PATH)
                print("⚠️ Backed up existing pre-commit hook")

            # Create new hook script
            hook_content = cls._generate_hook_script()
            with open(cls.HOOK_PATH, 'w') as f:
                f.write(hook_content)

            # Make it executable
            os.chmod(cls.HOOK_PATH, 0o755)
            print("✅ CodePolice pre-commit hook installed")

        except Exception as e:
            cls._handle_error("install", e)

    @classmethod
    def uninstall(cls) -> None:
        """Remove CodePolice hook and restore backup"""
        try:
            if cls.HOOK_PATH.exists():
                cls.HOOK_PATH.unlink()

            if cls.BACKUP_PATH.exists():
                cls.BACKUP_PATH.rename(cls.HOOK_PATH)
                print("✅ Restored original pre-commit hook")

        except Exception as e:
            cls._handle_error("uninstall", e)

    @classmethod
    def _generate_hook_script(cls) -> str:
        """Generate the hook script content"""
        return """#!/bin/sh
# CodePolice Git Pre-commit Hook

echo "🔍 Running CodePolice pre-commit check..."
# Get staged Python files
FILES=$(git diff --cached --name-only | grep -E '\\.py$')

if [ -z "$FILES" ]; then
    exit 0
fi

# Run code police check
codepolice check $FILES

# Check result
RESULT=$?
if [ $RESULT -ne 0 ]; then
    echo "❌ CodePolice check failed! Fix issues or use git commit --no-verify"
    exit $RESULT
fi

exit 0
"""

    @classmethod
    def _handle_error(cls, action: str, error: Exception) -> None:
        """Handle errors during hook management"""
        print(f"❌ Failed to {action} git hook: {str(error)}")
        sys.exit(1)


# Command line interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CodePolice Git Hook Manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("install", help="Install pre-commit hook")
    subparsers.add_parser("uninstall", help="Uninstall pre-commit hook")

    args = parser.parse_args()

    if args.command == "install":
        GitHookManager.install()
    elif args.command == "uninstall":
        GitHookManager.uninstall()
    else:
        parser.print_help()