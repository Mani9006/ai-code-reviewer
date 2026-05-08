"""Command-line interface for CodeReview AI."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from src.analyzer import CodeAnalyzer
from src.config import Config, load_config
from src.reports.html_reporter import HTMLReporter
from src.reports.json_reporter import JSONReporter
from src.reports.markdown_reporter import MarkdownReporter

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
}

SEVERITY_COLORS = {
    "info": COLORS["bright_blue"],
    "warning": COLORS["bright_yellow"],
    "error": COLORS["bright_red"],
    "critical": COLORS["bright_magenta"],
}

GRADE_COLORS = {
    "A+": COLORS["bright_green"],
    "A": COLORS["bright_green"],
    "A-": COLORS["green"],
    "B+": COLORS["bright_cyan"],
    "B": COLORS["cyan"],
    "B-": COLORS["yellow"],
    "C+": COLORS["bright_yellow"],
    "C": COLORS["yellow"],
    "C-": COLORS["yellow"],
    "D": COLORS["red"],
    "F": COLORS["bright_red"],
}


def setup_logging(verbose: bool = False) -> None:
    """Configure logging.

    Args:
        verbose: Enable verbose logging.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def print_banner() -> None:
    """Print the CodeReview AI banner."""
    banner = f"""
{COLORS['bright_cyan']}  ____          _       _                  _       ___  {COLORS['reset']}
{COLORS['bright_cyan']} / ___|___   __| | ___ | | _____   ___ __ (_) ___ |_ _| {COLORS['reset']}
{COLORS['bright_blue']}| |   / _ \\ / _` |/ _ \\| |/ / _ \\ / __/ _ \\| |/ _ \\ | |  {COLORS['reset']}
{COLORS['bright_magenta']}| |__| (_) | (_| | (_) |   <  __/| (_| (_) | |  __/ | |  {COLORS['reset']}
{COLORS['bright_magenta']} \\____\\___/ \\__,_|\\___/|_|\\_\\___(_)___\\___/|_|\\___||___| {COLORS['reset']}
{COLORS['dim']}                                                        v1.0.0{COLORS['reset']}
"""
    print(banner)


def print_progress(message: str, done: bool = False) -> None:
    """Print a progress message.

    Args:
        message: Message to display.
        done: Whether the task is complete.
    """
    icon = f"{COLORS['bright_green']}✓{COLORS['reset']}" if done else f"{COLORS['bright_blue']}→{COLORS['reset']}"
    print(f"  {icon} {message}")


def print_file_report(file_report, index: int, total: int) -> None:
    """Print a file report to the console.

    Args:
        file_report: FileReport to display.
        index: File index.
        total: Total files.
    """
    grade_color = GRADE_COLORS.get(file_report.grade, COLORS["white"])
    status = f"{COLORS['bright_green']}✓ PASS{COLORS['reset']}" if file_report.passed else f"{COLORS['bright_red']}✗ FAIL{COLORS['reset']}"
    sev = file_report.severity_counts

    print(f"\n{COLORS['bold']}[{index}/{total}]{COLORS['reset']} {COLORS['cyan']}{file_report.filepath}{COLORS['reset']}")
    print(f"  Score: {grade_color}{file_report.score:.1f}{COLORS['reset']}/100  Grade: {grade_color}{file_report.grade}{COLORS['reset']}  {status}")

    if not file_report.issues:
        print(f"  {COLORS['bright_green']}No issues found!{COLORS['reset']}")
        return

    # Print severity summary
    summary_parts = []
    for sev_name in ["info", "warning", "error", "critical"]:
        count = sev.get(sev_name, 0)
        if count > 0:
            color = SEVERITY_COLORS.get(sev_name, COLORS["white"])
            summary_parts.append(f"{color}{count} {sev_name}{COLORS['reset']}")
    if summary_parts:
        print(f"  Issues: {', '.join(summary_parts)}")

    # Print issues
    for issue in file_report.issues:
        sev_color = SEVERITY_COLORS.get(issue.severity, COLORS["white"])
        severity_icon = {
            "info": "ℹ",
            "warning": "⚠",
            "error": "✖",
            "critical": "!",
        }.get(issue.severity, "•")

        print(f"\n  {sev_color}[{severity_icon}] {COLORS['bold']}{issue.rule}{COLORS['reset']}")
        print(f"     {issue.message}")
        print(f"     {COLORS['dim']}→ Line {issue.lineno}{COLORS['reset']}")
        if issue.suggestion:
            print(f"     {COLORS['bright_green']}💡 {issue.suggestion}{COLORS['reset']}")


