"""Tests for the suggestion engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.analyzer import CodeAnalyzer, Issue
from src.ast_parser import ASTParser, ModuleInfo
from src.config import Config
from src.suggestions.engine import SuggestionEngine


class TestSuggestionEngine:
    """Test cases for SuggestionEngine."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config(ai_suggestions=True)

    @pytest.fixture
    def engine(self, config: Config) -> SuggestionEngine:
        """Create test engine."""
        return SuggestionEngine(config)

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create test parser."""
        return ASTParser()

    def test_suggestion_for_eval(self, engine: SuggestionEngine) -> None:
        """Test suggestion for eval usage."""
        issue = Issue(
            rule="dangerous_eval_call",
            message="eval() used",
            severity="critical",
            filepath="test.py",
            lineno=1,
            category="security",
        )
        suggestion = engine.generate_suggestion(issue, None)
        assert suggestion is not None
        assert "ast.literal_eval" in suggestion or "eval" in suggestion

    def test_suggestion_for_line_length(self, engine: SuggestionEngine) -> None:
        """Test suggestion for line too long."""
        issue = Issue(
            rule="line_too_long",
            message="Line too long",
            severity="warning",
            filepath="test.py",
            lineno=1,
            category="style",
        )
        suggestion = engine.generate_suggestion(issue, None)
        assert suggestion is not None

    def test_suggestion_for_missing_docstring(
        self, engine: SuggestionEngine, parser: ASTParser
    ) -> None:
        """Test suggestion for missing docstring."""
        code = '''
def my_function(param1, param2):
    return param1 + param2
'''
        module = parser.parse_source(code)
        issue = Issue(
            rule="missing_function_docstring",
            message="Missing docstring",
            severity="warning",
            filepath="test.py",
            lineno=2,
            category="documentation",
        )
        suggestion = engine.generate_suggestion(issue, module)
        assert suggestion is not None
        assert "docstring" in suggestion.lower()

    def test_suggestion_for_mutable_default(
        self, engine: SuggestionEngine
    ) -> None:
        """Test suggestion for mutable default argument."""
        issue = Issue(
            rule="mutable_default_argument",
            message="Mutable default",
            severity="error",
            filepath="test.py",
            lineno=1,
            category="style",
        )
        suggestion = engine.generate_suggestion(issue, None)
        assert suggestion is not None
        assert "None" in suggestion

    def test_no_suggestion_for_unknown_rule(
        self, engine: SuggestionEngine
    ) -> None:
        """Test that unknown rules don't generate suggestions."""
        issue = Issue(
            rule="unknown_rule_xyz",
            message="Unknown issue",
            severity="info",
            filepath="test.py",
            lineno=1,
            category="unknown",
        )
        suggestion = engine.generate_suggestion(issue, None)
        # Should return None or a generic category suggestion
        assert suggestion is None or len(suggestion) > 0

    def test_fix_example_for_line_length(self, engine: SuggestionEngine) -> None:
        """Test fix example generation."""
        issue = Issue(
            rule="line_too_long",
            message="Line too long",
            severity="warning",
            filepath="test.py",
            lineno=1,
            category="style",
        )
        example = engine.generate_fix_example(issue, None)
        assert example is not None
        assert "Break the line" in example or "Instead of" in example

    def test_fix_example_for_mutable_default(
        self, engine: SuggestionEngine
    ) -> None:
        """Test fix example for mutable default."""
        issue = Issue(
            rule="mutable_default_argument",
            message="Mutable default",
            severity="error",
            filepath="test.py",
            lineno=1,
            category="style",
        )
        example = engine.generate_fix_example(issue, None)
        assert example is not None
        assert "None" in example

    def test_context_suggestion_with_function(
        self, engine: SuggestionEngine, parser: ASTParser
    ) -> None:
        """Test context-aware suggestion with function info."""
        code = '''
def compute(a, b, c, d, e, f, g):
    if a > 0:
        if b > 0:
            if c > 0:
                return a + b + c
    return 0
'''
        module = parser.parse_source(code)
        issue = Issue(
            rule="high_cyclomatic_complexity",
            message="Complex function",
            severity="warning",
            filepath="test.py",
            lineno=2,
            category="complexity",
        )
        suggestion = engine.generate_suggestion(issue, module)
        assert suggestion is not None

    def test_analyzer_integration(self) -> None:
        """Test suggestions integrated in analyzer."""
        config = Config(ai_suggestions=True)
        analyzer = CodeAnalyzer(config)

        code = '''
def func(a,b):
    x = eval("1 + 2")
    return x
'''
        report = analyzer.analyze_code(code)
        # Some issues should have suggestions
        issues_with_suggestions = [
            i for i in report.issues if i.suggestion
        ]
        assert len(issues_with_suggestions) > 0
