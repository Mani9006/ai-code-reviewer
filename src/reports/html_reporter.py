"""HTML report generator for code review results."""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.analyzer import ReviewReport

logger = logging.getLogger(__name__)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeReview AI Report - {title}</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-green: #3fb950;
            --accent-yellow: #d29922;
            --accent-orange: #f0883e;
            --accent-red: #f85149;
            --accent-blue: #58a6ff;
            --accent-purple: #bc8cff;
            --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        header {{
            text-align: center;
            padding: 3rem 2rem;
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 2rem;
        }}
        header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        header .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .summary-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.2s;
        }}
        .summary-card:hover {{ transform: translateY(-2px); }}
        .summary-card .value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}
        .summary-card .label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .grade {{
            font-size: 4rem;
            font-weight: 800;
        }}
        .grade-a {{ color: var(--accent-green); }}
        .grade-b {{ color: var(--accent-yellow); }}
        .grade-c {{ color: var(--accent-orange); }}
        .grade-d {{ color: var(--accent-red); }}
        .grade-f {{ color: #ff0000; }}
        .score-bar {{
            width: 100%;
            height: 12px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            overflow: hidden;
            margin-top: 0.5rem;
        }}
        .score-fill {{
            height: 100%;
            border-radius: 6px;
            transition: width 1s ease;
        }}
        .section {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        .section-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--text-primary);
        }}
        .section-body {{ padding: 1.5rem; }}
        .file-item {{
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 1rem;
            overflow: hidden;
        }}
        .file-header {{
            padding: 1rem 1.25rem;
            background: var(--bg-tertiary);
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }}
        .file-name {{
            font-family: var(--font-mono);
            font-size: 0.9rem;
            color: var(--accent-blue);
        }}
        .file-score {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-info {{ background: rgba(88, 166, 255, 0.15); color: var(--accent-blue); }}
        .badge-warning {{ background: rgba(210, 153, 34, 0.15); color: var(--accent-yellow); }}
        .badge-error {{ background: rgba(248, 81, 73, 0.15); color: var(--accent-red); }}
        .badge-critical {{ background: rgba(248, 81, 73, 0.25); color: #ff6b6b; border: 1px solid rgba(248, 81, 73, 0.4); }}
        .issue-list {{
            list-style: none;
            padding: 1rem 1.25rem;
        }}
        .issue-item {{
            padding: 0.875rem 1rem;
            margin-bottom: 0.75rem;
            border-left: 3px solid;
            border-radius: 0 6px 6px 0;
            background: var(--bg-tertiary);
        }}
        .issue-info {{ border-left-color: var(--accent-blue); }}
        .issue-warning {{ border-left-color: var(--accent-yellow); }}
        .issue-error {{ border-left-color: var(--accent-red); }}
        .issue-critical {{ border-left-color: #ff0000; background: rgba(248, 81, 73, 0.08); }}
        .issue-rule {{
            font-family: var(--font-mono);
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .issue-info .issue-rule {{ color: var(--accent-blue); }}
        .issue-warning .issue-rule {{ color: var(--accent-yellow); }}
        .issue-error .issue-rule {{ color: var(--accent-red); }}
        .issue-critical .issue-rule {{ color: #ff0000; }}
        .issue-message {{
            color: var(--text-primary);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}
        .issue-location {{
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
        }}
        .issue-suggestion {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            padding: 0.5rem 0.75rem;
            background: var(--bg-secondary);
            border-radius: 6px;
            border-left: 2px solid var(--accent-green);
        }}
        .issue-suggestion::before {{
            content: "Suggestion: ";
            font-weight: 600;
            color: var(--accent-green);
        }}
        .severity-counts {{
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        .metric {{
            text-align: center;
            padding: 1rem;
            background: var(--bg-tertiary);
            border-radius: 8px;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent-blue);
        }}
        .metric-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }}
        .code-snippet {{
            font-family: var(--font-mono);
            font-size: 0.85rem;
            background: var(--bg-primary);
            padding: 0.75rem 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin-top: 0.5rem;
            color: var(--text-primary);
        }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .passed {{ color: var(--accent-green); }}
        .failed {{ color: var(--accent-red); }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .section {{ animation: fadeIn 0.3s ease-out; }}
    </style>
</head>
<body>
    <div class="container">
        {content}
        <div class="footer">
            <p>Generated by CodeReview AI v1.0.0 on {timestamp}</p>
        </div>
    </div>
</body>
</html>"""


class HTMLReporter:
    """Generate HTML reports from review results."""

    def __init__(self, output_dir: str = "./code_review_reports") -> None:
        """Initialize HTML reporter.

        Args:
            output_dir: Directory for output files.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, report: "ReviewReport", filename: str = "report.html") -> Path:
        """Generate an HTML report.

        Args:
            report: Review report to render.
            filename: Output filename.

        Returns:
            Path to generated HTML file.
        """
        content = self._render_report(report)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_output = HTML_TEMPLATE.format(
            title="Code Review Report",
            content=content,
            timestamp=timestamp,
        )

        output_path = self.output_dir / filename
        output_path.write_text(html_output, encoding="utf-8")
        logger.info("HTML report generated: %s", output_path)
        return output_path

    def _render_report(self, report: "ReviewReport") -> str:
        """Render report content as HTML.

        Args:
            report: Review report.

        Returns:
            HTML content string.
        """
        parts: list[str] = []

        parts.append(self._render_header(report))
        parts.append(self._render_summary(report))
        parts.append(self._render_file_reports(report))

        return "\n".join(parts)

    def _render_header(self, report: "ReviewReport") -> str:
        """Render report header.

        Args:
            report: Review report.

        Returns:
            HTML header string.
        """
        grade_class = self._get_grade_class(report.overall_grade)
        status = "passed" if report.passed else "failed"
        status_text = "PASSED" if report.passed else "FAILED"

        return f"""
        <header>
            <h1>CodeReview AI Report</h1>
            <p class="subtitle">Automated Code Quality Analysis</p>
            <div class="grade {grade_class}">{report.overall_grade}</div>
            <p style="margin-top: 0.5rem;">
                <span class="{status}">{status_text}</span> |
                Overall Score: {report.overall_score}/100
            </p>
        </header>"""

    def _render_summary(self, report: "ReviewReport") -> str:
        """Render summary section.

        Args:
            report: Review report.

        Returns:
            HTML summary string.
        """
        summary = report.summary
        sev = summary.get("severity_totals", {})

        return f"""
        <div class="summary-grid">
            <div class="summary-card">
                <div class="value">{summary.get("total_files", 0)}</div>
                <div class="label">Files Analyzed</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: var(--accent-red);">{report.total_issues}</div>
                <div class="label">Total Issues</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: var(--accent-blue);">{summary.get("files_with_issues", 0)}</div>
                <div class="label">Files with Issues</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: var(--accent-yellow);">{sev.get("warning", 0)}</div>
                <div class="label">Warnings</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: var(--accent-red);">{sev.get("error", 0)}</div>
                <div class="label">Errors</div>
            </div>
            <div class="summary-card">
                <div class="value" style="color: #ff0000;">{sev.get("critical", 0)}</div>
                <div class="label">Critical</div>
            </div>
        </div>"""

    def _render_file_reports(self, report: "ReviewReport") -> str:
        """Render file-level reports.

        Args:
            report: Review report.

        Returns:
            HTML string.
        """
        parts: list[str] = []

        parts.append('<div class="section">')
        parts.append(
            '<div class="section-header">'
            f'<span class="section-title">File Analysis '
            f'({len(report.files)} files)</span>'
            '</div>'
        )
        parts.append('<div class="section-body">')

        for file_report in report.files:
            parts.append(self._render_file_report(file_report))

        parts.append("</div></div>")
        return "\n".join(parts)

    def _render_file_report(self, file_report) -> str:
        """Render a single file report.

        Args:
            file_report: FileReport to render.

        Returns:
            HTML string.
        """
        grade_class = self._get_grade_class(file_report.grade)
        sev = file_report.severity_counts

        issues_html = ""
        if file_report.issues:
            issues_html = '<ul class="issue-list">'
            for issue in file_report.issues:
                issues_html += self._render_issue(issue)
            issues_html += "</ul>"
        else:
            issues_html = (
                '<p style="padding: 1rem; color: var(--accent-green); '
                'text-align: center;">No issues found!</p>'
            )

        # Metrics
        metrics_html = ""
        if file_report.metrics:
            metrics_html = '<div class="metrics-grid">'
            for key, value in file_report.metrics.items():
                if isinstance(value, (int, float)):
                    label = key.replace("_", " ").title()
                    metrics_html += (
                        f'<div class="metric">'
                        f'<div class="metric-value">{value}</div>'
                        f'<div class="metric-label">{label}</div>'
                        f'</div>'
                    )
            metrics_html += "</div>"

        return f"""
        <div class="file-item">
            <div class="file-header">
                <span class="file-name">{html.escape(file_report.filepath)}</span>
                <div class="file-score">
                    <div class="score-bar" style="width: 100px;">
                        <div class="score-fill" style="width: {file_report.score}%; 
                            background: {'var(--accent-green)' if file_report.score >= 80 else 'var(--accent-yellow)' if file_report.score >= 70 else 'var(--accent-red)'}">
                        </div>
                    </div>
                    <span class="grade {grade_class}">{file_report.grade}</span>
                    <span>{file_report.score:.1f}</span>
                    <div class="severity-counts">
                        <span class="badge badge-info">{sev.get("info", 0)} info</span>
                        <span class="badge badge-warning">{sev.get("warning", 0)} warn</span>
                        <span class="badge badge-error">{sev.get("error", 0)} err</span>
                        <span class="badge badge-critical">{sev.get("critical", 0)} crit</span>
                    </div>
                </div>
            </div>
            {metrics_html}
            {issues_html}
        </div>"""

    def _render_issue(self, issue) -> str:
        """Render a single issue.

        Args:
            issue: Issue to render.

        Returns:
            HTML string.
        """
        severity_class = f"issue-{issue.severity}"
        suggestion_html = ""
        if issue.suggestion:
            suggestion_html = (
                f'<div class="issue-suggestion">'
                f'{html.escape(issue.suggestion)}</div>'
            )

        code_html = ""
        if issue.code_snippet:
            escaped_code = html.escape(issue.code_snippet)
            code_html = f'<div class="code-snippet">{escaped_code}</div>'

        return f"""
        <li class="issue-item {severity_class}">
            <div class="issue-rule">{html.escape(issue.rule)}</div>
            <div class="issue-message">{html.escape(issue.message)}</div>
            <div class="issue-location">
                Line {issue.lineno}, Col {issue.col_offset}
                {" - " + html.escape(issue.category) if issue.category else ""}
            </div>
            {suggestion_html}
            {code_html}
        </li>"""

    def _get_grade_class(self, grade: str) -> str:
        """Get CSS class for a grade.

        Args:
            grade: Letter grade.

        Returns:
            CSS class name.
        """
        grade_map = {
            "A+": "grade-a", "A": "grade-a", "A-": "grade-a",
            "B+": "grade-b", "B": "grade-b", "B-": "grade-b",
            "C+": "grade-c", "C": "grade-c", "C-": "grade-c",
            "D": "grade-d", "F": "grade-f",
        }
        return grade_map.get(grade, "grade-f")
