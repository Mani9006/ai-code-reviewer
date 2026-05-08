"""Performance-related code review rules."""

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
    """Check performance-related rules.

    Args:
        module: Parsed module information.
        config: Configuration object.
        filepath: Path to the file being analyzed.

    Returns:
        List of Issue objects for performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Check for list concatenation in loops
    issues.extend(_check_list_concat_in_loops(module, filepath))

    # Check for inefficient string concatenation
    issues.extend(_check_string_concat(module, filepath))

    # Check for repeated attribute access
    issues.extend(_check_repeated_attribute_access(module, filepath))

    # Check for list/dict comprehensions that could be used
    issues.extend(_check_missing_comprehensions(module, filepath))

    # Check for inefficient membership tests
    issues.extend(_check_membership_tests(module, filepath))

    # Check for unnecessary list() calls
    issues.extend(_check_unnecessary_list_calls(module, filepath))

    # Check for global variable usage in functions
    issues.extend(_check_global_usage(module, filepath))

    # Check for recursive functions without memoization
    issues.extend(_check_recursive_without_memoization(module, filepath))

    logger.debug("Performance check found %d issues in %s", len(issues), filepath)
    return issues


def _check_list_concat_in_loops(module: ModuleInfo, filepath: Path) -> list:
    """Check for list concatenation inside loops.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, (ast.For, ast.While)):
            for child in ast.walk(node):
                if isinstance(child, ast.AugAssign) and isinstance(
                    child.op, ast.Add
                ):
                    if isinstance(child.target, ast.Name):
                        issues.append(
                            Issue(
                                rule="list_concat_in_loop",
                                message="List concatenation in loop - "
                                "use list.append() or "
                                "list.extend() instead",
                                severity="warning",
                                filepath=str(filepath),
                                lineno=child.lineno,
                                category="performance",
                                suggestion="Replace 'result += item' with "
                                "'result.append(item)' for O(1) "
                                "amortized time per operation.",
                            )
                        )

    return issues


def _check_string_concat(module: ModuleInfo, filepath: Path) -> list:
    """Check for inefficient string concatenation in loops.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, (ast.For, ast.While)):
            for child in ast.walk(node):
                if isinstance(child, ast.AugAssign) and isinstance(
                    child.op, ast.Add
                ):
                    if isinstance(child.value, ast.Constant) and isinstance(
                        child.value.value, str
                    ):
                        issues.append(
                            Issue(
                                rule="string_concat_in_loop",
                                message="String concatenation in loop - "
                                "use str.join() instead",
                                severity="warning",
                                filepath=str(filepath),
                                lineno=child.lineno,
                                category="performance",
                                suggestion="Collect strings in a list and "
                                "use ''.join(list) after the loop "
                                "for O(n) total time.",
                            )
                        )

    return issues


def _check_repeated_attribute_access(module: ModuleInfo, filepath: Path) -> list:
    """Check for repeated attribute access that could be cached.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    attribute_accesses: dict[str, dict[int, list[int]]] = {}

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Attribute):
            attr_str = _get_attribute_string(node)
            if attr_str:
                scope_id = _get_scope_id(node)
                if scope_id not in attribute_accesses:
                    attribute_accesses[scope_id] = {}
                if attr_str not in attribute_accesses[scope_id]:
                    attribute_accesses[scope_id][attr_str] = []
                attribute_accesses[scope_id][attr_str].append(node.lineno)

    for scope_attrs in attribute_accesses.values():
        for attr, lines in scope_attrs.items():
            if len(lines) >= 3:
                issues.append(
                    Issue(
                        rule="repeated_attribute_access",
                        message=f"Attribute '{attr}' accessed "
                        f"{len(lines)} times - consider caching",
                        severity="info",
                        filepath=str(filepath),
                        lineno=lines[0],
                        category="performance",
                        suggestion=f"Store '{attr}' in a local variable "
                        f"to avoid repeated attribute lookups.",
                    )
                )

    return issues


