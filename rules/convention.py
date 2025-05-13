"""
Coding Convention Rules Module
Enforces PEP8 and project-specific style guidelines
"""

import libcst as cst
from libcst import matchers as m
from typing import List, Dict, Any
from core.rule_engine import RuleBase


class NamingConventionRule(RuleBase):
    """
    Enforces snake_case naming for functions and variables
    """

    def __init__(self):
        self.snake_case_pattern = r'^[a-z_][a-z0-9_]*$'
        self.camel_case_pattern = r'^[A-Z][a-zA-Z0-9]*$'

    def apply(self, node: cst.Module) -> List[Dict[str, Any]]:
        issues = []

        # Match variable and function definitions
        var_matcher = m.Assign(
            targets=[m.AssignTarget(target=m.Name())]
        ) & m.MatchIfTrue(lambda n: not self._is_snake_case(n.targets[0].target.value))

        func_matcher = m.FunctionDef(
            name=m.Name()
        ) & m.MatchIfTrue(lambda n: not self._is_snake_case(n.name.value))

        # Check variables
        for match in m.findall(node, var_matcher):
            issues.append({
                'rule': 'naming_convention',
                'message': f"Variable name '{match.targets[0].target.value}' should be snake_case",
                'line': match.lineno,
                'column': match.col_offset,
                'severity': 'warning',
                'fix_type': 'rename',
                'suggestion': self._to_snake_case(match.targets[0].target.value),
                'node': match
            })

        # Check functions
        for match in m.findall(node, func_matcher):
            issues.append({
                'rule': 'naming_convention',
                'message': f"Function name '{match.name.value}' should be snake_case",
                'line': match.lineno,
                'column': match.col_offset,
                'severity': 'warning',
                'fix_type': 'rename',
                'suggestion': self._to_snake_case(match.name.value),
                'node': match
            })

        return issues

    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention"""
        import re
        return bool(re.match(self.snake_case_pattern, name))

    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase/PascalCase to snake_case"""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


class UnusedImportRule(RuleBase):
    """
    Detects unused imports in Python modules
    """

    def apply(self, node: cst.Module) -> List[Dict[str, Any]]:
        issues = []

        # Track all imports and their usage
        imports = {}
        used_names = set()

        # First collect all imports
        for imp in m.findall(node, m.Import() | m.ImportFrom()):
            if m.matches(imp, m.Import()):
                for name in imp.names:
                    alias = name.asname.name.value if name.asname else name.name.value
                    imports[alias] = imp
            else:
                module = imp.module.value if imp.module else ""
                for name in imp.names:
                    full_name = f"{module}.{name.name.value}"
                    alias = name.asname.name.value if name.asname else name.name.value
                    imports[alias] = imp

        # Then collect all used names
        for name_node in m.findall(node, m.Name()):
            used_names.add(name_node.value)

        # Find unused imports
        for alias, imp in imports.items():
            if alias not in used_names:
                issues.append({
                    'rule': 'unused_import',
                    'message': f"Unused import: {alias}",
                    'line': imp.lineno,
                    'column': imp.col_offset,
                    'severity': 'warning',
                    'fix_type': 'remove',
                    'suggestion': "Remove this unused import",
                    'node': imp
                })

        return issues