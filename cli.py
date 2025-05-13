"""
Command Line Interface for CodePolice
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import asdict
import logging
import importlib.util

# Local imports
try:
    from core.parser import CodeParser
    from core.rule_engine import RuleEngine
    from core.fixer import CodeFixer
    from integrations.git_hook import GitHookManager
    from models.copilot_proxy import CopilotFixer, load_copilot_config
except ImportError:
    # Fallback for direct script execution
    from parser import CodeParser
    from rule_engine import RuleEngine
    from fixer import CodeFixer
    from integrations.git_hook import GitHookManager
    from models.copilot_proxy import CopilotFixer, load_copilot_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CodePoliceCLI")


class CLI:
    """
    Main CLI class for CodePolice
    """

    def __init__(self):
        self.parser = self._create_parser()
        self.args = self.parser.parse_args()
        self.config = self._load_config()
        self.rule_engine = RuleEngine()

        # Initialize optional modules
        self.copilot = None
        if self.config.get('use_copilot', True):
            try:
                self.copilot = CopilotFixer(load_copilot_config())
            except Exception as e:
                logger.warning(f"Copilot initialization failed: {e}")

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser"""
        parser = argparse.ArgumentParser(
            description="CodePolice - Intelligent Code Quality Gatekeeper",
            formatter_class=argparse.RawTextHelpFormatter
        )

        subparsers = parser.add_subparsers(dest='command', required=True)

        # Check command
        check_parser = subparsers.add_parser('check', help='Check code quality')
        check_parser.add_argument('path', nargs='?', default='.', help='Path to check (file or directory)')
        check_parser.add_argument('--format', choices=['text', 'json', 'html'], default='text', help='Output format')
        check_parser.add_argument('--output', type=str, help='Output file path')
        check_parser.add_argument('--no-copilot', action='store_true', help='Disable AI suggestions')
        check_parser.add_argument('--list-rules', action='store_true', help='List all available rules')

        # Fix command
        fix_parser = subparsers.add_parser('fix', help='Apply automatic fixes')
        fix_parser.add_argument('path', nargs='?', default='.', help='Path to fix')
        fix_parser.add_argument('--apply', action='store_true', help='Apply fixes (dry run by default)')
        fix_parser.add_argument('--only', type=str, help='Apply only specific rule (e.g., unused_import)')

        # Hook command
        hook_parser = subparsers.add_parser('hook', help='Manage Git hooks')
        hook_subparsers = hook_parser.add_subparsers(dest='hook_command', required=True)
        hook_subparsers.add_parser('install', help='Install Git pre-commit hook')
        hook_subparsers.add_parser('uninstall', help='Uninstall Git pre-commit hook')

        # Config command
        config_parser = subparsers.add_parser('config', help='Manage configuration')
        config_subparsers = config_parser.add_subparsers(dest='config_command', required=True)
        config_subparsers.add_parser('show', help='Show current configuration')
        config_subparsers.add_parser('init', help='Initialize configuration file')

        return parser

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or defaults"""
        config_path = Path("codepolice.yaml")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")

        return {
            "use_copilot": True,
            "default_rules": ["security", "performance", "convention"]
        }

    def run(self) -> int:
        """Execute command based on parsed arguments"""
        try:
            if self.args.command == 'check':
                return self._run_check()
            elif self.args.command == 'fix':
                return self._run_fix()
            elif self.args.command == 'hook':
                return self._run_hook()
            elif self.args.command == 'config':
                return self._run_config()
            else:
                self.parser.print_help()
                return 1
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return 130

    def _run_check(self) -> int:
        """Run code quality checks"""
        from core.parser import CodeParser

        # List rules if requested
        if self.args.list_rules:
            self._list_rules()
            return 0

        # Process files
        path = Path(self.args.path)
        issues = []

        if path.is_dir():
            for py_file in path.rglob("*.py"):
                parser = CodeParser(str(py_file))
                module = parser.get_ast()
                issues.extend(self.rule_engine.run_rules(module))
        else:
            parser = CodeParser(str(path))
            module = parser.get_ast()
            issues.extend(self.rule_engine.run_rules(module))

        # Apply Copilot suggestions if enabled
        if self.copilot and not self.args.no_copilot:
            for issue in issues:
                if hasattr(parser, 'get_code_snippet'):
                    snippet = parser.get_code_snippet(issue['node'])
                    issue['ai_suggestion'] = self.copilot.get_suggestion(snippet)

        # Output results
        self._output_results(issues)

        return 1 if issues else 0

    def _run_fix(self) -> int:
        """Apply automatic fixes"""
        from core.parser import CodeParser
        from core.fixer import CodeFixer

        path = Path(self.args.path)
        if not path.exists():
            logger.error(f"Path not found: {path}")
            return 1

        # Process files
        if path.is_dir():
            files = path.rglob("*.py")
        else:
            files = [path]

        for py_file in files:
            parser = CodeParser(str(py_file))
            module = parser.get_ast()
            issues = self.rule_engine.run_rules(module)

            if issues:
                print(f"\nProcessing {py_file}:")

                # Filter issues if --only specified
                if self.args.only:
                    issues = [i for i in issues if i['rule'] == self.args.only]

                fixer = CodeFixer(module)
                fixed_module = fixer.apply_fixes(issues)

                # Show diff
                diff = fixer.generate_diff()
                print(diff)

                # Write changes
                if self.args.apply:
                    with open(py_file, 'w') as f:
                        f.write(fixed_module.code)
                    print(f"✅ Applied fixes to {py_file}")
                else:
                    print("💡 Use --apply to apply these changes")

        return 0

    def _run_hook(self) -> int:
        """Manage Git hooks"""
        if self.args.hook_command == 'install':
            GitHookManager.install()
        elif self.args.hook_command == 'uninstall':
            GitHookManager.uninstall()
        return 0

    def _run_config(self) -> int:
        """Manage configuration"""
        config_path = Path("codepolice.yaml")

        if self.args.config_command == 'show':
            if config_path.exists():
                with open(config_path, 'r') as f:
                    print(f.read())
            else:
                print("No configuration file found")
            return 0

        elif self.args.config_command == 'init':
            default_config = {
                "rules": {
                    "hardcoded_secret": {"level": "error"},
                    "unused_import": {"level": "warning"}
                }
            }

            with open(config_path, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            print(f"✅ Created configuration file at {config_path}")
            return 0

        return 0

    def _list_rules(self) -> None:
        """List all available rules"""
        print("Available Rules:")
        print("=" * 30)

        # Example rule structure - should be loaded from actual rules
        rules = {
            "security": [
                "hardcoded_secret",
                "unsafe_eval"
            ],
            "performance": [
                "nested_list_comprehension",
                "repeated_calculation"
            ],
            "convention": [
                "naming_convention",
                "unused_import"
            ]
        }

        for category, rule_list in rules.items():
            print(f"\n{category.capitalize()}:")
            for rule in rule_list:
                print(f"  - {rule}")

    def _output_results(self, issues: List[Dict]) -> None:
        """Output results in specified format"""
        if self.args.format == 'json':
            output = json.dumps(issues, indent=2)
        elif self.args.format == 'html':
            output = self._generate_html_report(issues)
        else:
            output = self._generate_text_report(issues)

        # Print or save to file
        if self.args.output:
            with open(self.args.output, 'w') as f:
                f.write(output)
            print(f"✅ Report saved to {self.args.output}")
        else:
            print(output)

    def _generate_text_report(self, issues: List[Dict]) -> str:
        """Generate human-readable text report"""
        output = ""

        for issue in issues:
            node = issue.pop('node', None)
            location = f"{issue['line']}:{issue['column']}"
            color = "\033[91m" if issue['severity'] == 'error' else "\033[93m"
            reset = "\033[0m"

            output += f"{color}{issue['rule']} ({location}){reset}\n"
            output += f"  Message: {issue['message']}\n"
            output += f"  Suggestion: {issue['suggestion']}\n"
            output += "-" * 50 + "\n"

        return output

    def _generate_html_report(self, issues: List[Dict]) -> str:
        """Generate HTML formatted report"""
        template = """
<!DOCTYPE html>
<html>
<head>
    <title>CodePolice Report</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .issue { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; }
        .rule { font-weight: bold; color: #2c3e50; }
        .location { color: #7f8c8d; float: right; }
        .message { margin-top: 10px; }
        .suggestion { margin-top: 10px; color: #27ae60; }
    </style>
</head>
<body>
    <h1>CodePolice Report</h1>
    <p>Total Issues: {total}</p>

    {issues}
</body>
</html>
"""

        issue_template = """
<div class="issue">
    <div class="rule">{rule} <span class="location">Line {line}:{column}</span></div>
    <div class="message">{message}</div>
    <div class="suggestion">Suggestion: {suggestion}</div>
</div>
"""

        html_issues = ""
        for issue in issues:
            html_issues += issue_template.format(**issue)

        return template.format(
            total=len(issues),
            issues=html_issues
        )


# Main entry point
if __name__ == "__main__":
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is required for CodePolice")
        print("Please install it using: pip install pyyaml")
        sys.exit(1)

    cli = CLI()
    sys.exit(cli.run())