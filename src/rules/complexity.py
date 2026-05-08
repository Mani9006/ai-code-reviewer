"""Cyclomatic and cognitive complexity rule checks."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.ast_parser import ModuleInfo

if TYPE_CHECKING:
    from src.analyzer import Issue
    from src.config import Config

logger = logging.getLogger(__name__)


def check(module: ModuleInfo, config: Config, filepath: Path) -> list["Issue"]:
    """Check complexity-related rules.

    Args:
        module: Parsed module information.
        config: Configuration object.
        filepath: Path to the file being analyzed.

    Returns:
        List of Issue objects for complexity violations.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    rule_cfg = config.rules.get("complexity", {})

    threshold = rule_cfg.get("threshold", config.max_cyclomatic_complexity)
    cognitive_threshold = config.max_cognitive_complexity
    max_nesting = config.max_nesting_depth
    max_params = config.max_function_parameters
    max_methods = config.max_class_methods
    max_file_lines = config.max_file_lines
    max_func_length = config.max_function_length

    # Check file length
    if module.total_lines > max_file_lines:
        issues.append(
            Issue(
                rule="file_too_long",
                message=f"File has {module.total_lines} lines (max: {max_file_lines})",
                severity="warning",
                filepath=str(filepath),
                lineno=1,
                category="complexity",
                suggestion=f"Consider splitting into multiple modules. "
                f"Try extracting classes or functions into separate files.",
            )
        )

    # Check function complexity and length
    for func in module.functions:
        if func.complexity > threshold:
            severity = "error" if func.complexity > threshold * 2 else "warning"
            issues.append(
                Issue(
                    rule="high_cyclomatic_complexity",
                    message=f"Function '{func.name}' has cyclomatic "
                    f"complexity of {func.complexity} (max: {threshold})",
                    severity=severity,
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="complexity",
                    suggestion=_suggest_complexity_reduction(func),
                )
            )

        if func.cognitive_complexity > cognitive_threshold:
            issues.append(
                Issue(
                    rule="high_cognitive_complexity",
                    message=f"Function '{func.name}' has cognitive "
                    f"complexity of {func.cognitive_complexity} "
                    f"(max: {cognitive_threshold})",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="complexity",
                    suggestion="Refactor nested conditionals into separate "
                    "functions or use early returns to reduce "
                    "cognitive load.",
                )
            )

        if func.nesting_depth > max_nesting:
            issues.append(
                Issue(
                    rule="deep_nesting",
                    message=f"Function '{func.name}' has nesting depth "
                    f"of {func.nesting_depth} (max: {max_nesting})",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="complexity",
                    suggestion="Extract deeply nested code into helper "
                    "functions to improve readability.",
                )
            )

        if len(func.args) > max_params:
            issues.append(
                Issue(
                    rule="too_many_arguments",
                    message=f"Function '{func.name}' has {len(func.args)} "
                    f"parameters (max: {max_params})",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="complexity",
                    suggestion="Consider using a dataclass, config object, "
                    "or kwargs to group related parameters.",
                )
            )

        # Check function length
        if func.end_lineno and func.end_lineno - func.lineno > max_func_length:
            issues.append(
                Issue(
                    rule="function_too_long",
                    message=f"Function '{func.name}' spans "
                    f"{func.end_lineno - func.lineno} lines "
                    f"(max: {max_func_length})",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="complexity",
                    suggestion="Break this function into smaller, "
                    "single-responsibility helper functions.",
                )
            )

    # Check class method counts
    for cls in module.classes:
        if len(cls.methods) > max_methods:
            issues.append(
                Issue(
                    rule="too_many_methods",
                    message=f"Class '{cls.name}' has {len(cls.methods)} "
                    f"methods (max: {max_methods})",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=cls.lineno,
                    category="complexity",
                    suggestion="Consider splitting into smaller classes "
                    "using composition or extracting related "
                    "methods into mixins.",
                )
            )

    # Check for try blocks with too many statements
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Try):
            body_len = len(node.body)
            if body_len > 20:
                issues.append(
                    Issue(
                        rule="large_try_block",
                        message=f"Try block has {body_len} statements; "
                        "keep try blocks focused",
                        severity="info",
                        filepath=str(filepath),
                        lineno=node.lineno,
                        category="complexity",
                        suggestion="Wrap only the specific statement that "
                        "may raise in the try block.",
                    )
                )

    logger.debug("Complexity check found %d issues in %s", len(issues), filepath)
    return issues


def _suggest_complexity_reduction(func) -> str:
    """Generate suggestion for reducing function complexity.

    Args:
        func: Function info to analyze.

    Returns:
        Suggestion string.
    """
    suggestions = []

    if func.complexity > 20:
        suggestions.append(
            "This function is very complex. Consider extracting "
            "logical branches into separate helper functions."
        )
    if func.is_async and func.complexity > 10:
        suggestions.append(
            "Async functions should be kept simple. Move complex "
            "logic to synchronous helpers."
        )
    if func.cognitive_complexity > func.complexity * 1.5:
        suggestions.append(
            "Cognitive complexity is disproportionately high. "
            "Use early returns and reduce nesting."
        )

    if not suggestions:
        suggestions.append(
            "Extract conditional branches into separate functions "
            "or use polymorphism to replace conditionals."
        )

    return " ".join(suggestions)
