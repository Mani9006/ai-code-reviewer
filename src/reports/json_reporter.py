"""JSON report generator for code review results."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.analyzer import ReviewReport

logger = logging.getLogger(__name__)


class JSONReporter:
    """Generate JSON reports from review results."""

    def __init__(self, output_dir: str = "./code_review_reports") -> None:
        """Initialize JSON reporter.

        Args:
            output_dir: Directory for output files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self, report: "ReviewReport", filename: str = "report.json"
    ) -> Path:
        """Generate a JSON report.

        Args:
            report: Review report to serialize.
            filename: Output filename.

        Returns:
            Path to generated JSON file.
        """
        data = self._serialize_report(report)
        output_path = self.output_dir / filename
        output_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
        logger.info("JSON report generated: %s", output_path)
        return output_path

    def _serialize_report(self, report: "ReviewReport") -> dict:
        """Serialize report to dictionary.

        Args:
            report: Review report.

        Returns:
            Dictionary representation.
        """
        timestamp = datetime.now().isoformat()

        return {
            "metadata": {
                "tool": "CodeReview AI",
                "version": "1.0.0",
                "generated_at": timestamp,
                "report_schema": "1.0",
            },
            "summary": {
                "overall_score": report.overall_score,
                "overall_grade": report.overall_grade,
                "passed": report.passed,
                "total_files": report.summary.get("total_files", 0),
                "files_with_issues": report.summary.get(
                    "files_with_issues", 0
                ),
                "total_issues": report.total_issues,
                "severity_totals": report.summary.get(
                    "severity_totals", {}
                ),
                "average_score": report.summary.get("average_score", 0),
                "duration_ms": report.duration_ms,
            },
            "files": [
                self._serialize_file_report(fr) for fr in report.files
            ],
        }

    def _serialize_file_report(self, file_report) -> dict:
        """Serialize a file report to dictionary.

        Args:
            file_report: FileReport to serialize.

        Returns:
            Dictionary representation.
        """
        return {
            "filepath": file_report.filepath,
            "score": file_report.score,
            "grade": file_report.grade,
            "passed": file_report.passed,
            "issue_count": file_report.issue_count,
            "severity_counts": file_report.severity_counts,
            "metrics": file_report.metrics,
            "issues": [
                self._serialize_issue(issue) for issue in file_report.issues
            ],
        }

    def _serialize_issue(self, issue) -> dict:
        """Serialize an issue to dictionary.

        Args:
            issue: Issue to serialize.

        Returns:
            Dictionary representation.
        """
        return {
            "rule": issue.rule,
            "message": issue.message,
            "severity": issue.severity,
            "filepath": issue.filepath,
            "lineno": issue.lineno,
            "col_offset": issue.col_offset,
            "end_lineno": issue.end_lineno,
            "category": issue.category,
            "confidence": issue.confidence,
            "suggestion": issue.suggestion,
            "code_snippet": issue.code_snippet,
        }
