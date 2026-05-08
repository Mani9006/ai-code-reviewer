"""Code smell detectors for identifying problematic code patterns."""

from __future__ import annotations

import ast
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.ast_parser import ModuleInfo

if TYPE_CHECKING:
    from src.analyzer import Issue
    from src.config import Config

logger = logging.getLogger(__name__)


def detect(module: ModuleInfo, config: Config) -> list["Issue"]:
    """Detect code smells in the module.

    Args:
        module: Parsed module information.
        config: Configuration object.

    Returns:
        List of detected code smell issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    detector_cfg = config.detectors.get("code_smells", {})
    duplicate_threshold = detector_cfg.get("duplicate_threshold", 6)

    # Check for duplicate code blocks
    issues.extend(_detect_duplicate_code(module, duplicate_threshold))

    # Check for long parameter lists
    issues.extend(_detect_long_parameter_lists(module))

    # Check for feature envy (method uses another class more)
    issues.extend(_detect_feature_envy(module))

    # Check for dead code (after return/raise)
    issues.extend(_detect_dead_code(module))

    # Check for comment-ed out code
    issues.extend(_detect_commented_code(module))

    # Check for complex conditionals
    issues.extend(_detect_complex_conditionals(module))

    # Check for God class indicators
    issues.extend(_detect_god_class(module))

    # Check for data class opportunities
    issues.extend(_detect_data_class_opportunity(module))

    logger.debug("Code smell detection found %d issues", len(issues))
    return issues


def _detect_duplicate_code(module: ModuleInfo, threshold: int) -> list:
    """Detect duplicate code blocks.

    Args:
        module: Parsed module information.
        threshold: Minimum line count to consider.

    Returns:
        List of duplicate code issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    code_blocks: dict[str, list[tuple[str, int]]] = {}

    # Extract code blocks from function bodies
    for func in module.functions:
        for i, stmt in enumerate(func.body):
            block_str = ast.dump(stmt)
            block_hash = hashlib.md5(block_str.encode()).hexdigest()
            if block_hash not in code_blocks:
                code_blocks[block_hash] = []
            code_blocks[block_hash].append((func.name, func.lineno))

    for block_hash, locations in code_blocks.items():
        if len(locations) > 1:
            funcs = ", ".join(loc[0] for loc in locations)
            issues.append(
                Issue(
                    rule="duplicate_code",
                    message=f"Duplicate code block found in: {funcs}",
                    severity="warning",
                    filepath=str(module.filepath),
                    lineno=locations[0][1],
                    category="code_smell",
                    suggestion="Extract the duplicated code into a shared "
                    "helper function.",
                )
            )

    return issues


def _detect_long_parameter_lists(module: ModuleInfo) -> list:
    """Detect functions with long parameter lists.

    Args:
        module: Parsed module information.

    Returns:
        List of long parameter list issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    max_params = 5

    for func in module.functions:
        param_count = len(func.args)
        if param_count > max_params:
            issues.append(
                Issue(
                    rule="long_parameter_list",
                    message=f"'{func.name}' has {param_count} parameters "
                    f"(max recommended: {max_params})",
                    severity="warning",
                    filepath=str(module.filepath),
                    lineno=func.lineno,
                    category="code_smell",
                    suggestion="Group related parameters into a dataclass "
                    "or use the Builder pattern.",
                )
            )

    return issues


def _detect_feature_envy(module: ModuleInfo) -> list:
    """Detect methods that may have feature envy.

    Args:
        module: Parsed module information.

    Returns:
        List of feature envy issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Simplified: check methods that call another class frequently
    for cls in module.classes:
        for method in cls.methods:
            external_calls: dict[str, int] = {}
            for node in ast.walk(ast.Module(body=method.body, type_ignores=[])):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            obj_name = node.func.value.id
                            if obj_name != "self" and obj_name != "cls":
                                external_calls[obj_name] = (
                                    external_calls.get(obj_name, 0) + 1
                                )

            for obj, count in external_calls.items():
                if count >= 3:
                    issues.append(
                        Issue(
                            rule="feature_envy",
                            message=f"Method '{method.name}' may have "
                            f"feature envy towards '{obj}' "
                            f"({count} calls)",
                            severity="info",
                            filepath=str(module.filepath),
                            lineno=method.lineno,
                            category="code_smell",
                            suggestion=f"Consider moving operations on "
                            f"'{obj}' into that class.",
                        )
                    )

    return issues