def print_summary(report) -> None:
    """Print the overall summary.

    Args:
        report: ReviewReport to summarize.
    """
    grade_color = GRADE_COLORS.get(report.overall_grade, COLORS["white"])
    status_text = f"{COLORS['bright_green']}PASSED{COLORS['reset']}" if report.passed else f"{COLORS['bright_red']}FAILED{COLORS['reset']}"
    status_icon = "✓" if report.passed else "✗"

    print(f"\n{'=' * 60}")
    print(f"  {COLORS['bold']}CODE REVIEW SUMMARY{COLORS['reset']}")
    print(f"{'=' * 60}")
    print(f"  Overall Grade: {grade_color}{COLORS['bold']}{report.overall_grade}{COLORS['reset']}")
    print(f"  Overall Score: {grade_color}{report.overall_score:.1f}{COLORS['reset']}/100")
    print(f"  Status: {status_icon} {status_text}")
    print(f"  Files Analyzed: {report.summary.get('total_files', 0)}")
    print(f"  Files with Issues: {report.summary.get('files_with_issues', 0)}")
    print(f"  Total Issues: {report.total_issues}")

    sev = report.summary.get("severity_totals", {})
    print(f"\n  {COLORS['bold']}Issue Breakdown:{COLORS['reset']}")
    for sev_name in ["info", "warning", "error", "critical"]:
        count = sev.get(sev_name, 0)
        color = SEVERITY_COLORS.get(sev_name, COLORS["white"])
        print(f"    {color}• {sev_name.capitalize()}: {count}{COLORS['reset']}")

    print(f"\n  Duration: {report.duration_ms:.0f}ms")
    print(f"{'=' * 60}")

    if not report.passed:
        print(
            f"\n  {COLORS['bright_yellow']}⚠ Score below threshold. "
            f"Review required.{COLORS['reset']}"
        )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="codereview-ai",
        description="AI-powered Code Review Assistant for Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze src/                    Analyze all Python files in src/
  %(prog)s analyze file.py                 Analyze a single file
  %(prog)s analyze src/ -o report.html     Generate HTML report
  %(prog)s analyze src/ --format json      Output as JSON
  %(prog)s analyze src/ --fail-threshold 80  Set custom fail threshold
  %(prog)s analyze src/ -c config.json     Use custom configuration
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze Python code",
        description="Analyze Python files or directories for code quality issues.",
    )
    analyze_parser.add_argument(
        "path",
        help="Path to Python file or directory to analyze",
    )
    analyze_parser.add_argument(
        "-o", "--output",
        help="Output file path for the report",
    )
    analyze_parser.add_argument(
        "-f", "--format",
        choices=["html", "markdown", "md", "json", "console"],
        default="console",
        help="Report output format (default: console)",
    )
    analyze_parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
    )
    analyze_parser.add_argument(
        "--fail-threshold",
        type=float,
        default=70.0,
        help="Score threshold for passing (default: 70.0)",
    )
    analyze_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse into subdirectories",
    )
    analyze_parser.add_argument(
        "--no-suggestions",
        action="store_true",
        help="Disable AI-powered suggestions",
    )
    analyze_parser.add_argument(
        "--severity",
        choices=["info", "warning", "error", "critical"],
        help="Minimum severity level to report",
    )

    # config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
    )
    config_parser.add_argument(
        "action",
        choices=["init", "show"],
        help="Configuration action",
    )
    config_parser.add_argument(
        "-o", "--output",
        default=".codereview.json",
        help="Configuration file path (default: .codereview.json)",
    )

    # self-analyze command
    subparsers.add_parser(
        "self-analyze",
        help="Analyze the CodeReview AI tool itself",
    )

    return parser


