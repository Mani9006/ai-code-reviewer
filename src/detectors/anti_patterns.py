"""Anti-pattern detectors for common Python mistakes."""

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


def detect(module: ModuleInfo, config: Config) -> list["Issue"]:
    """Detect anti-patterns in the module.

    Args:
        module: Parsed module information.
        config: Configuration object.

    Returns:
        List of detected anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Check for except/pass patterns
    issues.extend(_detect_except_pass(module))

    # Check for using 'type' instead of 'isinstance'
    issues.extend(_detect_type_instead_of_isinstance(module))

    # Check for bare raise in except
    issues.extend(_detect_bare_raise(module))

    # Check for reassigning built-in names
    issues.extend(_detect_builtin_reassignment(module))

    # Check for unnecessary list() in for loops
    issues.extend(_detect_unnecessary_list_conversion(module))

    # Check for not using 'with' for resource management
    issues.extend(_detect_missing_context_manager(module))

    # Check for string comparison using 'is'
    issues.extend(_detect_string_is_comparison(module))

    # Check for not using enumerate
    issues.extend(_detect_missing_enumerate(module))

    # Check for catching BaseException
    issues.extend(_detect_base_exception_catch(module))

    # Check for using .format with user input
    issues.extend(_detect_unsafe_format(module))

    logger.debug("Anti-pattern detection found %d issues", len(issues))
    return issues


def _detect_except_pass(module: ModuleInfo) -> list:
    """Detect bare except: pass patterns.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.ExceptHandler):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                issues.append(
                    Issue(
                        rule="except_pass",
                        message="Bare 'except: pass' silently ignores "
                        "all errors",
                        severity="error",
                        filepath=str(module.filepath),
                        lineno=node.lineno,
                        category="anti_pattern",
                        suggestion="At minimum, log the exception. "
                        "Prefer 'except SpecificException as e: "
                        "logger.error(e)'.",
                    )
                )

    return issues


def _detect_type_instead_of_isinstance(module: ModuleInfo) -> list:
    """Detect using type() instead of isinstance().

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Call):
                if isinstance(node.left.func, ast.Name):
                    if node.left.func.id == "type":
                        issues.append(
                            Issue(
                                rule="type_vs_isinstance",
                                message="Use isinstance() instead of "
                                "type() for type checking",
                                severity="warning",
                                filepath=str(module.filepath),
                                lineno=node.lineno,
                                category="anti_pattern",
                                suggestion="isinstance() supports "
                                "inheritance checking. Use "
                                "'isinstance(obj, Type)' instead.",
                            )
                        )

    return issues


def _detect_bare_raise(module: ModuleInfo) -> list:
    """Detect bare raise without active exception.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Raise):
            if node.exc is None:
                issues.append(
                    Issue(
                        rule="bare_raise",
                        message="Bare 'raise' without exception",
                        severity="info",
                        filepath=str(module.filepath),
                        lineno=node.lineno,
                        category="anti_pattern",
                        suggestion="Explicitly specify the exception to "
                        "raise for clarity.",
                    )
                )

    return issues


def _detect_builtin_reassignment(module: ModuleInfo) -> list:
    """Detect reassignment of built-in names.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    builtins = {
        "list", "dict", "set", "str", "int", "float", "bool",
        "type", "object", "id", "max", "min", "sum", "len",
        "range", "filter", "map", "zip", "input", "open",
        "help", "dir", "vars", "locals", "globals", "eval",
        "exec", "compile", "all", "any", "abs", "round",
    }

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id in builtins:
                        issues.append(
                            Issue(
                                rule="builtin_reassignment",
                                message=f"Built-in '{target.id}' is being "
                                "reassigned",
                                severity="error",
                                filepath=str(module.filepath),
                                lineno=node.lineno,
                                category="anti_pattern",
                                suggestion=f"Use a different variable name. "
                                f"'{target.id}' shadows the built-in.",
                            )
                        )

    return issues


def _detect_unnecessary_list_conversion(module: ModuleInfo) -> list:
    """Detect unnecessary list() conversions.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "list":
                if node.args:
                    arg = node.args[0]
                    if isinstance(arg, (ast.List, ast.Tuple)):
                        issues.append(
                            Issue(
                                rule="unnecessary_list_conversion",
                                message="Unnecessary list() conversion of "
                                "a list/tuple literal",
                                severity="info",
                                filepath=str(module.filepath),
                                lineno=node.lineno,
                                category="anti_pattern",
                                suggestion="Remove the list() call - the "
                                "literal is already a list.",
                            )
                        )

    return issues


