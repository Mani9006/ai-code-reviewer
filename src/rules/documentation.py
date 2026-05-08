"""Documentation coverage and docstring quality rule checks."""

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

# Google/NumPy/Sphinx docstring section patterns
DOCSTRING_SECTIONS = [
    re.compile(r"^\s*Args\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Arguments\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Parameters\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Returns\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Raises\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Yields\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Examples\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*Note\s*:\s*$", re.MULTILINE),
    re.compile(r"^\s*TODO\s*:\s*$", re.MULTILINE),
    # Sphinx style
    re.compile(r":param\s+\w+"),
    re.compile(r":return[s]?"),
    re.compile(r":raise[s]?"),
    re.compile(r":type\s+\w+"),
    re.compile(r":rtype"),
]


def check(module: ModuleInfo, config: Config, filepath: Path) -> list["Issue"]:
    """Check documentation-related rules.

    Args:
        module: Parsed module information.
        config: Configuration object.
        filepath: Path to the file being analyzed.

    Returns:
        List of Issue objects for documentation violations.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    rule_cfg = config.rules.get("documentation", {})
    require_docstrings = rule_cfg.get("require_docstrings", True)
    min_coverage = config.min_docstring_coverage

    # Module-level docstring check
    if not module.docstring and require_docstrings and module.total_lines > 10:
        issues.append(
            Issue(
                rule="missing_module_docstring",
                message="Module is missing a docstring",
                severity="warning",
                filepath=str(filepath),
                lineno=1,
                category="documentation",
                suggestion="Add a module-level docstring describing the "
                "purpose of this module.",
            )
        )

    # Function docstring checks
    for func in module.functions:
        if _is_dunder_method(func.name) or func.name.startswith("_"):
            continue

        if not func.docstring and require_docstrings:
            severity = (
                "error"
                if func.complexity > config.max_cyclomatic_complexity // 2
                else "warning"
            )
            issues.append(
                Issue(
                    rule="missing_function_docstring",
                    message=f"Function '{func.name}' is missing a docstring",
                    severity=severity,
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="documentation",
                    suggestion=f"Add a docstring to '{func.name}' describing "
                    f"its purpose, parameters, and return value.",
                )
            )
        elif func.docstring:
            # Check docstring quality
            quality_issues = _check_docstring_quality(
                func.docstring, func, filepath, str(filepath)
            )
            issues.extend(quality_issues)

    # Class docstring checks
    for cls in module.classes:
        if not cls.docstring and require_docstrings:
            issues.append(
                Issue(
                    rule="missing_class_docstring",
                    message=f"Class '{cls.name}' is missing a docstring",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=cls.lineno,
                    category="documentation",
                    suggestion=f"Add a docstring to class '{cls.name}' "
                    f"describing its purpose and usage.",
                )
            )
        elif cls.docstring:
            # Check class docstring quality
            if len(cls.docstring.strip()) < 10:
                issues.append(
                    Issue(
                        rule="short_class_docstring",
                        message=f"Class '{cls.name}' has a very short "
                        "docstring",
                        severity="info",
                        filepath=str(filepath),
                        lineno=cls.lineno,
                        category="documentation",
                        suggestion="Expand the class docstring to provide "
                        "more context about its purpose.",
                    )
                )

    # Method docstring checks
    for cls in module.classes:
        for method in cls.methods:
            if (
                _is_dunder_method(method.name)
                or method.name.startswith("_")
                or method.name == "__init__"
            ):
                continue

            if not method.docstring and require_docstrings:
                issues.append(
                    Issue(
                        rule="missing_method_docstring",
                        message=f"Method '{cls.name}.{method.name}' is "
                        "missing a docstring",
                        severity="info",
                        filepath=str(filepath),
                        lineno=method.lineno,
                        category="documentation",
                        suggestion=f"Add a docstring to '{method.name}'.",
                    )
                )

    # Check for TODO/FIXME comments
    issues.extend(_check_todo_comments(module, filepath))

    # Calculate docstring coverage
    total = len(module.functions) + len(module.classes)
    documented = sum(1 for f in module.functions if f.docstring)
    documented += sum(1 for c in module.classes if c.docstring)

    if total > 0:
        coverage = (documented / total) * 100
        if coverage < min_coverage:
            issues.append(
                Issue(
                    rule="low_docstring_coverage",
                    message=f"Docstring coverage is {coverage:.1f}% "
                    f"(min: {min_coverage}%)",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=1,
                    category="documentation",
                    suggestion=f"Add docstrings to undocumented functions "
                    f"and classes to reach {min_coverage}% coverage.",
                )
            )

    logger.debug("Documentation check found %d issues in %s", len(issues), filepath)
    return issues


def _is_dunder_method(name: str) -> bool:
    """Check if method name is a dunder method.

    Args:
        name: Method name to check.

    Returns:
        True if name starts and ends with double underscore.
    """
    return name.startswith("__") and name.endswith("__")


def _check_docstring_quality(
    docstring: str, func, filepath: Path, filepath_str: str
) -> list:
    """Check the quality of a function docstring.

    Args:
        docstring: The docstring content.
        func: Function info.
        filepath: Path to file.
        filepath_str: String version of filepath.

    Returns:
        List of quality issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Check length
    stripped = docstring.strip()
    if len(stripped) < 10:
        issues.append(
            Issue(
                rule="short_docstring",
                message=f"Docstring for '{func.name}' is too short",
                severity="info",
                filepath=filepath_str,
                lineno=func.lineno,
                category="documentation",
                suggestion="Expand the docstring with more details.",
            )
        )

    # Check if args are documented
    if func.args and len(func.args) > 0:
        has_param_docs = any(p.search(docstring) for p in DOCSTRING_SECTIONS)
        if not has_param_docs:
            issues.append(
                Issue(
                    rule="undocumented_parameters",
                    message=f"Parameters of '{func.name}' are not "
                    "documented in docstring",
                    severity="info",
                    filepath=filepath_str,
                    lineno=func.lineno,
                    category="documentation",
                    suggestion="Document all parameters using Args:, "
                    "Parameters:, or :param: sections.",
                )
            )

    # Check if return is documented for non-None returns
    if func.returns:
        has_return_doc = any(
            p.search(docstring)
            for p in [
                re.compile(r"^\s*Returns\s*:", re.MULTILINE),
                re.compile(r":return[s]?"),
            ]
        )
        if not has_return_doc:
            issues.append(
                Issue(
                    rule="undocumented_return",
                    message=f"Return value of '{func.name}' is not "
                    "documented",
                    severity="info",
                    filepath=filepath_str,
                    lineno=func.lineno,
                    category="documentation",
                    suggestion="Document the return value using Returns: "
                    "or :return:.",
                )
            )

    # Check for proper formatting
    if "\"\"\"" not in docstring and "'" * 3 not in docstring:
        # Docstring content without the delimiters
        pass  # This is normal for ast.get_docstring

    return issues


def _check_todo_comments(module: ModuleInfo, filepath: Path) -> list:
    """Check for TODO and FIXME comments.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of TODO/FIXME issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError:
        return issues
    lines = source.split("\n")

    todo_pattern = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|BUG)", re.IGNORECASE)

    for lineno, line in enumerate(lines, 1):
        match = todo_pattern.search(line)
        if match:
            keyword = match.group(1).upper()
            severity_map = {
                "TODO": "info",
                "FIXME": "warning",
                "HACK": "warning",
                "XXX": "info",
                "BUG": "error",
            }
            issues.append(
                Issue(
                    rule=f"{keyword.lower()}_comment",
                    message=f"Found {keyword} comment: "
                    f"{line.strip()[:60]}",
                    severity=severity_map.get(keyword, "info"),
                    filepath=str(filepath),
                    lineno=lineno,
                    category="documentation",
                    suggestion=f"Resolve the {keyword} item or create a "
                    f"ticket to track it.",
                )
            )

    return issues
