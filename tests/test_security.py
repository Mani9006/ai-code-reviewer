"""Tests for security rule checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ast_parser import ASTParser
from src.config import Config


class TestSecurityRules:
    """Test cases for security rule checks."""

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create test parser."""
        return ASTParser()

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config()

    def test_dangerous_eval(self, parser: ASTParser, config: Config) -> None:
        """Test detection of eval() calls."""
        code = '''
"""Test module."""

def process(data):
    """Process data."""
    return eval(data)
'''
        module = parser.parse_source(code)
        from src.rules import security
        issues = security.check(module, config, Path("test.py"))

        eval_issues = [i for i in issues if "eval" in i.rule]
        assert len(eval_issues) > 0

    def test_hardcoded_password(self, parser: ASTParser, config: Config, tmp_path: Path) -> None:
        """Test detection of hardcoded passwords."""
        code = '''
"""Test module."""

password = "super_secret_password_123"
api_key = "sk-1234567890abcdef"
'''
        test_file = tmp_path / "secrets.py"
        test_file.write_text(code, encoding="utf-8")
        module = parser.parse_file(test_file)
        from src.rules import security
        issues = security.check(module, config, test_file)

        secret_issues = [i for i in issues if "hardcoded" in i.rule]
        assert len(secret_issues) >= 2

    def test_sql_injection(self, parser: ASTParser, config: Config, tmp_path: Path) -> None:
        """Test detection of SQL injection patterns."""
        code = '''
"""Test module."""

def query(user_id):
    """Query database."""
    sql = "SELECT * FROM users WHERE id = " + str(user_id)
    return sql
'''
        test_file = tmp_path / "sql.py"
        test_file.write_text(code, encoding="utf-8")
        module = parser.parse_file(test_file)
        from src.rules import security
        issues = security.check(module, config, test_file)

        sql_issues = [i for i in issues if "sql" in i.rule]
        assert len(sql_issues) > 0

    def test_wildcard_import(self, parser: ASTParser, config: Config) -> None:
        """Test detection of wildcard imports."""
        code = '''
"""Test module."""

from os import *
from module import *
'''
        module = parser.parse_source(code)
        from src.rules import security
        issues = security.check(module, config, Path("test.py"))

        wildcard_issues = [i for i in issues if i.rule == "wildcard_import"]
        assert len(wildcard_issues) > 0

    def test_weak_hash(self, parser: ASTParser, config: Config) -> None:
        """Test detection of weak hash algorithms."""
        code = '''
"""Test module."""

import hashlib

def hash_data(data):
    """Hash data."""
    return hashlib.md5(data.encode()).hexdigest()
'''
        module = parser.parse_source(code)
        from src.rules import security
        issues = security.check(module, config, Path("test.py"))

        hash_issues = [i for i in issues if i.rule == "weak_hash_algorithm"]
        assert len(hash_issues) > 0

    def test_safe_code_passes(self, parser: ASTParser, config: Config) -> None:
        """Test that safe code passes."""
        code = '''
"""Test module."""

import json

def process(data):
    """Process data safely."""
    return json.loads(data)
'''
        module = parser.parse_source(code)
        from src.rules import security
        issues = security.check(module, config, Path("test.py"))

        # Safe code should not trigger security issues
        assert all(i.rule != "dangerous_eval_call" for i in issues)


class TestSecurityDetectors:
    """Test cases for security risk detectors."""

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create test parser."""
        return ASTParser()

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config()

    def test_command_injection(self, parser: ASTParser, config: Config) -> None:
        """Test detection of command injection."""
        code = '''
"""Test module."""

import subprocess

def run(user_input):
    """Run command."""
    return subprocess.run(user_input, shell=True)
'''
        module = parser.parse_source(code)
        from src.detectors import security_risks
        issues = security_risks.detect(module, config)

        cmd_issues = [i for i in issues if i.rule == "command_injection"]
        assert len(cmd_issues) > 0

    def test_insecure_random(self, parser: ASTParser, config: Config) -> None:
        """Test detection of insecure random."""
        code = '''
"""Test module."""

import random

def pick():
    """Pick random."""
    return random.randint(1, 100)
'''
        module = parser.parse_source(code)
        from src.detectors import security_risks
        issues = security_risks.detect(module, config)

        random_issues = [i for i in issues if i.rule == "insecure_random"]
        assert len(random_issues) > 0

    def test_debug_mode(self, parser: ASTParser, config: Config) -> None:
        """Test detection of debug mode."""
        code = '''
"""Test module."""

debug = True
is_debug = True
'''
        module = parser.parse_source(code)
        from src.detectors import security_risks
        issues = security_risks.detect(module, config)

        debug_issues = [i for i in issues if i.rule == "debug_mode_enabled"]
        assert len(debug_issues) > 0

    def test_except_pass(self, parser: ASTParser, config: Config) -> None:
        """Test detection of except: pass."""
        code = '''
"""Test module."""

def risky():
    """Risky function."""
    try:
        something()
    except:
        pass
'''
        module = parser.parse_source(code)
        from src.detectors import anti_patterns
        issues = anti_patterns.detect(module, config)

        pass_issues = [i for i in issues if i.rule == "except_pass"]
        assert len(pass_issues) > 0

    def test_string_is_comparison(self, parser: ASTParser, config: Config) -> None:
        """Test detection of string 'is' comparison."""
        code = '''
"""Test module."""

def check(name):
    """Check name."""
    if name is "admin":
        return True
    return False
'''
        module = parser.parse_source(code)
        from src.detectors import anti_patterns
        issues = anti_patterns.detect(module, config)

        is_issues = [i for i in issues if i.rule == "string_is_comparison"]
        assert len(is_issues) > 0

    def test_type_vs_isinstance(self, parser: ASTParser, config: Config) -> None:
        """Test detection of type() vs isinstance()."""
        code = '''
"""Test module."""

def check(x):
    """Check type."""
    if type(x) is dict:
        return True
    return False
'''
        module = parser.parse_source(code)
        from src.detectors import anti_patterns
        issues = anti_patterns.detect(module, config)

        type_issues = [i for i in issues if i.rule == "type_vs_isinstance"]
        assert len(type_issues) > 0
