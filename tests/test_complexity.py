"""Tests for complexity rule checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.analyzer import Issue
from src.ast_parser import ASTParser, ModuleInfo
from src.config import Config


class TestComplexityRules:
    """Test cases for complexity rule checks."""

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create test parser."""
        return ASTParser()

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config(
            max_cyclomatic_complexity=10,
            max_cognitive_complexity=15,
            max_function_parameters=5,
            max_class_methods=20,
            max_file_lines=500,
            max_function_length=50,
            max_nesting_depth=4,
        )

    def test_high_complexity_function(self, parser: ASTParser, config: Config) -> None:
        """Test detection of high cyclomatic complexity."""
        code = '''
"""Test module."""

def complex_function(x, y, z):
    """A complex function."""
    if x > 0 and y > 0:
        for i in range(10):
            if z > 0:
                if x + y > 10:
                    if x * y > 50 and z < 100:
                        try:
                            if x - y < 0:
                                return 1
                            return 2
                        except ValueError:
                            return 3
                    return 4
                return 5
            elif z < 0:
                while x < 100:
                    x += 1
                    if x > 50:
                        break
            return 6
    elif x < 0:
        return 7
    return 8
'''
        # Use a low threshold to ensure we get issues
        test_config = Config(
            max_cyclomatic_complexity=5,
            max_cognitive_complexity=15,
            max_function_parameters=5,
            max_class_methods=20,
            max_file_lines=500,
            max_function_length=50,
            max_nesting_depth=4,
        )
        module = parser.parse_source(code)
        from src.rules import complexity
        issues = complexity.check(module, test_config, Path("test.py"))

        complexity_issues = [i for i in issues if "complexity" in i.rule]
        assert len(complexity_issues) > 0

    def test_function_too_long(self, parser: ASTParser, config: Config) -> None:
        """Test detection of long functions."""
        code = '\n'.join(
            [f'"""Test module."""', 'def long_func():', '    """A long function."""']
            + [f'    x{i} = {i}' for i in range(60)]
            + ['    return x0']
        )
        module = parser.parse_source(code)
        from src.rules import complexity
        issues = complexity.check(module, config, Path("test.py"))

        length_issues = [i for i in issues if "function_too_long" in i.rule]
        assert len(length_issues) > 0

    def test_too_many_arguments(self, parser: ASTParser, config: Config) -> None:
        """Test detection of too many function arguments."""
        code = '''
"""Test module."""

def func(a, b, c, d, e, f, g):
    """Function with many args."""
    return a + b + c + d + e + f + g
'''
        module = parser.parse_source(code)
        from src.rules import complexity
        issues = complexity.check(module, config, Path("test.py"))

        arg_issues = [i for i in issues if "too_many_arguments" in i.rule]
        assert len(arg_issues) > 0

    def test_file_too_long(self, parser: ASTParser, config: Config) -> None:
        """Test detection of files that are too long."""
        code = '\n'.join(
            ['"""Test module."""']
            + [f'x{i} = {i}' for i in range(550)]
        )
        module = parser.parse_source(code)
        from src.rules import complexity
        issues = complexity.check(module, config, Path("test.py"))

        file_issues = [i for i in issues if "file_too_long" in i.rule]
        assert len(file_issues) > 0

    def test_too_many_class_methods(self, parser: ASTParser, config: Config) -> None:
        """Test detection of classes with too many methods."""
        methods = '\n'.join(
            f'    def method_{i}(self):\n        return {i}'
            for i in range(25)
        )
        code = f'"""Test module."""\n\nclass BigClass:\n    """A big class."""\n{methods}\n'
        module = parser.parse_source(code)
        from src.rules import complexity
        issues = complexity.check(module, config, Path("test.py"))

        method_issues = [i for i in issues if "too_many_methods" in i.rule]
        assert len(method_issues) > 0

    def test_clean_function_passes(self, parser: ASTParser, config: Config) -> None:
        """Test that clean functions pass."""
        code = '''
"""Test module."""

def simple_func(a, b):
    """A simple function.

    Args:
        a: First arg.
        b: Second arg.

    Returns:
        Sum of a and b.
    """
    if a > 0:
        return a + b
    return b
'''
        module = parser.parse_source(code)
        from src.rules import complexity
        issues = complexity.check(module, config, Path("test.py"))

        # Should not flag a simple function
        assert all(i.rule != "high_cyclomatic_complexity" for i in issues)
