"""Tests for naming convention rule checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ast_parser import ASTParser
from src.config import Config


class TestNamingRules:
    """Test cases for naming rule checks."""

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create test parser."""
        return ASTParser()

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config()

    def test_invalid_function_name(self, parser: ASTParser, config: Config) -> None:
        """Test detection of invalid function names."""
        code = '''
"""Test module."""

def InvalidFunctionName():
    """Invalid name."""
    pass
'''
        module = parser.parse_source(code)
        from src.rules import naming
        issues = naming.check(module, config, Path("test.py"))

        naming_issues = [i for i in issues if i.rule == "invalid_function_name"]
        assert len(naming_issues) > 0

    def test_invalid_class_name(self, parser: ASTParser, config: Config) -> None:
        """Test detection of invalid class names."""
        code = '''
"""Test module."""

class invalid_class_name:
    """Invalid class name."""
    pass
'''
        module = parser.parse_source(code)
        from src.rules import naming
        issues = naming.check(module, config, Path("test.py"))

        class_issues = [i for i in issues if i.rule == "invalid_class_name"]
        assert len(class_issues) > 0

    def test_builtin_shadowing(self, parser: ASTParser, config: Config) -> None:
        """Test detection of built-in name shadowing."""
        code = '''
"""Test module."""

def list(items):
    """Shadow built-in."""
    return items
'''
        module = parser.parse_source(code)
        from src.rules import naming
        issues = naming.check(module, config, Path("test.py"))

        shadow_issues = [i for i in issues if i.rule == "builtin_shadowing"]
        assert len(shadow_issues) > 0

    def test_single_char_names(self, parser: ASTParser, config: Config) -> None:
        """Test detection of single character names."""
        code = '''
"""Test module."""

def func(a, b, x):
    """Function with short names."""
    return a + b + x
'''
        module = parser.parse_source(code)
        from src.rules import naming
        issues = naming.check(module, config, Path("test.py"))

        char_issues = [i for i in issues if i.rule == "single_char_name"]
        assert len(char_issues) > 0

    def test_valid_names_pass(self, parser: ASTParser, config: Config) -> None:
        """Test that valid names pass."""
        code = '''
"""Test module."""

class ValidClass:
    """A valid class."""

    def valid_method(self, param_name):
        """A valid method."""
        return param_name

def valid_function():
    """A valid function."""
    local_var = 1
    return local_var
'''
        module = parser.parse_source(code)
        from src.rules import naming
        issues = naming.check(module, config, Path("test.py"))

        # Valid names should not trigger rules
        assert all(i.rule != "invalid_function_name" for i in issues)
        assert all(i.rule != "invalid_class_name" for i in issues)

    def test_module_name_naming(self, parser: ASTParser, config: Config) -> None:
        """Test detection of invalid module-level names."""
        code = '''
"""Test module."""

def someFunction():
    """CamelCase function."""
    pass
'''
        module = parser.parse_source(code)
        from src.rules import naming
        # Use a filepath with invalid module name
        issues = naming.check(module, config, Path("InvalidModule.py"))

        mod_issues = [i for i in issues if i.rule == "invalid_module_name"]
        assert len(mod_issues) > 0

    def test_dunder_methods_allowed(self, parser: ASTParser, config: Config) -> None:
        """Test that dunder methods are allowed."""
        code = '''
"""Test module."""

class MyClass:
    """A class."""

    def __init__(self):
        pass

    def __str__(self):
        return "MyClass"

    def __repr__(self):
        return "MyClass()"
'''
        module = parser.parse_source(code)
        from src.rules import naming
        issues = naming.check(module, config, Path("test.py"))

        dunder_issues = [i for i in issues if "invalid" in i.rule.lower()]
        assert all(
            "dunder" not in i.message.lower() for i in dunder_issues
        )
