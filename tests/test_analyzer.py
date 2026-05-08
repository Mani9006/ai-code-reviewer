"""Tests for the code analyzer."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.analyzer import CodeAnalyzer, FileReport, Issue, ReviewReport
from src.ast_parser import ASTParser, ModuleInfo
from src.config import Config


class TestIssue:
    """Test cases for the Issue dataclass."""

    def test_issue_creation(self) -> None:
        """Test creating an Issue."""
        issue = Issue(
            rule="test_rule",
            message="Test message",
            severity="warning",
            filepath="test.py",
            lineno=10,
            category="test",
            suggestion="Fix it",
        )
        assert issue.rule == "test_rule"
        assert issue.severity == "warning"
        assert issue.weight == 3

    def test_issue_to_dict(self) -> None:
        """Test Issue serialization."""
        issue = Issue(
            rule="test_rule",
            message="Test message",
            severity="error",
            filepath="test.py",
            lineno=5,
        )
        d = issue.to_dict()
        assert d["rule"] == "test_rule"
        assert d["severity"] == "error"

    def test_severity_weights(self) -> None:
        """Test severity weight mapping."""
        assert Issue(rule="r", message="m", severity="info", filepath="f", lineno=1).weight == 1
        assert Issue(rule="r", message="m", severity="warning", filepath="f", lineno=1).weight == 3
        assert Issue(rule="r", message="m", severity="error", filepath="f", lineno=1).weight == 5
        assert Issue(rule="r", message="m", severity="critical", filepath="f", lineno=1).weight == 10


class TestFileReport:
    """Test cases for FileReport."""

    def test_empty_report(self) -> None:
        """Test empty file report."""
        report = FileReport(filepath="test.py")
        assert report.issue_count == 0
        assert report.score == 100.0
        assert report.severity_counts == {
            "info": 0, "warning": 0, "error": 0, "critical": 0
        }

    def test_severity_counts(self) -> None:
        """Test severity count aggregation."""
        issues = [
            Issue(rule="r1", message="m", severity="info", filepath="f", lineno=1),
            Issue(rule="r2", message="m", severity="warning", filepath="f", lineno=2),
            Issue(rule="r3", message="m", severity="error", filepath="f", lineno=3),
        ]
        report = FileReport(filepath="test.py", issues=issues)
        counts = report.severity_counts
        assert counts["info"] == 1
        assert counts["warning"] == 1
        assert counts["error"] == 1
        assert counts["critical"] == 0


class TestCodeAnalyzer:
    """Test cases for CodeAnalyzer."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config(
            max_line_length=120,
            max_function_length=50,
            max_cyclomatic_complexity=10,
            fail_threshold=70.0,
        )

    @pytest.fixture
    def analyzer(self, config: Config) -> CodeAnalyzer:
        """Create test analyzer."""
        return CodeAnalyzer(config)

    def test_analyze_clean_code(self, analyzer: CodeAnalyzer, tmp_path: Path) -> None:
        """Test analyzing clean code."""
        code = '''
"""Clean module docstring."""

def hello(name: str) -> str:
    """Return a greeting.

    Args:
        name: Name to greet.

    Returns:
        Greeting string.
    """
    return f"Hello, {name}!"
'''
        test_file = tmp_path / "clean.py"
        test_file.write_text(code, encoding="utf-8")

        report = analyzer.analyze_file(test_file)
        assert report.passed is True
        assert report.score >= 80

    def test_analyze_code_with_issues(self, analyzer: CodeAnalyzer, tmp_path: Path) -> None:
        """Test analyzing code with issues."""
        code = '''
def very_long_function(a,b,c,d,e,f,g,h):
    x=1
    if a:
        if b:
            if c:
                if d:
                    return x
'''
        test_file = tmp_path / "issues.py"
        test_file.write_text(code, encoding="utf-8")

        report = analyzer.analyze_file(test_file)
        assert len(report.issues) > 0

    def test_analyze_directory(self, analyzer: CodeAnalyzer, tmp_path: Path) -> None:
        """Test analyzing a directory."""
        (tmp_path / "module1.py").write_text(
            '"""Module 1."""\ndef func1():\n    """Func 1."""\n    pass\n',
            encoding="utf-8",
        )
        (tmp_path / "module2.py").write_text(
            '"""Module 2."""\ndef func2():\n    """Func 2."""\n    pass\n',
            encoding="utf-8",
        )

        report = analyzer.analyze_directory(tmp_path)
        assert report.summary["total_files"] == 2

    def test_analyze_from_string(self, analyzer: CodeAnalyzer) -> None:
        """Test analyzing code from a string."""
        code = '"""Test."""\ndef func():\n    """A function."""\n    return 42\n'
        report = analyzer.analyze_code(code)
        assert report.filepath == "<string>"
        assert report.score >= 80

    def test_analyze_syntax_error(self, analyzer: CodeAnalyzer, tmp_path: Path) -> None:
        """Test handling syntax errors."""
        test_file = tmp_path / "broken.py"
        test_file.write_text("def func(\n", encoding="utf-8")

        report = analyzer.analyze_file(test_file)
        assert any(i.severity == "critical" for i in report.issues)

    def test_analyze_nonexistent_file(self, analyzer: CodeAnalyzer) -> None:
        """Test handling non-existent files."""
        report = analyzer.analyze_file("/nonexistent/file.py")
        assert report.score == 0.0
        assert report.grade == "F"

    def test_analyze_nonexistent_directory(self, analyzer: CodeAnalyzer) -> None:
        """Test handling non-existent directories."""
        report = analyzer.analyze_directory("/nonexistent/dir")
        assert not report.passed

    def test_report_serialization(self, analyzer: CodeAnalyzer) -> None:
        """Test report serialization."""
        code = 'def func():\n    """A function."""\n    return 42\n'
        report = analyzer.analyze_code(code)
        data = report.to_dict()
        assert "filepath" in data
        assert "score" in data
        assert "issues" in data

    def test_self_analysis(self, analyzer: CodeAnalyzer) -> None:
        """Test that the analyzer can analyze itself."""
        src_dir = Path(__file__).parent.parent / "src"
        if src_dir.exists():
            report = analyzer.analyze_directory(src_dir)
            assert report.summary["total_files"] > 0


