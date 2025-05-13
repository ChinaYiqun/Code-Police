"""
Performance Optimization Rules Module
Identifies inefficient code patterns in Python
"""

import libcst as cst
from libcst import matchers as m
from typing import List, Dict, Any
from core.rule_engine import RuleBase


class NestedListComprehensionRule(RuleBase):
    """
    Detects deeply nested list comprehensions that reduce readability
    Example: [[x*y for x in range(10)] for y in range(10)]
    """

    def __init__(self, max_depth=2):
        self.max_depth = max_depth

    def apply(self, node: cst.Module) -> List[Dict[str, Any]]:
        issues = []

        # Match list comprehensions with nested structure
        nested_list_matcher = m.ListComp(
            for_in=m.Comprehension(
                iter=m.Comprehension()
            )
        )

        for match in m.findall(node, nested_list_matcher):
            # Count nesting depth
            depth = self._count_nesting(match)

            if depth > self.max_depth:
                issues.append({
                    'rule': 'nested_list_comprehension',
                    'message': f"Nested list comprehension with depth {depth} (max allowed: {self.max_depth})",
                    'line': match.lineno,
                    'column': match.col_offset,
                    'severity': 'warning',
                    'fix_type': 'refactor',
                    'suggestion': "Refactor into regular loops for better readability",
                    'node': match
                })

        return issues

    def _count_nesting(self, node: cst.ListComp) -> int:
        """Calculate nesting depth of list comprehension"""
        count = 0
        current = node.for_in
        while hasattr(current, 'iter') and isinstance(current.iter, cst.Comprehension):
            count += 1
            current = current.iter
        return count + 1


class RepeatedCalculationRule(RuleBase):
    """
    Detects repeated calculations in loops
    Example: [expensive_func() for _ in range(100)]
    """

    def apply(self, node: cst.Module) -> List[Dict[str, Any]]:
        issues = []

        # Match list comprehensions with function calls
        repeated_call_matcher = m.ListComp(
            element=m.Call()
        )

        for match in m.findall(node, repeated_call_matcher):
            # Check if same function is called multiple times
            func_name = getattr(match.element.func, 'value', None)
            if func_name:
                issues.append({
                    'rule': 'repeated_calculation',
                    'message': f"Repeated call to {func_name} in list comprehension",
                    'line': match.lineno,
                    'column': match.col_offset,
                    'severity': 'warning',
                    'fix_type': 'refactor',
                    'suggestion': "Move the calculation outside the loop",
                    'node': match
                })

        return issues