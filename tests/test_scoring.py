"""Tests for scoring and grading modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.analyzer import Issue
from src.config import Config
from src.scoring.calculator import ScoreCalculator, ScoreBreakdown
from src.scoring.grading import Grade, GradeAssigner, GradeReport


class TestScoreBreakdown:
    """Test cases for ScoreBreakdown."""

    def test_default_values(self) -> None:
        """Test default score values."""
        breakdown = ScoreBreakdown()
        assert breakdown.overall == 100.0
        assert breakdown.complexity == 100.0
        assert breakdown.security == 100.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        breakdown = ScoreBreakdown()
        d = breakdown.to_dict()
        assert d["overall"] == 100.0
        assert "complexity" in d
        assert "security" in d


class TestScoreCalculator:
    """Test cases for ScoreCalculator."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test configuration."""
        return Config()

    @pytest.fixture
    def calculator(self, config: Config) -> ScoreCalculator:
        """Create test calculator."""
        return ScoreCalculator(config)

    def test_perfect_score_no_issues(self, calculator: ScoreCalculator) -> None:
        """Test perfect score with no issues."""
        score, grade = calculator.calculate_file_score([])
        assert score == 100.0
        assert grade == "A+"

    def test_score_with_info_issues(self, calculator: ScoreCalculator) -> None:
        """Test score with info-level issues."""
        issues = [
            Issue(rule="line_too_long", message="Line 1", severity="info",
                  filepath="f.py", lineno=1, category="style"),
            Issue(rule="trailing_whitespace", message="Line 2", severity="info",
                  filepath="f.py", lineno=2, category="style"),
        ]
        score, grade = calculator.calculate_file_score(issues)
        assert score < 100.0
        assert score > 90.0

    def test_score_with_warnings(self, calculator: ScoreCalculator) -> None:
        """Test score with warnings."""
        issues = [
            Issue(rule="line_too_long", message="Line 1", severity="warning",
                  filepath="f.py", lineno=1, category="style"),
        ]
        score, grade = calculator.calculate_file_score(issues)
        assert score < 100.0

    def test_score_with_errors(self, calculator: ScoreCalculator) -> None:
        """Test score with errors."""
        # Add many errors across multiple categories to reduce score
        issues = []
        for i in range(20):
            issues.append(Issue(
                rule="high_cyclomatic_complexity", message=f"Complex {i}",
                severity="error", filepath="f.py", lineno=i,
                category="complexity",
            ))
        score, grade = calculator.calculate_file_score(issues)
        # Many errors should reduce score below perfect
        assert score < 100.0
        assert score > 0

    def test_score_with_critical(self, calculator: ScoreCalculator) -> None:
        """Test score with critical issues."""
        issues = [
            Issue(rule="dangerous_eval_call", message="Bad eval",
                  severity="critical", filepath="f.py", lineno=1, category="security"),
        ]
        score, grade = calculator.calculate_file_score(issues)
        assert score < 90.0

    def test_grade_boundaries(self, calculator: ScoreCalculator) -> None:
        """Test grade boundary calculations."""
        assert calculator.calculate_grade(98) == "A+"
        assert calculator.calculate_grade(95) == "A"
        assert calculator.calculate_grade(91) == "A-"
        assert calculator.calculate_grade(88) == "B+"
        assert calculator.calculate_grade(85) == "B"
        assert calculator.calculate_grade(81) == "B-"
        assert calculator.calculate_grade(78) == "C+"
        assert calculator.calculate_grade(75) == "C"
        assert calculator.calculate_grade(71) == "C-"
        assert calculator.calculate_grade(65) == "D"
        assert calculator.calculate_grade(55) == "F"

    def test_directory_score(self, calculator: ScoreCalculator) -> None:
        """Test directory score calculation."""
        scores = [90, 80, 70]
        avg = calculator.calculate_directory_score(scores)
        assert avg == 80.0

    def test_directory_score_empty(self, calculator: ScoreCalculator) -> None:
        """Test empty directory score."""
        avg = calculator.calculate_directory_score([])
        assert avg == 100.0

    def test_breakdown(self, calculator: ScoreCalculator) -> None:
        """Test score breakdown."""
        issues = [
            Issue(rule="line_too_long", message="Line", severity="info",
                  filepath="f.py", lineno=1, category="style"),
            Issue(rule="high_cyclomatic_complexity", message="Complex",
                  severity="warning", filepath="f.py", lineno=2, category="complexity"),
        ]
        breakdown = calculator.calculate_breakdown(issues)
        assert breakdown.overall < 100.0
        assert breakdown.style < 100.0
        assert breakdown.complexity < 100.0

    def test_security_bonus_penalty(self, calculator: ScoreCalculator) -> None:
        """Test security issue penalty weighting."""
        issues = [
            Issue(rule="sql_injection_risk", message="SQL injection",
                  severity="warning", filepath="f.py", lineno=1, category="security"),
        ]
        score, grade = calculator.calculate_file_score(issues)
        # Security issues should have higher penalty
        style_issue = [
            Issue(rule="line_too_long", message="Long line",
                  severity="warning", filepath="f.py", lineno=1, category="style"),
        ]
        style_score, _ = calculator.calculate_file_score(style_issue)
        assert score <= style_score  # Security should penalize more


