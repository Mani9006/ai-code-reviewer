"""Code quality score calculator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.ast_parser import ModuleInfo

if TYPE_CHECKING:
    from src.analyzer import Issue
    from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown by category."""

    overall: float = 100.0
    complexity: float = 100.0
    naming: float = 100.0
    documentation: float = 100.0
    security: float = 100.0
    performance: float = 100.0
    style: float = 100.0
    code_smells: float = 100.0
    anti_patterns: float = 100.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "overall": self.overall,
            "complexity": self.complexity,
            "naming": self.naming,
            "documentation": self.documentation,
            "security": self.security,
            "performance": self.performance,
            "style": self.style,
            "code_smells": self.code_smells,
            "anti_patterns": self.anti_patterns,
        }


class ScoreCalculator:
    """Calculate code quality scores based on issues and metrics."""

    # Category mapping from rule names
    CATEGORY_MAP: dict[str, str] = {
        "high_cyclomatic_complexity": "complexity",
        "high_cognitive_complexity": "complexity",
        "deep_nesting": "complexity",
        "too_many_arguments": "complexity",
        "function_too_long": "complexity",
        "file_too_long": "complexity",
        "too_many_methods": "complexity",
        "large_try_block": "complexity",
        "invalid_function_name": "naming",
        "invalid_class_name": "naming",
        "invalid_module_name": "naming",
        "single_char_name": "naming",
        "builtin_shadowing": "naming",
        "keyword_name": "naming",
        "missing_function_docstring": "documentation",
        "missing_class_docstring": "documentation",
        "missing_method_docstring": "documentation",
        "missing_module_docstring": "documentation",
        "short_docstring": "documentation",
        "short_class_docstring": "documentation",
        "undocumented_parameters": "documentation",
        "undocumented_return": "documentation",
        "low_docstring_coverage": "documentation",
        "dangerous_eval_call": "security",
        "dangerous_exec_call": "security",
        "hardcoded_password": "security",
        "hardcoded_secret": "security",
        "hardcoded_token": "security",
        "sql_injection_risk": "security",
        "wildcard_import": "security",
        "assert_for_security": "security",
        "weak_hash_algorithm": "security",
        "sql_fstring_risk": "security",
        "aws_key_exposure": "security",
        "aws_secret_exposure": "security",
        "github_token_exposure": "security",
        "openai_key_exposure": "security",
        "google_api_key_exposure": "security",
        "line_too_long": "style",
        "trailing_whitespace": "style",
        "tab_character": "style",
        "multiple_statements": "style",
        "missing_whitespace_around_operator": "style",
        "missing_blank_lines": "style",
        "import_order": "style",
        "bare_except": "style",
        "mutable_default_argument": "style",
        "duplicate_code": "code_smells",
        "long_parameter_list": "code_smells",
        "feature_envy": "code_smells",
        "unreachable_code": "code_smells",
        "commented_code": "code_smells",
        "complex_conditional": "code_smells",
        "god_class": "code_smells",
        "use_dataclass": "code_smells",
        "except_pass": "anti_patterns",
        "type_vs_isinstance": "anti_patterns",
        "bare_raise": "anti_patterns",
        "builtin_reassignment": "anti_patterns",
        "unnecessary_list_conversion": "anti_patterns",
        "missing_context_manager": "anti_patterns",
        "string_is_comparison": "anti_patterns",
        "use_enumerate": "anti_patterns",
        "catch_base_exception": "anti_patterns",
        "recursive_without_memoization": "performance",
        "list_concat_in_loop": "performance",
        "string_concat_in_loop": "performance",
        "repeated_attribute_access": "performance",
        "slow_membership_test": "performance",
        "unnecessary_list_calls": "performance",
        "global_variable_usage": "performance",
        "use_list_comprehension": "performance",
        "unsafe_deserialization": "security",
        "command_injection": "security",
        "path_traversal": "security",
        "ssrf_risk": "security",
        "timing_attack": "security",
        "insecure_random": "security",
        "unsafe_tempfile": "security",
        "debug_mode_enabled": "security",
        "unsafe_string_format": "anti_patterns",
    }

    # Weights for each category
    CATEGORY_WEIGHTS: dict[str, float] = {
        "complexity": 1.0,
        "naming": 0.8,
        "documentation": 0.8,
        "security": 2.0,
        "performance": 0.7,
        "style": 0.5,
        "code_smells": 1.0,
        "anti_patterns": 0.8,
    }

    def __init__(self, config: Config) -> None:
        """Initialize score calculator.

        Args:
            config: Configuration object.
        """
        self.config = config

    def calculate_file_score(
        self, issues: list["Issue"], module: ModuleInfo | None = None
    ) -> tuple[float, str]:
        """Calculate score and grade for a file.

        Args:
            issues: List of issues found.
            module: Optional parsed module info.

        Returns:
            Tuple of (score, grade).
        """
        breakdown = self.calculate_breakdown(issues, module)
        score = breakdown.overall
        grade = self.calculate_grade(score)
        return score, grade

    def calculate_breakdown(
        self, issues: list["Issue"], module: ModuleInfo | None = None
    ) -> ScoreBreakdown:
        """Calculate detailed score breakdown.

        Args:
            issues: List of issues found.
            module: Optional parsed module info.

        Returns:
            ScoreBreakdown with category scores.
        """
        breakdown = ScoreBreakdown()

        if not issues:
            return breakdown

        # Group issues by category
        category_issues: dict[str, list["Issue"]] = {
            "complexity": [],
            "naming": [],
            "documentation": [],
            "security": [],
            "performance": [],
            "style": [],
            "code_smells": [],
            "anti_patterns": [],
        }

        for issue in issues:
            cat = self.CATEGORY_MAP.get(issue.rule, "style")
            if cat in category_issues:
                category_issues[cat].append(issue)

        # Calculate score for each category
        for category, cat_issues in category_issues.items():
            score = self._category_score(cat_issues)
            setattr(breakdown, category, score)

        # Calculate weighted overall score
        total_weight = 0.0
        weighted_sum = 0.0

        for category, weight in self.CATEGORY_WEIGHTS.items():
            score = getattr(breakdown, category)
            weighted_sum += score * weight
            total_weight += weight

        breakdown.overall = round(weighted_sum / total_weight, 1) if total_weight > 0 else 100.0

        # Adjust for critical issues
        critical_count = sum(
            1 for i in issues if i.severity == "critical"
        )
        if critical_count > 0:
            penalty = min(critical_count * 10, 50)
            breakdown.overall = max(0, breakdown.overall - penalty)

        # Bonus for good documentation coverage
        if module and hasattr(module, "docstring"):
            if module.docstring:
                breakdown.overall = min(100, breakdown.overall + 2)

        breakdown.overall = round(breakdown.overall, 1)
        return breakdown

    def _category_score(self, issues: list["Issue"]) -> float:
        """Calculate score for a category.

        Args:
            issues: Issues in the category.

        Returns:
            Score from 0-100.
        """
        if not issues:
            return 100.0

        total_penalty = 0.0
        for issue in issues:
            penalty = self._issue_penalty(issue)
            total_penalty += penalty

        score = max(0, 100 - total_penalty)
        return round(score, 1)

    def _issue_penalty(self, issue: "Issue") -> float:
        """Calculate penalty for a single issue.

        Args:
            issue: Issue to calculate penalty for.

        Returns:
            Penalty value.
        """
        severity_penalties = {
            "info": 1.0,
            "warning": 3.0,
            "error": 7.0,
            "critical": 15.0,
        }
        base = severity_penalties.get(issue.severity, 1.0)

        # Security issues get extra weight
        if issue.category == "security" or issue.category == "security_risk":
            base *= 1.5

        return base

    def calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score.

        Args:
            score: Numerical score.

        Returns:
            Letter grade (A+ through F).
        """
        if score >= 98:
            return "A+"
        elif score >= 93:
            return "A"
        elif score >= 90:
            return "A-"
        elif score >= 87:
            return "B+"
        elif score >= 83:
            return "B"
        elif score >= 80:
            return "B-"
        elif score >= 77:
            return "C+"
        elif score >= 73:
            return "C"
        elif score >= 70:
            return "C-"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def calculate_directory_score(self, file_scores: list[float]) -> float:
        """Calculate aggregate score for a directory.

        Args:
            file_scores: List of individual file scores.

        Returns:
            Aggregate score.
        """
        if not file_scores:
            return 100.0
        return round(sum(file_scores) / len(file_scores), 1)
