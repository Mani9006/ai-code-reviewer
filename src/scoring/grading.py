"""Grade assignment and quality classification."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Grade(Enum):
    """Quality grade levels."""

    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D = "D"
    F = "F"

    @property
    def description(self) -> str:
        """Get human-readable grade description.

        Returns:
            Description string.
        """
        descriptions = {
            Grade.A_PLUS: "Exceptional - Outstanding code quality",
            Grade.A: "Excellent - Very high code quality",
            Grade.A_MINUS: "Very Good - Minor issues only",
            Grade.B_PLUS: "Good - Above average quality",
            Grade.B: "Satisfactory - Good quality with some issues",
            Grade.B_MINUS: "Acceptable - Moderate quality",
            Grade.C_PLUS: "Below Average - Needs improvement",
            Grade.C: "Fair - Significant issues present",
            Grade.C_MINUS: "Poor - Many issues to address",
            Grade.D: "Very Poor - Major rework needed",
            Grade.F: "Failing - Critical issues require immediate attention",
        }
        return descriptions.get(self, "Unknown")

    @property
    def color(self) -> str:
        """Get color code for the grade.

        Returns:
            ANSI color code.
        """
        colors = {
            Grade.A_PLUS: "\033[38;5;82m",   # Bright green
            Grade.A: "\033[38;5;82m",        # Bright green
            Grade.A_MINUS: "\033[38;5;118m", # Green
            Grade.B_PLUS: "\033[38;5;190m",  # Yellow-green
            Grade.B: "\033[38;5;226m",       # Yellow
            Grade.B_MINUS: "\033[38;5;220m", # Gold
            Grade.C_PLUS: "\033[38;5;208m",  # Orange
            Grade.C: "\033[38;5;202m",       # Dark orange
            Grade.C_MINUS: "\033[38;5;196m", # Red-orange
            Grade.D: "\033[38;5;160m",       # Red
            Grade.F: "\033[38;5;124m",       # Dark red
        }
        return colors.get(self, "\033[0m")

    @property
    def hex_color(self) -> str:
        """Get hex color for the grade.

        Returns:
            Hex color string.
        """
        colors = {
            Grade.A_PLUS: "#00FF00",
            Grade.A: "#00FF00",
            Grade.A_MINUS: "#7FFF00",
            Grade.B_PLUS: "#ADFF2F",
            Grade.B: "#FFFF00",
            Grade.B_MINUS: "#FFD700",
            Grade.C_PLUS: "#FFA500",
            Grade.C: "#FF8C00",
            Grade.C_MINUS: "#FF6347",
            Grade.D: "#FF4500",
            Grade.F: "#FF0000",
        }
        return colors.get(self, "#808080")


@dataclass
class GradeReport:
    """Detailed grade report."""

    grade: Grade
    score: float
    passed: bool
    description: str = ""
    recommendations: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if self.recommendations is None:
            self.recommendations = []
        if not self.description:
            self.description = self.grade.description

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "grade": self.grade.value,
            "score": self.score,
            "passed": self.passed,
            "description": self.description,
            "recommendations": self.recommendations,
        }


class GradeAssigner:
    """Assign grades and generate grade reports."""

    GRADE_THRESHOLDS: list[tuple[float, Grade]] = [
        (98.0, Grade.A_PLUS),
        (93.0, Grade.A),
        (90.0, Grade.A_MINUS),
        (87.0, Grade.B_PLUS),
        (83.0, Grade.B),
        (80.0, Grade.B_MINUS),
        (77.0, Grade.C_PLUS),
        (73.0, Grade.C),
        (70.0, Grade.C_MINUS),
        (60.0, Grade.D),
        (0.0, Grade.F),
    ]

    def __init__(self, fail_threshold: float = 70.0) -> None:
        """Initialize grade assigner.

        Args:
            fail_threshold: Score below which is considered failing.
        """
        self.fail_threshold = fail_threshold

    def assign_grade(self, score: float) -> GradeReport:
        """Assign a grade based on score.

        Args:
            score: Numerical score.

        Returns:
            GradeReport with detailed information.
        """
        grade = self._score_to_grade(score)
        passed = score >= self.fail_threshold

        recommendations = self._generate_recommendations(score, grade)

        return GradeReport(
            grade=grade,
            score=score,
            passed=passed,
            description=grade.description,
            recommendations=recommendations,
        )

    def _score_to_grade(self, score: float) -> Grade:
        """Convert score to grade.

        Args:
            score: Numerical score.

        Returns:
            Grade enum value.
        """
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return Grade.F

    def _generate_recommendations(
        self, score: float, grade: Grade
    ) -> list[str]:
        """Generate improvement recommendations.

        Args:
            score: Numerical score.
            grade: Assigned grade.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        if score >= 90:
            recommendations.append(
                "Code quality is excellent. Continue maintaining "
                "high standards."
            )
            if score < 98:
                recommendations.append(
                    "Consider adding more comprehensive docstrings "
                    "for perfect coverage."
                )
        elif score >= 80:
            recommendations.append(
                "Address warnings and info-level issues to improve "
                "to an A grade."
            )
            recommendations.append(
                "Ensure all public functions and classes have "
                "docstrings."
            )
        elif score >= 70:
            recommendations.append(
                "Prioritize fixing error-level issues first."
            )
            recommendations.append(
                "Review security-related findings and address "
                "vulnerabilities."
            )
            recommendations.append(
                "Refactor functions with high complexity scores."
            )
        else:
            recommendations.append(
                "URGENT: Address all critical and error-level "
                "issues immediately."
            )
            recommendations.append(
                "Review and fix security vulnerabilities before "
                "deployment."
            )
            recommendations.append(
                "Significant refactoring recommended for complex "
                "functions."
            )
            recommendations.append(
                "Ensure proper documentation coverage across all "
                "modules."
            )

        return recommendations

    def compare_grades(self, old_score: float, new_score: float) -> str:
        """Compare two scores and describe the change.

        Args:
            old_score: Previous score.
            new_score: Current score.

        Returns:
            Description of the change.
        """
        diff = new_score - old_score
        old_grade = self._score_to_grade(old_score)
        new_grade = self._score_to_grade(new_score)

        if diff > 0:
            direction = "improved"
        elif diff < 0:
            direction = "declined"
        else:
            direction = "unchanged"

        if old_grade == new_grade:
            return (
                f"Score {direction} by {abs(diff):.1f} points "
                f"(Grade: {new_grade.value})"
            )
        else:
            return (
                f"Score {direction} by {abs(diff):.1f} points "
                f"({old_grade.value} -> {new_grade.value})"
            )
