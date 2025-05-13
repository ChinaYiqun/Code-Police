"""
Rule Engine Module for CodePolice
Loads rules and applies them to AST nodes
"""

import yaml
from typing import Dict, List, Any
from pathlib import Path
from libcst import CSTNode


class RuleEngine:
    """
    Manages rule loading and execution against AST nodes
    """

    def __init__(self, config_path: str = "codepolice.yaml"):
        self.config_path = Path(config_path)
        self.rules = self._load_rules()
        self.issues = []  # Store detected issues

    def _load_rules(self) -> Dict[str, Any]:
        """Load rule configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f).get('rules', {})
        except Exception as e:
            raise RuntimeError(f"Failed to load rules: {e}")

    def apply_rules(self, node: CSTNode) -> None:
        """
        Apply all rules to the given AST node
        Args:
            node: AST node to analyze
        """
        for rule_name, rule_config in self.rules.items():
            if 'node_type' not in rule_config:
                continue

            # Convert node type string to LibCST class
            node_type = getattr(cst, rule_config['node_type'])

            if isinstance(node, node_type):
                self._check_rule(node, rule_name, rule_config)

    def _check_rule(self, node: CSTNode, rule_name: str, rule_config: dict) -> None:
        """
        Execute rule checks on specific node
        Args:
            node: AST node being analyzed
            rule_name: Name of current rule
            rule_config: Rule configuration dictionary
        """
        # Example implementation - should be replaced with actual rule logic
        if hasattr(node, 'value') and isinstance(node.value, str):
            if 'bad_pattern' in rule_config.get('options', {}):
                if rule_config['options']['bad_pattern'] in node.value:
                    issue = {
                        'rule': rule_name,
                        'message': rule_config['message'],
                        'line': node.lineno,
                        'column': node.col_offset,
                        'severity': rule_config.get('level', 'warning'),
                        'suggestion': rule_config.get('fix', 'No fix available')
                    }
                    self.issues.append(issue)