"""
AST Parser Module for CodePolice
Uses LibCST to parse Python code into AST and traverse nodes
"""

import libcst as cst
from pathlib import Path
from typing import Dict, List, Optional


class CodeParser:
    """
    Handles parsing of Python code files into AST structures
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.source_code = self._read_file()
        self.module = self._parse_module()

    def _read_file(self) -> str:
        """Read source code from file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read {self.file_path}: {e}")

    def _parse_module(self) -> cst.Module:
        """Parse source code into CST Module AST"""
        try:
            return cst.parse_module(self.source_code)
        except Exception as e:
            raise RuntimeError(f"AST parsing error in {self.file_path}: {e}")

    def get_ast(self) -> cst.Module:
        """Return the parsed AST module"""
        return self.module

    def traverse_nodes(self, visitor: cst.CSTVisitor) -> None:
        """
        Traverse AST nodes using provided visitor
        Args:
            visitor: LibCST visitor instance
        """
        self.module.visit(visitor)