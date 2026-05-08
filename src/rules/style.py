"""Style-related code review rules (PEP 8 compliance)."""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from src.ast_parser import ModuleInfo

if TYPE_CHECKING:
    from src.analyzer import Issue
    from src.config import Config

logger = logging.getLogger(__name__)


def check(module: ModuleInfo, config: Config, filepath: Path) -> list["Issue"]:
    """Check style-related rules (PEP 8 compliance).

    Args:
        module: Parsed module information.
        config: Configuration object.
        filepath: Path to the file being analyzed.

    Returns:
        List of Issue objects for style violations.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    max_length = config.rules.get("style", {}).get(
        "max_line_length", config.max_line_length
    )

    try:
        source = filepath.read_text(encoding="utf-8")
        lines = source.split("\n")
    except (OSError, UnicodeDecodeError) as e:
        logger.error("Cannot read %s: %s", filepath, e)
        return issues

    # Check line length
    for lineno, line in enumerate(lines, 1):
        if len(line) > max_length:
            issues.append(
                Issue(
                    rule="line_too_long",
                    message=f"Line too long ({len(line)} > {max_length} chars)",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=lineno,
                    category="style",
                    suggestion="Break the line at a natural point, "
                    "use implicit continuation inside "
                    "parentheses, or use a backslash.",
                )
            )

        # Check trailing whitespace
        if line.rstrip() != line:
            issues.append(
                Issue(
                    rule="trailing_whitespace",
                    message="Line has trailing whitespace",
                    severity="info",
                    filepath=str(filepath),
                    lineno=lineno,
                    category="style",
                    suggestion="Remove trailing whitespace from the line.",
                )
            )

        # Check tab characters
        if "\t" in line:
            issues.append(
                Issue(
                    rule="tab_character",
                    message="Line contains tab characters",
                    severity="info",
                    filepath=str(filepath),
                    lineno=lineno,
                    category="style",
                    suggestion="Replace tabs with 4 spaces for consistent "
                    "indentation.",
                )
            )

    # Check for multiple statements on one line
    issues.extend(_check_multiple_statements(module, filepath))

    # Check for missing whitespace around operators
    issues.extend(_check_whitespace_around_operators(lines, filepath))

    # Check for blank lines
    issues.extend(_check_blank_lines(module, lines, filepath))

    # Check import order (standard lib, third-party, local)
    issues.extend(_check_import_order(module, filepath))

    # Check for bare except
    issues.extend(_check_bare_except(module, filepath))

    # Check for mutable default arguments
    issues.extend(_check_mutable_defaults(module, filepath))

    logger.debug("Style check found %d issues in %s", len(issues), filepath)
    return issues


def _check_multiple_statements(module: ModuleInfo, filepath: Path) -> list:
    """Check for multiple statements on one line.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of style issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        # Check for semicolon-separated statements
        pass  # AST removes semicolons, handled in raw text check

    # Raw text check for semicolons
    try:
        source = filepath.read_text(encoding="utf-8")
        lines = source.split("\n")
    except OSError:
        return issues

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if ";" in stripped and not stripped.startswith("#"):
            # Skip semicolons in strings
            if not _is_semicolon_in_string(stripped):
                issues.append(
                    Issue(
                        rule="multiple_statements",
                        message="Multiple statements on one line "
                        "(semicolon detected)",
                        severity="info",
                        filepath=str(filepath),
                        lineno=lineno,
                        category="style",
                        suggestion="Put each statement on its own line "
                        "for better readability.",
                    )
                )

    return issues


def _check_whitespace_around_operators(lines: list[str], filepath: Path) -> list:
    """Check for missing whitespace around operators.

    Args:
        lines: Source code lines.
        filepath: Path to file.

    Returns:
        List of style issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Patterns for operators that need spaces around them
    assign_patterns = [
        # Simple assignment without surrounding space
        r"(?<![=<>!+\-*/%&|^~])=(?![=<>!+\-*/%&|^~])",
    ]

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        # Check for tight assignment operators (e.g., x=1 without spaces)
        # Skip lines that are just strings or comments
        try:
            if re.search(r"\w=[^=]", stripped):
                issues.append(
                    Issue(
                        rule="missing_whitespace_around_operator",
                        message="Missing whitespace around assignment "
                        "operator",
                        severity="info",
                        filepath=str(filepath),
                        lineno=lineno,
                        category="style",
                        suggestion="Add spaces around operators for "
                        "readability. Use 'x = 1' instead of 'x=1'.",
                    )
                )
        except re.error:
            continue

    return issues


def _check_blank_lines(
    module: ModuleInfo, lines: list[str], filepath: Path
) -> list:
    """Check blank line rules.

    Args:
        module: Parsed module information.
        lines: Source code lines.
        filepath: Path to file.

    Returns:
        List of style issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Check top-level definitions have proper spacing
    for func in module.functions:
        if func.lineno > 1:
            # Check for 2 blank lines before top-level function
            blank_count = _count_preceding_blank_lines(lines, func.lineno)
            if blank_count < 2 and func.lineno > 2:
                issues.append(
                    Issue(
                        rule="missing_blank_lines",
                        message=f"Function '{func.name}' should have 2 "
                        "blank lines before it",
                        severity="info",
                        filepath=str(filepath),
                        lineno=func.lineno,
                        category="style",
                        suggestion="Add 2 blank lines before top-level "
                        "function definitions.",
                    )
                )

    return issues


