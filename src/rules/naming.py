"""Naming convention rule checks for Python identifiers."""

from __future__ import annotations

import keyword
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from src.ast_parser import ModuleInfo

if TYPE_CHECKING:
    from src.analyzer import Issue
    from src.config import Config

logger = logging.getLogger(__name__)

# Naming convention regex patterns
PATTERNS = {
    "snake_case": re.compile(r"^[a-z][a-z0-9_]*$"),
    "camelCase": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    "PascalCase": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
    "UPPER_CASE": re.compile(r"^[A-Z][A-Z0-9_]*$"),
    "private": re.compile(r"^_[a-z][a-z0-9_]*$"),
    "dunder": re.compile(r"^__[a-z][a-z0-9_]*__$"),
}

CONVENTION_MAP = {
    "snake_case": {
        "function": PATTERNS["snake_case"],
        "variable": PATTERNS["snake_case"],
        "module": re.compile(r"^[a-z][a-z0-9_]*$"),
    },
    "camelCase": {
        "function": PATTERNS["camelCase"],
        "variable": PATTERNS["camelCase"],
        "module": re.compile(r"^[a-z][a-z0-9]*$"),
    },
}


def check(module: ModuleInfo, config: Config, filepath: Path) -> list["Issue"]:
    """Check naming convention rules.

    Args:
        module: Parsed module information.
        config: Configuration object.
        filepath: Path to the file being analyzed.

    Returns:
        List of Issue objects for naming violations.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    convention = config.rules.get("naming", {}).get("convention", "snake_case")
    conventions = CONVENTION_MAP.get(convention, CONVENTION_MAP["snake_case"])

    # Check module name
    module_name = filepath.stem
    if not conventions["module"].match(module_name) and not _is_dunder_name(
        module_name
    ):
        issues.append(
            Issue(
                rule="invalid_module_name",
                message=f"Module name '{module_name}' does not follow "
                f"{convention} convention",
                severity="warning",
                filepath=str(filepath),
                lineno=1,
                category="naming",
                suggestion=f"Rename to '{_to_snake_case(module_name)}.py' "
                f"to follow {convention}.",
            )
        )

    # Check function names
    for func in module.functions:
        if _is_dunder_name(func.name) or _is_single_underscore(func.name):
            continue

        pattern = conventions["function"]
        if not pattern.match(func.name):
            severity = "error" if not func.is_method else "warning"
            issues.append(
                Issue(
                    rule="invalid_function_name",
                    message=f"Function '{func.name}' does not follow "
                    f"{convention} convention",
                    severity=severity,
                    filepath=str(filepath),
                    lineno=func.lineno,
                    col_offset=func.col_offset,
                    category="naming",
                    suggestion=f"Consider renaming to "
                    f"'{_to_convention(func.name, convention)}'",
                )
            )

        # Check for shadowing built-ins
        if _is_builtin_shadow(func.name):
            issues.append(
                Issue(
                    rule="builtin_shadowing",
                    message=f"Function '{func.name}' shadows a built-in "
                    "function",
                    severity="error",
                    filepath=str(filepath),
                    lineno=func.lineno,
                    category="naming",
                    suggestion=f"Rename to avoid confusion with built-in "
                    f"'{func.name}()'. Use a more descriptive name.",
                )
            )

    # Check class names (always PascalCase)
    for cls in module.classes:
        if not PATTERNS["PascalCase"].match(cls.name):
            issues.append(
                Issue(
                    rule="invalid_class_name",
                    message=f"Class '{cls.name}' should use PascalCase",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=cls.lineno,
                    category="naming",
                    suggestion=f"Rename to '{_to_pascal_case(cls.name)}'",
                )
            )

    # Check constant names (UPPER_CASE for module-level)
    for var in module.global_variables:
        if not _is_dunder_name(var) and not PATTERNS["UPPER_CASE"].match(var):
            # Only flag if value looks like a constant
            pass  # Constants detected via AST patterns elsewhere

    # Check for single-character names (except in specific contexts)
    for func in module.functions:
        for arg in func.args:
            if len(arg) == 1 and arg not in ("_", "i", "j", "k", "n", "x", "y", "z"):
                issues.append(
                    Issue(
                        rule="single_char_name",
                        message=f"Parameter '{arg}' in '{func.name}' uses "
                        "a single character name",
                        severity="info",
                        filepath=str(filepath),
                        lineno=func.lineno,
                        category="naming",
                        suggestion="Use descriptive parameter names for "
                        "better readability.",
                    )
                )

    # Check for names that are keywords
    all_names = [f.name for f in module.functions] + [c.name for c in module.classes]
    for name in all_names:
        if keyword.iskeyword(name):
            issues.append(
                Issue(
                    rule="keyword_name",
                    message=f"Name '{name}' is a Python keyword",
                    severity="critical",
                    filepath=str(filepath),
                    lineno=1,
                    category="naming",
                    suggestion=f"Rename '{name}' to avoid syntax conflicts.",
                )
            )

    logger.debug("Naming check found %d issues in %s", len(issues), filepath)
    return issues


def _is_dunder_name(name: str) -> bool:
    """Check if name is a dunder method.

    Args:
        name: Name to check.

    Returns:
        True if name starts and ends with double underscore.
    """
    return name.startswith("__") and name.endswith("__")


def _is_single_underscore(name: str) -> bool:
    """Check if name is a single underscore.

    Args:
        name: Name to check.

    Returns:
        True if name is just '_'
    """
    return name == "_"


def _is_builtin_shadow(name: str) -> bool:
    """Check if name shadows a Python built-in.

    Args:
        name: Name to check.

    Returns:
        True if name is a built-in.
    """
    builtins = {
        "abs", "all", "any", "bin", "bool", "breakpoint", "bytearray",
        "bytes", "callable", "chr", "classmethod", "compile", "complex",
        "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec",
        "filter", "float", "format", "frozenset", "getattr", "globals",
        "hasattr", "hash", "help", "hex", "id", "input", "int",
        "isinstance", "issubclass", "iter", "len", "list", "locals",
        "map", "max", "memoryview", "min", "next", "object", "oct",
        "open", "ord", "pow", "print", "property", "range", "repr",
        "reversed", "round", "set", "setattr", "slice", "sorted",
        "staticmethod", "str", "sum", "super", "tuple", "type", "vars",
        "zip", "__import__", "True", "False", "None",
    }
    return name in builtins


def _to_snake_case(name: str) -> str:
    """Convert a name to snake_case.

    Args:
        name: Name to convert.

    Returns:
        snake_case version of name.
    """
    # Handle camelCase and PascalCase
    result = re.sub(r"([A-Z])", r"_\1", name).lower()
    result = result.lstrip("_")
    result = re.sub(r"[^a-z0-9_]+", "_", result)
    return result or name.lower()


def _to_pascal_case(name: str) -> str:
    """Convert a name to PascalCase.

    Args:
        name: Name to convert.

    Returns:
        PascalCase version of name.
    """
    parts = re.split(r"[_\-]+", name)
    return "".join(p.capitalize() for p in parts if p)


def _to_convention(name: str, convention: str) -> str:
    """Convert a name to the specified convention.

    Args:
        name: Current name.
        convention: Target convention.

    Returns:
        Converted name.
    """
    if convention == "snake_case":
        return _to_snake_case(name)
    if convention == "camelCase":
        snake = _to_snake_case(name)
        parts = snake.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:] if p)
    return name