class TestASTParser:
    """Test cases for ASTParser."""

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create test parser."""
        return ASTParser()

    def test_parse_function(self, parser: ASTParser) -> None:
        """Test parsing a function."""
        code = '''
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"
'''
        module = parser.parse_source(code)
        assert len(module.functions) == 1
        assert module.functions[0].name == "greet"
        assert module.functions[0].docstring == "Greet someone."

    def test_parse_class(self, parser: ASTParser) -> None:
        """Test parsing a class."""
        code = '''
class Person:
    """A person."""

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        """Greet."""
        return f"Hello, I am {self.name}"
'''
        module = parser.parse_source(code)
        assert len(module.classes) == 1
        assert module.classes[0].name == "Person"
        assert len(module.classes[0].methods) == 2

    def test_parse_imports(self, parser: ASTParser) -> None:
        """Test parsing imports."""
        code = '''
import os
import sys
from pathlib import Path
from typing import Optional, List
'''
        module = parser.parse_source(code)
        assert len(module.imports) == 4

    def test_line_stats(self, parser: ASTParser) -> None:
        """Test line statistics."""
        code = '''# Comment line
def func():
    """Docstring."""
    x = 1  # inline comment
    return x
'''
        module = parser.parse_source(code)
        assert module.total_lines >= 5
        assert module.code_lines > 0
        assert module.comment_lines >= 1

    def test_cache(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test parser caching."""
        test_file = tmp_path / "cache.py"
        test_file.write_text("x = 1\n", encoding="utf-8")

        result1 = parser.parse_file(test_file)
        result2 = parser.parse_file(test_file)
        # Should return cached result
        assert result1 is result2

        parser.clear_cache()
        result3 = parser.parse_file(test_file)
        assert result3 is not result1


class TestReviewReport:
    """Test cases for ReviewReport."""

    def test_empty_report(self) -> None:
        """Test empty review report."""
        report = ReviewReport()
        assert report.overall_score == 100.0
        assert report.overall_grade == "A"
        assert report.passed is True
        assert report.total_issues == 0

    def test_report_dict(self) -> None:
        """Test report to dict."""
        report = ReviewReport(
            files=[
                FileReport(filepath="test.py", score=85.0, grade="B"),
            ],
            total_issues=5,
            overall_score=85.0,
            overall_grade="B",
        )
        data = report.to_dict()
        assert data["overall_score"] == 85.0
        assert data["overall_grade"] == "B"
        assert len(data["files"]) == 1