def _detect_missing_context_manager(module: ModuleInfo) -> list:
    """Detect file operations without context managers.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                # Check if inside a with statement
                parent = getattr(node, "parent", None)
                in_with = False
                current = node
                while current is not None:
                    if isinstance(current, ast.With):
                        in_with = True
                        break
                    current = getattr(current, "parent", None)

                if not in_with:
                    issues.append(
                        Issue(
                            rule="missing_context_manager",
                            message="File opened without 'with' context "
                            "manager",
                            severity="warning",
                            filepath=str(module.filepath),
                            lineno=node.lineno,
                            category="anti_pattern",
                            suggestion="Use 'with open(...) as f:' to "
                            "ensure the file is properly closed.",
                        )
                    )

    return issues


def _detect_string_is_comparison(module: ModuleInfo) -> list:
    """Detect string comparison using 'is' instead of '=='.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Compare):
            if any(isinstance(op, ast.Is) for op in node.ops):
                # Check if comparing string constants
                left = node.left
                comparators = node.comparators

                if isinstance(left, ast.Constant) and isinstance(
                    left.value, str
                ):
                    issues.append(
                        Issue(
                            rule="string_is_comparison",
                            message="String comparison uses 'is' instead "
                            "of '=='",
                            severity="error",
                            filepath=str(module.filepath),
                            lineno=node.lineno,
                            category="anti_pattern",
                            suggestion="Use '==' for value comparison. "
                            "'is' checks identity, which may "
                            "fail with string interning.",
                        )
                    )

                for comp in comparators:
                    if isinstance(comp, ast.Constant) and isinstance(
                        comp.value, str
                    ):
                        issues.append(
                            Issue(
                                rule="string_is_comparison",
                                message="String comparison uses 'is' "
                                "instead of '=='",
                                severity="error",
                                filepath=str(module.filepath),
                                lineno=node.lineno,
                                category="anti_pattern",
                                suggestion="Use '==' for value comparison.",
                            )
                        )

    return issues


def _detect_missing_enumerate(module: ModuleInfo) -> list:
    """Detect loops using manual counter instead of enumerate().

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.For):
            # Check for pattern: i = 0; for x in items: ... i += 1
            body = node.body
            for stmt in body:
                if isinstance(stmt, ast.AugAssign):
                    if isinstance(stmt.target, ast.Name):
                        if stmt.target.id in ("i", "idx", "index", "count"):
                            if isinstance(stmt.op, ast.Add):
                                issues.append(
                                    Issue(
                                        rule="use_enumerate",
                                        message=f"Manual counter "
                                        f"'{stmt.target.id}' "
                                        f"detected - use enumerate()",
                                        severity="info",
                                        filepath=str(module.filepath),
                                        lineno=stmt.lineno,
                                        category="anti_pattern",
                                        suggestion="Use enumerate() for "
                                        "cleaner iteration with "
                                        "indices: 'for i, x in "
                                        "enumerate(items):'.",
                                    )
                                )

    return issues


def _detect_base_exception_catch(module: ModuleInfo) -> list:
    """Detect catching BaseException instead of Exception.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is not None:
                type_name = _get_exception_name(node.type)
                if type_name == "BaseException":
                    issues.append(
                        Issue(
                            rule="catch_base_exception",
                            message="Catching BaseException catches "
                            "SystemExit and KeyboardInterrupt",
                            severity="warning",
                            filepath=str(module.filepath),
                            lineno=node.lineno,
                            category="anti_pattern",
                            suggestion="Use 'except Exception:' unless you "
                            "specifically need to catch system "
                            "exceptions.",
                        )
                    )

    return issues


def _detect_unsafe_format(module: ModuleInfo) -> list:
    """Detect potentially unsafe string formatting.

    Args:
        module: Parsed module information.

    Returns:
        List of anti-pattern issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "format":
                    # Check if format string comes from user input
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ("query", "sql", "cmd"):
                            issues.append(
                                Issue(
                                    rule="unsafe_string_format",
                                    message="String .format() used on "
                                    "potentially unsafe string",
                                    severity="warning",
                                    filepath=str(module.filepath),
                                    lineno=node.lineno,
                                    category="anti_pattern",
                                    suggestion="Use parameterized queries "
                                    "or f-strings with validated "
                                    "input.",
                                )
                            )

    return issues


def _get_exception_name(node: ast.expr) -> str:
    """Get the name of an exception type.

    Args:
        node: AST expression node.

    Returns:
        Exception name string.
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Tuple):
        return "Tuple"
    return ""