def handle_analyze(args: argparse.Namespace) -> int:
    """Handle the analyze command.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = load_config(args.config)
    config.fail_threshold = args.fail_threshold
    if args.no_suggestions:
        config.ai_suggestions = False

    analyzer = CodeAnalyzer(config)
    path = Path(args.path)

    print_banner()
    print_progress(f"Analyzing: {path}")

    if path.is_file():
        file_report = analyzer.analyze_file(path)
        print_file_report(file_report, 1, 1)

        # Generate report if requested
        if args.output or args.format != "console":
            _generate_report([file_report], args)

        return 0 if file_report.passed else 1

    elif path.is_dir():
        report = analyzer.analyze_directory(path, recursive=not args.no_recursive)

        for i, file_report in enumerate(report.files, 1):
            print_file_report(file_report, i, len(report.files))

        print_summary(report)

        # Generate report if requested
        if args.output or args.format != "console":
            _generate_report(report.files, args, report)

        return 0 if report.passed else 1

    else:
        print(
            f"{COLORS['bright_red']}Error: Path not found: "
            f"{path}{COLORS['reset']}"
        )
        return 1


def handle_config(args: argparse.Namespace) -> int:
    """Handle the config command.

    Args:
        args: Parsed arguments.

    Returns:
        Exit code.
    """
    if args.action == "init":
        config = Config()
        config.to_file(args.output)
        print(
            f"{COLORS['bright_green']}✓ Configuration initialized: "
            f"{args.output}{COLORS['reset']}"
        )
    elif args.action == "show":
        import json

        config = load_config()
        print(json.dumps(config.to_dict(), indent=2))
    return 0


def handle_self_analyze() -> int:
    """Handle the self-analyze command.

    Returns:
        Exit code.
    """
    print_banner()
    print_progress("Analyzing CodeReview AI itself...")

    config = load_config()
    analyzer = CodeAnalyzer(config)

    # Find the src directory
    src_dir = Path(__file__).parent
    report = analyzer.analyze_directory(src_dir)

    for i, file_report in enumerate(report.files, 1):
        print_file_report(file_report, i, len(report.files))

    print_summary(report)
    return 0 if report.passed else 1


def _generate_report(
    file_reports, args: argparse.Namespace, report=None
) -> None:
    """Generate output report.

    Args:
        file_reports: List of FileReport objects.
        args: Parsed arguments.
        report: Optional ReviewReport.
    """
    if not report:
        from src.analyzer import ReviewReport

        total_issues = sum(fr.issue_count for fr in file_reports)
        report = ReviewReport(
            files=file_reports,
            total_issues=total_issues,
        )

    output_dir = "./code_review_reports"
    if args.output:
        output_path = Path(args.output)
        output_dir = str(output_path.parent)

    fmt = args.format

    if fmt == "html":
        reporter = HTMLReporter(output_dir)
        path = reporter.generate(report)
        print(f"\n  {COLORS['bright_green']}HTML report: {path}{COLORS['reset']}")
    elif fmt in ("markdown", "md"):
        reporter = MarkdownReporter(output_dir)
        path = reporter.generate(report)
        print(f"\n  {COLORS['bright_green']}Markdown report: {path}{COLORS['reset']}")
    elif fmt == "json":
        reporter = JSONReporter(output_dir)
        path = reporter.generate(report)
        print(f"\n  {COLORS['bright_green']}JSON report: {path}{COLORS['reset']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Exit code.
    """
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)

    # Handle no-color option
    if getattr(args, "no_color", False):
        for key in COLORS:
            COLORS[key] = ""
        SEVERITY_COLORS.clear()
        GRADE_COLORS.clear()

    if args.command == "analyze":
        return handle_analyze(args)
    elif args.command == "config":
        return handle_config(args)
    elif args.command == "self-analyze":
        return handle_self_analyze()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