def _detect_dead_code(module: ModuleInfo) -> list:
    """Detect unreachable code after return/raise statements.

    Args:
        module: Parsed module information.

    Returns:
        List of dead code issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            for i, stmt in enumerate(body):
                if isinstance(stmt, (ast.Return, ast.Raise)):
                    # Check if there are statements after this
                    if i + 1 < len(body):
                        next_stmt = body[i + 1]
                        issues.append(
                            Issue(
                                rule="unreachable_code",
                                message="Unreachable code after "
                                f"{stmt.__class__.__name__.lower()}",
                                severity="error",
                                filepath=str(module.filepath),
                                lineno=next_stmt.lineno,
                                category="code_smell",
                                suggestion="Remove the unreachable code "
                                "or fix the control flow.",
                            )
                        )
                        break  # Only report first occurrence

    return issues


def _detect_commented_code(module: ModuleInfo) -> list:
    """Detect commented-out code.

    Args:
        module: Parsed module information.

    Returns:
        List of commented code issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    try:
        source = module.filepath.read_text(encoding="utf-8")
        lines = source.split("\n")
    except OSError:
        return issues

    code_indicators = [
        "def ", "class ", "import ", "from ", "return ",
        "if ", "for ", "while ", "try:", "except",
    ]

    consecutive_comment_lines: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            content = stripped[1:].strip()
            if any(content.startswith(indicator) for indicator in code_indicators):
                consecutive_comment_lines.append((lineno, stripped))
        else:
            if len(consecutive_comment_lines) >= 2:
                first_line = consecutive_comment_lines[0][0]
                issues.append(
                    Issue(
                        rule="commented_code",
                        message=f"Commented-out code detected "
                        f"({len(consecutive_comment_lines)} lines)",
                        severity="info",
                        filepath=str(module.filepath),
                        lineno=first_line,
                        category="code_smell",
                        suggestion="Remove commented-out code or use "
                        "version control to track history.",
                    )
                )
            consecutive_comment_lines = []

    return issues


def _detect_complex_conditionals(module: ModuleInfo) -> list:
    """Detect overly complex conditional expressions.

    Args:
        module: Parsed module information.

    Returns:
        List of complex conditional issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.If):
            # Count boolean operations
            bool_count = _count_bool_ops(node.test)
            if bool_count > 4:
                issues.append(
                    Issue(
                        rule="complex_conditional",
                        message=f"Conditional has {bool_count} boolean "
                        "operations",
                        severity="warning",
                        filepath=str(module.filepath),
                        lineno=node.lineno,
                        category="code_smell",
                        suggestion="Extract complex conditions into "
                        "well-named helper variables or functions.",
                    )
                )

    return issues


def _detect_god_class(module: ModuleInfo) -> list:
    """Detect God Class indicators.

    Args:
        module: Parsed module information.

    Returns:
        List of God Class issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    max_methods = 10
    max_attributes = 10

    for cls in module.classes:
        method_count = len(cls.methods)

        # Count attributes (rough estimate from assignments to self)
        attr_count = 0
        for method in cls.methods:
            for node in ast.walk(ast.Module(body=method.body, type_ignores=[])):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute):
                            if isinstance(target.value, ast.Name):
                                if target.value.id == "self":
                                    attr_count += 1

        if method_count > max_methods and attr_count > max_attributes:
            issues.append(
                Issue(
                    rule="god_class",
                    message=f"Class '{cls.name}' has {method_count} "
                    f"methods and ~{attr_count} attributes - "
                    "possible God Class",
                    severity="warning",
                    filepath=str(module.filepath),
                    lineno=cls.lineno,
                    category="code_smell",
                    suggestion="Split the class using the Single "
                    "Responsibility Principle. Extract "
                    "cohesive groups of methods into separate "
                    "classes.",
                )
            )

    return issues


def _detect_data_class_opportunity(module: ModuleInfo) -> list:
    """Detect classes that could be replaced with @dataclass.

    Args:
        module: Parsed module information.

    Returns:
        List of dataclass opportunity issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for cls in module.classes:
        # Check if class is mainly __init__ with assignments
        if len(cls.methods) == 1 and cls.methods[0].name == "__init__":
            init_method = cls.methods[0]
            body = init_method.body

            # Check if all body statements are self.attr = param assignments
            is_simple_init = True
            for stmt in body:
                if isinstance(stmt, ast.Assign):
                    if not (
                        len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Attribute)
                        and isinstance(stmt.targets[0].value, ast.Name)
                        and stmt.targets[0].value.id == "self"
                    ):
                        is_simple_init = False
                        break

            if is_simple_init and len(body) >= 3:
                issues.append(
                    Issue(
                        rule="use_dataclass",
                        message=f"Class '{cls.name}' could be a "
                        "@dataclass",
                        severity="info",
                        filepath=str(module.filepath),
                        lineno=cls.lineno,
                        category="code_smell",
                        suggestion="Use @dataclass decorator to "
                        "automatically generate __init__, __repr__, "
                        "and other methods.",
                    )
                )

    return issues


def _count_bool_ops(node: ast.expr) -> int:
    """Count boolean operations in an expression.

    Args:
        node: AST expression node.

    Returns:
        Count of boolean operations.
    """
    count = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.BoolOp, ast.Compare)):
            count += 1
    return count


def _get_call_target(node: ast.expr) -> str:
    """Get string representation of call target.

    Args:
        node: AST expression node.

    Returns:
        String representation.
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""