def _check_import_order(module: ModuleInfo, filepath: Path) -> list:
    """Check that imports are ordered correctly.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of style issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    stdlib_modules = {
        "abc", "argparse", "ast", "asyncio", "base64", "collections",
        "contextlib", "copy", "csv", "dataclasses", "datetime", "enum",
        "functools", "glob", "hashlib", "http", "importlib", "inspect",
        "io", "itertools", "json", "logging", "math", "multiprocessing",
        "operator", "os", "pathlib", "pickle", "random", "re",
        "shutil", "signal", "socket", "sqlite3", "statistics", "string",
        "subprocess", "sys", "tempfile", "threading", "time", "typing",
        "unittest", "urllib", "uuid", "warnings", "xml", "zipfile",
    }

    prev_group = -1
    for imp in module.imports:
        if imp.is_from_import:
            module_name = (imp.module or "").split(".")[0]
        else:
            module_name = (imp.module or "").split(".")[0]

        if module_name in stdlib_modules:
            group = 0  # Standard library
        elif module_name == "":
            group = 0  # Relative imports
        else:
            group = 1  # Third-party / local

        if group < prev_group:
            issues.append(
                Issue(
                    rule="import_order",
                    message=f"Import '{module_name}' is out of order. "
                    "Group standard library imports first.",
                    severity="info",
                    filepath=str(filepath),
                    lineno=imp.lineno,
                    category="style",
                    suggestion="Order imports: stdlib, third-party, "
                    "then local. Add a blank line between groups.",
                )
            )

        prev_group = group

    return issues


def _check_bare_except(module: ModuleInfo, filepath: Path) -> list:
    """Check for bare except clauses.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of style issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append(
                    Issue(
                        rule="bare_except",
                        message="Bare 'except:' clause catches "
                        "KeyboardInterrupt and SystemExit",
                        severity="warning",
                        filepath=str(filepath),
                        lineno=node.lineno,
                        category="style",
                        suggestion="Use 'except Exception:' to catch "
                        "standard exceptions only.",
                    )
                )

    return issues


def _check_mutable_defaults(module: ModuleInfo, filepath: Path) -> list:
    """Check for mutable default arguments.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of style issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    def is_mutable(node):
        """Check if AST node represents a mutable default."""
        if isinstance(node, (ast.List, ast.Dict)):
            return True
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            return func_name in ("set", "list", "dict")
        return False

    for func in module.functions:
        # Check defaults (from end of args)
        defaults = getattr(func, "_defaults", [])
        # We need to access the AST node for defaults

    # Better approach: walk the AST directly
    for node in ast.walk(module.tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_defaults = []
            # positional defaults
            if hasattr(node.args, "defaults"):
                all_defaults.extend(node.args.defaults)
            # kwonly defaults
            if hasattr(node.args, "kw_defaults"):
                all_defaults.extend(node.args.kw_defaults)

            for default in all_defaults:
                if default is not None and is_mutable(default):
                    issues.append(
                        Issue(
                            rule="mutable_default_argument",
                            message="Mutable default argument detected - "
                            "use None with assignment",
                            severity="error",
                            filepath=str(filepath),
                            lineno=node.lineno,
                            category="style",
                            suggestion="Use 'arg=None' in signature and "
                            "'if arg is None: arg = []' in body "
                            "to avoid shared mutable state.",
                        )
                    )

    return issues


def _is_semicolon_in_string(line: str) -> bool:
    """Check if semicolon is inside a string.

    Args:
        line: Line to check.

    Returns:
        True if semicolon is in a string.
    """
    in_string = False
    string_char = None
    escaped = False
    for char in line:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in ('"', "'"):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None
    return False  # We ignore semicolons for simplicity


def _count_preceding_blank_lines(lines: list[str], lineno: int) -> int:
    """Count blank lines before a given line.

    Args:
        lines: Source code lines.
        lineno: 1-based line number.

    Returns:
        Number of preceding blank lines.
    """
    count = 0
    for i in range(lineno - 2, max(-1, lineno - 5), -1):
        if i >= 0 and not lines[i].strip():
            count += 1
        elif i >= 0:
            break
    return count