def _check_missing_comprehensions(module: ModuleInfo, filepath: Path) -> list:
    """Check for opportunities to use list/dict/set comprehensions.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.For):
            # Simple for loop with append pattern
            parent = getattr(node, "parent", None)
            if _is_simple_append_loop(node):
                issues.append(
                    Issue(
                        rule="use_list_comprehension",
                        message="For loop can be converted to a list "
                        "comprehension",
                        severity="info",
                        filepath=str(filepath),
                        lineno=node.lineno,
                        category="performance",
                        suggestion="Convert to list comprehension for "
                        "better performance and readability.",
                    )
                )

    return issues


def _check_membership_tests(module: ModuleInfo, filepath: Path) -> list:
    """Check for inefficient membership tests (list vs set).

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Compare):
            if any(isinstance(op, ast.In) for op in node.ops):
                # Check if the right side is a list
                if isinstance(node.comparators[0], ast.List):
                    if len(node.comparators[0].elts) > 5:
                        issues.append(
                            Issue(
                                rule="slow_membership_test",
                                message="Membership test on list with "
                                ">5 elements - use a set",
                                severity="info",
                                filepath=str(filepath),
                                lineno=node.lineno,
                                category="performance",
                                suggestion="Convert the list to a set for "
                                "O(1) membership testing: "
                                "'item in {1, 2, 3}'",
                            )
                        )

    return issues


def _check_unnecessary_list_calls(module: ModuleInfo, filepath: Path) -> list:
    """Check for unnecessary list() calls.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name == "list":
                if node.args and isinstance(node.args[0], ast.Call):
                    arg_name = _get_call_name(node.args[0].func)
                    if arg_name in ("map", "filter"):
                        issues.append(
                            Issue(
                                rule="unnecessary_list_conversion",
                                message="Unnecessary list() conversion "
                                "of map/filter result",
                                severity="info",
                                filepath=str(filepath),
                                lineno=node.lineno,
                                category="performance",
                                suggestion="Iterate over the map/filter "
                                "result directly or use a "
                                "comprehension instead.",
                            )
                        )

    return issues


def _check_global_usage(module: ModuleInfo, filepath: Path) -> list:
    """Check for global variable usage in functions.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.FunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Global):
                    for name in child.names:
                        issues.append(
                            Issue(
                                rule="global_variable_usage",
                                message=f"Global variable '{name}' used in "
                                "function",
                                severity="info",
                                filepath=str(filepath),
                                lineno=child.lineno,
                                category="performance",
                                suggestion=f"Pass '{name}' as a parameter "
                                "instead of using global for "
                                "better testability and "
                                "performance.",
                            )
                        )

    return issues


def _check_recursive_without_memoization(
    module: ModuleInfo, filepath: Path
) -> list:
    """Check for recursive functions without memoization.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of performance issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Find all function definitions
    for node in ast.walk(module.tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            is_recursive = False

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    call_name = _get_call_name(child.func)
                    if call_name == func_name:
                        is_recursive = True
                        break

            if is_recursive:
                has_cache = any(
                    dec.attr == "lru_cache"
                    for dec in node.decorator_list
                    if isinstance(dec, ast.Attribute)
                )
                if not has_cache:
                    issues.append(
                        Issue(
                            rule="recursive_without_memoization",
                            message=f"Recursive function "
                            "'{func_name}' lacks memoization",
                            severity="warning",
                            filepath=str(filepath),
                            lineno=node.lineno,
                            category="performance",
                            suggestion="Add @functools.lru_cache decorator "
                            "to memoize recursive calls and "
                            "avoid redundant computation.",
                        )
                    )

    return issues


def _is_simple_append_loop(node: ast.For) -> bool:
    """Check if a for loop is a simple append pattern.

    Args:
        node: For loop AST node.

    Returns:
        True if loop matches simple append pattern.
    """
    if len(node.body) != 1:
        return False

    stmt = node.body[0]
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
            return True

    return False


def _get_attribute_string(node: ast.Attribute) -> str:
    """Convert attribute access to string.

    Args:
        node: Attribute AST node.

    Returns:
        String representation.
    """
    parts = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts)) if parts else ""


def _get_scope_id(node: ast.AST) -> int:
    """Get a scope identifier for a node.

    Args:
        node: AST node.

    Returns:
        Scope identifier.
    """
    # Simplified - just use the nearest function/class
    current = node
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.ClassDef)):
            return id(current)
        current = getattr(current, "parent", None)
    return 0


def _get_call_name(node: ast.expr) -> str:
    """Extract call name from AST node.

    Args:
        node: AST expression node.

    Returns:
        Function name string.
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _get_attribute_string(node)
    return ""
