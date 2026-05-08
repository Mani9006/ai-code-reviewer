"""Advanced security risk detectors."""

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
    """Detect advanced security risks.

    Args:
        module: Parsed module information.
        config: Configuration object.

    Returns:
        List of detected security risk issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    # Check for unsafe deserialization
    issues.extend(_detect_unsafe_deserialization(module))

    # Check for command injection risks
    issues.extend(_detect_command_injection(module))

    # Check for path traversal
    issues.extend(_detect_path_traversal(module))

    # Check for SSRF indicators
    issues.extend(_detect_ssrf_risks(module))

    # Check for timing attack vulnerabilities
    issues.extend(_detect_timing_attacks(module))

    # Check for insecure random usage
    issues.extend(_detect_insecure_random(module))

    # Check for unsafe tempfile usage
    issues.extend(_detect_unsafe_tempfile(module))

    # Check for debug mode left enabled
    issues.extend(_detect_debug_mode(module))

    logger.debug("Security risk detection found %d issues", len(issues))
    return issues


def _detect_unsafe_deserialization(module: ModuleInfo) -> list:
    """Detect unsafe deserialization patterns.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in ("pickle.loads", "pickle.load", "yaml.load"):
                issues.append(
                    Issue(
                        rule="unsafe_deserialization",
                        message=f"Unsafe deserialization: {func_name} "
                        "can execute arbitrary code",
                        severity="critical",
                        filepath=str(module.filepath),
                        lineno=node.lineno,
                        category="security_risk",
                        suggestion="Use yaml.safe_load() instead of "
                        "yaml.load(), or json for safe "
                        "deserialization.",
                    )
                )

    return issues


def _detect_command_injection(module: ModuleInfo) -> list:
    """Detect potential command injection vulnerabilities.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    dangerous_funcs = ["os.system", "os.popen", "subprocess.call",
                       "subprocess.run", "subprocess.Popen"]

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in dangerous_funcs:
                # Check if shell=True is used
                shell_true = False
                string_concat = False

                for keyword in node.keywords:
                    if keyword.arg == "shell":
                        if isinstance(keyword.value, ast.Constant):
                            shell_true = keyword.value.value is True

                # Check if first argument involves string formatting
                if node.args:
                    arg = node.args[0]
                    if isinstance(arg, (ast.BinOp, ast.JoinedStr)):
                        string_concat = True

                if shell_true or string_concat:
                    issues.append(
                        Issue(
                            rule="command_injection",
                            message=f"Potential command injection in "
                            f"{func_name}",
                            severity="critical"
                            if shell_true
                            else "warning",
                            filepath=str(module.filepath),
                            lineno=node.lineno,
                            category="security_risk",
                            suggestion="Use a list of arguments instead "
                            "of shell=True. Never pass user "
                            "input directly to shell commands.",
                        )
                    )

    return issues


def _detect_path_traversal(module: ModuleInfo) -> list:
    """Detect potential path traversal vulnerabilities.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    file_funcs = ["open", "os.path.join", "os.makedirs",
                  "shutil.copy", "shutil.move"]

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in file_funcs:
                if node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.BinOp):
                        issues.append(
                            Issue(
                                rule="path_traversal",
                                message=f"Potential path traversal in "
                                f"{func_name} with string "
                                "concatenation",
                                severity="warning",
                                filepath=str(module.filepath),
                                lineno=node.lineno,
                                category="security_risk",
                                suggestion="Use pathlib.Path for safe "
                                "path construction and validate "
                                "the resolved path.",
                            )
                        )

    return issues


def _detect_ssrf_risks(module: ModuleInfo) -> list:
    """Detect potential SSRF (Server-Side Request Forgery) risks.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in ("urllib.request.urlopen", "requests.get",
                             "requests.post", "requests.request"):
                # Check if URL is user-controlled
                if node.args and isinstance(node.args[0], ast.Name):
                    issues.append(
                        Issue(
                            rule="ssrf_risk",
                            message=f"Potential SSRF risk: user input "
                            f"passed to {func_name}",
                            severity="warning",
                            filepath=str(module.filepath),
                            lineno=node.lineno,
                            category="security_risk",
                            suggestion="Validate and sanitize URLs. Use "
                            "an allowlist of allowed domains.",
                        )
                    )

    return issues


def _detect_timing_attacks(module: ModuleInfo) -> list:
    """Detect potential timing attack vulnerabilities.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Compare):
            if isinstance(node.ops[0], ast.Eq):
                # Check for == comparison with password/token
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Name):
                        if any(
                            keyword in comparator.id.lower()
                            for keyword in ["password", "token", "secret",
                                            "api_key", "auth"]
                        ):
                            issues.append(
                                Issue(
                                    rule="timing_attack",
                                    message=f"String comparison of "
                                    f"'{comparator.id}' may be "
                                    "vulnerable to timing attacks",
                                    severity="warning",
                                    filepath=str(module.filepath),
                                    lineno=node.lineno,
                                    category="security_risk",
                                    suggestion="Use hmac.compare_digest() "
                                    "for constant-time comparison of "
                                    "secrets.",
                                )
                            )

    return issues


def _detect_insecure_random(module: ModuleInfo) -> list:
    """Detect usage of insecure random number generators.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in ("random.random", "random.randint",
                             "random.choice", "random.shuffle"):
                issues.append(
                    Issue(
                        rule="insecure_random",
                        message=f"Insecure random: {func_name} is not "
                        "cryptographically secure",
                        severity="warning",
                        filepath=str(module.filepath),
                        lineno=node.lineno,
                        category="security_risk",
                        suggestion="Use secrets module "
                        "(secrets.token_hex, secrets.choice) for "
                        "cryptographic operations.",
                    )
                )

    return issues


def _detect_unsafe_tempfile(module: ModuleInfo) -> list:
    """Detect unsafe temporary file creation.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in ("tempfile.mktemp",):
                issues.append(
                    Issue(
                        rule="unsafe_tempfile",
                        message=f"Unsafe temp file: {func_name} creates "
                        "race condition vulnerability",
                        severity="warning",
                        filepath=str(module.filepath),
                        lineno=node.lineno,
                        category="security_risk",
                        suggestion="Use tempfile.mkstemp() or "
                        "tempfile.NamedTemporaryFile() which "
                        "open the file atomically.",
                    )
                )

    return issues


def _detect_debug_mode(module: ModuleInfo) -> list:
    """Detect debug mode left enabled.

    Args:
        module: Parsed module information.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id.lower() in ("debug", "is_debug"):
                        if isinstance(node.value, ast.Constant):
                            if node.value.value is True:
                                issues.append(
                                    Issue(
                                        rule="debug_mode_enabled",
                                        message="Debug mode is enabled "
                                        "(True)",
                                        severity="error",
                                        filepath=str(module.filepath),
                                        lineno=node.lineno,
                                        category="security_risk",
                                        suggestion="Debug mode should be "
                                        "controlled by environment "
                                        "variables, not hardcoded.",
                                    )
                                )

    return issues


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
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""