class TestGrade:
    """Test cases for Grade enum."""

    def test_grade_values(self) -> None:
        """Test grade enum values."""
        assert Grade.A.value == "A"
        assert Grade.F.value == "F"

    def test_grade_descriptions(self) -> None:
        """Test grade descriptions."""
        assert "Excellent" in Grade.A.description
        assert "Failing" in Grade.F.description

    def test_grade_colors(self) -> None:
        """Test grade colors."""
        assert Grade.A.color != ""
        assert Grade.F.color != ""

    def test_grade_hex_colors(self) -> None:
        """Test grade hex colors."""
        assert Grade.A.hex_color.startswith("#")
        assert Grade.F.hex_color.startswith("#")


class TestGradeReport:
    """Test cases for GradeReport."""

    def test_grade_report_creation(self) -> None:
        """Test creating a GradeReport."""
        report = GradeReport(
            grade=Grade.A,
            score=95.0,
            passed=True,
        )
        assert report.grade == Grade.A
        assert report.score == 95.0
        assert report.passed is True

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        report = GradeReport(grade=Grade.B, score=85.0, passed=True)
        d = report.to_dict()
        assert d["grade"] == "B"
        assert d["score"] == 85.0
        assert d["passed"] is True


class TestGradeAssigner:
    """Test cases for GradeAssigner."""

    @pytest.fixture
    def assigner(self) -> GradeAssigner:
        """Create test assigner."""
        return GradeAssigner(fail_threshold=70.0)

    def test_a_plus(self, assigner: GradeAssigner) -> None:
        """Test A+ grade."""
        report = assigner.assign_grade(99)
        assert report.grade == Grade.A_PLUS
        assert report.passed is True

    def test_a_grade(self, assigner: GradeAssigner) -> None:
        """Test A grade."""
        report = assigner.assign_grade(95)
        assert report.grade == Grade.A
        assert report.passed is True

    def test_f_grade(self, assigner: GradeAssigner) -> None:
        """Test F grade."""
        report = assigner.assign_grade(50)
        assert report.grade == Grade.F
        assert report.passed is False

    def test_pass_threshold(self, assigner: GradeAssigner) -> None:
        """Test pass threshold."""
        report = assigner.assign_grade(70)
        assert report.passed is True

        report = assigner.assign_grade(69)
        assert report.passed is False

    def test_recommendations(self, assigner: GradeAssigner) -> None:
        """Test recommendations generation."""
        report = assigner.assign_grade(50)
        assert len(report.recommendations) > 0
        assert any("URGENT" in r for r in report.recommendations)

    def test_grade_comparison(self, assigner: GradeAssigner) -> None:
        """Test grade comparison."""
        result = assigner.compare_grades(80, 85)
        assert "improved" in result

        result = assigner.compare_grades(85, 80)
        assert "declined" in result

        result = assigner.compare_grades(85, 85)
        assert "unchanged" in result
