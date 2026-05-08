"""Core code analyzer that orchestrates all review rules and detectors."""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.ast_parser import ASTParser, ModuleInfo
from src.config import Config, load_config

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    """Represents a single code review issue."""

    rule: str
    message: str
    severity: str  # info, warning, error, critical
    filepath: str
    lineno: int
    col_offset: int = 0
    end_lineno: Optional[int] = None
    suggestion: str = ""
    code_snippet: str = ""
    category: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Convert issue to dictionary representation.

        Returns:
            Dictionary with all issue fields.
        """
        return {
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
            "filepath": self.filepath,
            "lineno": self.lineno,
            "col_offset": self.col_offset,
            "end_lineno": self.end_lineno,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
            "category": self.category,
            "confidence": self.confidence,
        }

    @property
    def weight(self) -> int:
        """Get severity weight for scoring calculations.

        Returns:
            Weight value based on severity.
        """
        weights = {"info": 1, "warning": 3, "error": 5, "critical": 10}
        return weights.get(self.severity, 1)


@dataclass
class FileReport:
    """Complete analysis report for a single file."""

    filepath: str
    issues: list[Issue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    score: float = 100.0
    grade: str = "A"
    passed: bool = True

    @property
    def issue_count(self) -> int:
        """Get total number of issues.

        Returns:
            Count of all issues.
        """
        return len(self.issues)

    @property
    def severity_counts(self) -> dict[str, int]:
        """Get count of issues by severity.

        Returns:
            Dictionary mapping severity to count.
        """
        counts: dict[str, int] = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for issue in self.issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert file report to dictionary representation.

        Returns:
            Dictionary with all file report fields.
        """
        return {
            "filepath": self.filepath,
            "score": self.score,
            "grade": self.grade,
            "passed": self.passed,
            "issue_count": self.issue_count,
            "severity_counts": self.severity_counts,
            "metrics": self.metrics,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class ReviewReport:
    """Complete code review report for all analyzed files."""

    files: list[FileReport] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    total_issues: int = 0
    overall_score: float = 100.0
    overall_grade: str = "A"
    passed: bool = True
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary representation.

        Returns:
            Dictionary with complete report data.
        """
        return {
            "summary": self.summary,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "passed": self.passed,
            "total_issues": self.total_issues,
            "duration_ms": self.duration_ms,
            "files": [
                {
                    "filepath": f.filepath,
                    "score": f.score,
                    "grade": f.grade,
                    "passed": f.passed,
                    "issue_count": f.issue_count,
                    "severity_counts": f.severity_counts,
                    "issues": [i.to_dict() for i in f.issues],
                    "metrics": f.metrics,
                }
                for f in self.files
            ],
        }


class CodeAnalyzer:
    """Main code analyzer that orchestrates all review components."""

    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize the code analyzer.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or load_config()
        self.parser = ASTParser()
        self._issues: list[Issue] = []
        self._rule_modules: list[Any] = []
        self._detector_modules: list[Any] = []
        self._load_modules()

    def _load_modules(self) -> None:
        """Dynamically load all rule and detector modules."""
        try:
            from src.rules import complexity, documentation, naming, performance, security, style

            if self.config.is_rule_enabled("complexity"):
                self._rule_modules.append(complexity)
            if self.config.is_rule_enabled("naming"):
                self._rule_modules.append(naming)
            if self.config.is_rule_enabled("documentation"):
                self._rule_modules.append(documentation)
            if self.config.is_rule_enabled("security"):
                self._rule_modules.append(security)
            if self.config.is_rule_enabled("performance"):
                self._rule_modules.append(performance)
            if self.config.is_rule_enabled("style"):
                self._rule_modules.append(style)

            from src.detectors import anti_patterns, code_smells, security_risks

            if self.config.is_detector_enabled("code_smells"):
                self._detector_modules.append(code_smells)
            if self.config.is_detector_enabled("security_risks"):
                self._detector_modules.append(security_risks)
            if self.config.is_detector_enabled("anti_patterns"):
                self._detector_modules.append(anti_patterns)

            logger.info(
                "Loaded %d rule modules and %d detector modules",
                len(self._rule_modules),
                len(self._detector_modules),
            )
        except ImportError as e:
            logger.warning("Failed to load some modules: %s", e)

    def analyze_file(self, filepath: str | Path) -> FileReport:
        """Analyze a single Python file.

        Args:
            filepath: Path to the Python file.

        Returns:
            FileReport with all findings.
        """
        filepath = Path(filepath)
        self._issues = []

        logger.info("Analyzing file: %s", filepath)

        try:
            module = self.parser.parse_file(filepath)
        except SyntaxError as e:
            issue = Issue(
                rule="syntax_error",
                message=f"Syntax error: {e}",
                severity="critical",
                filepath=str(filepath),
                lineno=getattr(e, "lineno", 1),
                col_offset=getattr(e, "offset", 0),
                category="syntax",
                suggestion="Fix the syntax error before running other checks.",
            )
            return FileReport(filepath=str(filepath), issues=[issue], score=0.0, grade="F", passed=False)
        except FileNotFoundError:
            issue = Issue(
                rule="file_not_found",
                message=f"File not found: {filepath}",
                severity="critical",
                filepath=str(filepath),
                lineno=0,
                category="file",
            )
            return FileReport(filepath=str(filepath), issues=[issue], score=0.0, grade="F", passed=False)

        # Run all rule checks
        self._run_rules(module, filepath)

        # Run all detectors
        self._run_detectors(module, filepath)

        # Apply suggestions
        self._generate_suggestions(module)

        # Calculate file score and grade
        from src.scoring.calculator import ScoreCalculator

        calculator = ScoreCalculator(self.config)
        score, grade = calculator.calculate_file_score(self._issues, module)

        report = FileReport(
            filepath=str(filepath),
            issues=self._issues,
            metrics=self._collect_metrics(module),
            score=score,
            grade=grade,
            passed=score >= self.config.fail_threshold,
        )

        logger.info(
            "File analysis complete: %s - Score: %.1f (%s), Issues: %d",
            filepath,
            score,
            grade,
            len(self._issues),
        )
        return report

    def analyze_directory(
        self, directory: str | Path, recursive: bool = True
    ) -> ReviewReport:
        """Analyze all Python files in a directory.

        Args:
            directory: Root directory to analyze.
            recursive: Whether to recurse into subdirectories.

        Returns:
            ReviewReport with all file analyses.
        """
        import time

        start = time.time()
        directory = Path(directory)

        if not directory.exists():
            return ReviewReport(
                summary={"error": f"Directory not found: {directory}"},
                passed=False,
            )

        pattern = "**/*.py" if recursive else "*.py"
        files = sorted(directory.glob(pattern))

        # Filter out ignored files
        files = [
            f for f in files if not self.config.should_ignore(f)
        ]

        logger.info("Found %d Python files to analyze in %s", len(files), directory)

        file_reports: list[FileReport] = []
        for filepath in files:
            report = self.analyze_file(filepath)
            file_reports.append(report)

        duration = (time.time() - start) * 1000

        # Calculate aggregate statistics
        total_issues = sum(r.issue_count for r in file_reports)
        avg_score = (
            sum(r.score for r in file_reports) / len(file_reports)
            if file_reports
            else 100.0
        )

        from src.scoring.calculator import ScoreCalculator

        calculator = ScoreCalculator(self.config)
        overall_grade = calculator.calculate_grade(avg_score)

        severity_totals: dict[str, int] = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for report in file_reports:
            for severity, count in report.severity_counts.items():
                severity_totals[severity] = severity_totals.get(severity, 0) + count

        report = ReviewReport(
            files=file_reports,
            summary={
                "total_files": len(files),
                "files_with_issues": sum(1 for r in file_reports if r.issues),
                "severity_totals": severity_totals,
                "average_score": round(avg_score, 1),
            },
            total_issues=total_issues,
            overall_score=round(avg_score, 1),
            overall_grade=overall_grade,
            passed=avg_score >= self.config.fail_threshold,
            duration_ms=duration,
        )

        logger.info(
            "Directory analysis complete: %s - Score: %.1f (%s), Total Issues: %d",
            directory,
            report.overall_score,
            report.overall_grade,
            total_issues,
        )
        return report

    def analyze_code(self, code: str, filename: str = "<string>") -> FileReport:
        """Analyze Python source code from a string.

        Args:
            code: Python source code to analyze.
            filename: Virtual filename for reporting.

        Returns:
            FileReport with all findings.
        """
        self._issues = []

        try:
            module = self.parser.parse_source(code, filename)
        except SyntaxError as e:
            issue = Issue(
                rule="syntax_error",
                message=f"Syntax error: {e}",
                severity="critical",
                filepath=filename,
                lineno=getattr(e, "lineno", 1),
                category="syntax",
            )
            return FileReport(filepath=filename, issues=[issue], score=0.0, grade="F", passed=False)

        self._run_rules(module, Path(filename))
        self._run_detectors(module, Path(filename))
        self._generate_suggestions(module)

        from src.scoring.calculator import ScoreCalculator

        calculator = ScoreCalculator(self.config)
        score, grade = calculator.calculate_file_score(self._issues, module)

        return FileReport(
            filepath=filename,
            issues=self._issues,
            metrics=self._collect_metrics(module),
            score=score,
            grade=grade,
            passed=score >= self.config.fail_threshold,
        )

    def _run_rules(self, module: ModuleInfo, filepath: Path) -> None:
        """Execute all loaded rule modules.

        Args:
            module: Parsed module information.
            filepath: Path to the file being analyzed.
        """
        for rule_module in self._rule_modules:
            try:
                if hasattr(rule_module, "check"):
                    new_issues = rule_module.check(module, self.config, filepath)
                    if new_issues:
                        self._issues.extend(new_issues)
                elif hasattr(rule_module, "run"):
                    new_issues = rule_module.run(module, self.config)
                    if new_issues:
                        self._issues.extend(new_issues)
            except Exception as e:
                logger.error("Rule module %s failed: %s", rule_module.__name__, e)

    def _run_detectors(self, module: ModuleInfo, filepath: Path) -> None:
        """Execute all loaded detector modules.

        Args:
            module: Parsed module information.
            filepath: Path to the file being analyzed.
        """
        for detector in self._detector_modules:
            try:
                if hasattr(detector, "detect"):
                    new_issues = detector.detect(module, self.config)
                    if new_issues:
                        self._issues.extend(new_issues)
                elif hasattr(detector, "run"):
                    new_issues = detector.run(module, self.config)
                    if new_issues:
                        self._issues.extend(new_issues)
            except Exception as e:
                logger.error(
                    "Detector module %s failed: %s", detector.__name__, e
                )

    def _generate_suggestions(self, module: ModuleInfo) -> None:
        """Generate AI-powered fix suggestions for all issues.

        Args:
            module: Parsed module information.
        """
        if not self.config.ai_suggestions:
            return

        try:
            from src.suggestions.engine import SuggestionEngine

            engine = SuggestionEngine(self.config)
            for issue in self._issues:
                if not issue.suggestion:
                    suggestion = engine.generate_suggestion(issue, module)
                    if suggestion:
                        issue.suggestion = suggestion
        except ImportError:
            logger.debug("Suggestion engine not available")

    def _collect_metrics(self, module: ModuleInfo) -> dict[str, Any]:
        """Collect file-level metrics.

        Args:
            module: Parsed module information.

        Returns:
            Dictionary of collected metrics.
        """
        avg_complexity = (
            sum(f.complexity for f in module.functions) / len(module.functions)
            if module.functions
            else 0.0
        )
        avg_cognitive = (
            sum(f.cognitive_complexity for f in module.functions)
            / len(module.functions)
            if module.functions
            else 0.0
        )

        total_methods = sum(len(c.methods) for c in module.classes)
        documented_functions = sum(
            1 for f in module.functions if f.docstring is not None
        )
        documented_classes = sum(
            1 for c in module.classes if c.docstring is not None
        )
        total_documentable = len(module.functions) + len(module.classes)
        total_documented = documented_functions + documented_classes

        docstring_coverage = (
            (total_documented / total_documentable * 100)
            if total_documentable > 0
            else 100.0
        )

        return {
            "total_lines": module.total_lines,
            "code_lines": module.code_lines,
            "comment_lines": module.comment_lines,
            "blank_lines": module.blank_lines,
            "comment_ratio": (
                round(module.comment_lines / module.code_lines * 100, 1)
                if module.code_lines > 0
                else 0.0
            ),
            "function_count": len(module.functions),
            "class_count": len(module.classes),
            "import_count": len(module.imports),
            "unused_imports": sum(1 for i in module.imports if i.is_unused),
            "average_complexity": round(avg_complexity, 1),
            "max_complexity": (
                max((f.complexity for f in module.functions), default=0)
            ),
            "average_cognitive_complexity": round(avg_cognitive, 1),
            "total_methods": total_methods,
            "docstring_coverage": round(docstring_coverage, 1),
            "global_variables": len(module.global_variables),
        }

    def get_issue_summary(self) -> dict[str, int]:
        """Get summary of all issues found.

        Returns:
            Dictionary mapping severity to count.
        """
        summary: dict[str, int] = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for issue in self._issues:
            summary[issue.severity] = summary.get(issue.severity, 0) + 1
        return summary
