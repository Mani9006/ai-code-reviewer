"""Markdown report generator for code review results."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.analyzer import ReviewReport

logger = logging.getLogger(__name__)


SEVERITY_EMOJIS = {
    "info": ":information_source:",
    "warning": ":warning:",
    "error": ":x:",
    "critical": ":rotating_light:",
}

SEVERITY_BADGES = {
    "info": "![Info](https://img.shields.io/badge/-info-blue)",
    "warning": "![Warning](https://img.shields.io/badge/-warning-yellow)",
    "error": "![Error](https://img.shields.io/badge/-error-red)",
    "critical": "![Critical](https://img.shields.io/badge/-critical-critical)",
}


class MarkdownReporter:
    """Generate Markdown reports from review results."""

    def __init__(self, output_dir: str = "./code_review_reports") -> None:
        """Initialize Markdown reporter.

        Args:
            output_dir: Directory for output files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self, report: "ReviewReport", filename: str = "report.md"
    ) -> Path:
        """Generate a Markdown report.

        Args:
            report: Review report to render.
            filename: Output filename.

        Returns:
            Path to generated Markdown file.
        """
        content = self._render_report(report)
        output_path = self.output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        logger.info("Markdown report generated: %s", output_path)
        return output_path

    def _render_report(self, report: "ReviewReport") -> str:
        """Render full report as Markdown.

        Args:
            report: Review report.

        Returns:
            Markdown content string.
        """
        lines: list[str] = []

        lines.extend(self._render_header(report))
        lines.extend(self._render_summary(report))
        lines.extend(self._render_details(report))
        lines.extend(self._render_footer())

        return "\n\n".join(lines)

    def _render_header(self, report: "ReviewReport") -> list[str]:
        """Render report header.

        Args:
            report: Review report.

        Returns:
            List of markdown lines.
        """
        status = "PASS" if report.passed else "FAIL"
        status_emoji = ":white_check_mark:" if report.passed else ":no_entry:"

        return [
            "# CodeReview AI Report",
            "",
            f"## Overall Result: {status} {status_emoji}",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| **Score** | {report.overall_score:.1f}/100 |",
            f"| **Grade** | {report.overall_grade} |",
            f"| **Status** | {'PASSED' if report.passed else 'FAILED'} |",
            f"| **Files Analyzed** | {report.summary.get('total_files', 0)} |",
            f"| **Total Issues** | {report.total_issues} |",
            f"| **Duration** | {report.duration_ms:.0f}ms |",
            "",
        ]

    def _render_summary(self, report: "ReviewReport") -> list[str]:
        """Render summary section.

        Args:
            report: Review report.

        Returns:
            List of markdown lines.
        """
        lines: list[str] = []
        sev = report.summary.get("severity_totals", {})

        lines.extend([
            "## Severity Breakdown",
            "",
            "| Severity | Count |",
            "|----------|-------|",
            f"| :information_source: Info | {sev.get('info', 0)} |",
            f"| :warning: Warning | {sev.get('warning', 0)} |",
            f"| :x: Error | {sev.get('error', 0)} |",
            f"| :rotating_light: Critical | {sev.get('critical', 0)} |",
            "",
        ])

        return lines

    def _render_details(self, report: "ReviewReport") -> list[str]:
        """Render detailed file reports.

        Args:
            report: Review report.

        Returns:
            List of markdown lines.
        """
        lines: list[str] = [
            "## File Analysis Details",
            "",
        ]

        for file_report in report.files:
            lines.extend(self._render_file_report(file_report))

        return lines

    def _render_file_report(self, file_report) -> list[str]:
        """Render a single file report.

        Args:
            file_report: FileReport to render.

        Returns:
            List of markdown lines.
        """
        lines: list[str] = []
        status = "PASS" if not file_report.issues else "ISSUES"

        lines.extend([
            f"### `{file_report.filepath}`",
            "",
            f"**Score:** {file_report.score:.1f}/100 | "
            f"**Grade:** {file_report.grade} | "
            f"**Status:** {status}",
            "",
        ])

        # Metrics table
        if file_report.metrics:
            lines.extend([
                "**Metrics:**",
                "",
            ])
            for key, value in file_report.metrics.items():
                if isinstance(value, (int, float, str)):
                    label = key.replace("_", " ").title()
                    lines.append(f"- **{label}:** {value}")
            lines.append("")

        # Issues
        if file_report.issues:
            lines.append("**Issues:**")
            lines.append("")
            for issue in file_report.issues:
                badge = SEVERITY_BADGES.get(issue.severity, "")
                lines.extend([
                    f"- {badge} **{issue.rule}** (Line {issue.lineno})",
                    f"  - {issue.message}",
                ])
                if issue.suggestion:
                    lines.append(f"  - *Fix:* {issue.suggestion}")
            lines.append("")
        else:
            lines.extend([
                ":white_check_mark: No issues found in this file.",
                "",
            ])

        return lines

    def _render_footer(self) -> list[str]:
        """Render report footer.

        Returns:
            List of markdown lines.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return [
            "---",
            "",
            f"*Report generated by CodeReview AI v1.0.0 on {timestamp}*",
        ]
