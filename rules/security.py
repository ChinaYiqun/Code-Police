"""
Security Rules Module for CodePolice
Detects security vulnerabilities in Python code
"""

import libcst as cst
from libcst import matchers as m
from typing import List, Dict, Any
from core.rule_engine import RuleBase


class HardcodedSecretRule(RuleBase):
    """
    Detects hardcoded secrets in variable assignments
    Example: password = "123456"
    """

    def __init__(self):
        self.secrets_keywords = ['password', 'secret', 'token', 'key']

    def apply(self, node: cst.Module) -> List[Dict[str, Any]]:
        issues = []

        # Define matcher for assignment with string value
        secret_matcher = m.Assign(
            value=m.SimpleString()
        ) & m.MatchIfTrue(lambda n: any(
            keyword in getattr(n.targets[0].target, 'value', '').lower()
            for keyword in self.secrets_keywords
        ))

        # Find all matches in AST
        for match in m.findall(node, secret_matcher):
            issues.append({
                'rule': 'hardcoded_secret',
                'message': f"Hardcoded secret detected in {match.targets[0].target.value}",
                'line': match.lineno,
                'column': match.col_offset,
                'severity': 'error',
                'fix_type': 'replace',
                'suggestion': 'Use environment variables instead (os.getenv)',
                'node': match
            })

        return issues


class UnsafeEvalRule(RuleBase):
    """
    Detects dangerous use of eval() function
    Example: eval(input("Enter code: "))
    """

    def apply(self, node: cst.Module) -> List[Dict[str, Any]]:
        issues = []

        # Match eval function calls
        eval_matcher = m.Call(
            func=m.Name("eval")
        )

        for match in m.findall(node, eval_matcher):
            issues.append({
                'rule': 'unsafe_eval',
                'message': "Potential code execution vulnerability through eval()",
                'line': match.lineno,
                'column': match.col_offset,
                'severity': 'error',
                'fix_type': 'remove',
                'suggestion': "Replace with ast.literal_eval() or input validation",
                'node': match
            })

        return issues