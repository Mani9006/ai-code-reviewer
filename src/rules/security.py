"""Security pattern scanning rules for detecting vulnerabilities."""

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

# Security patterns
DANGEROUS_FUNCTIONS = {
    "eval": "eval() executes arbitrary code. Use ast.literal_eval() for safe evaluation.",
    "exec": "exec() executes arbitrary code. Avoid or use with extreme caution.",
    "compile": "compile() with untrusted input is dangerous. Validate inputs carefully.",
    "__import__": "__import__() can bypass import restrictions. Use importlib instead.",
}

DANGEROUS_MODULES = {
    "pickle": "Pickle can execute arbitrary code during deserialization. Use json or msgpack.",
    "subprocess": "Subprocess calls can be dangerous with untrusted input. Validate all arguments.",
    "os.system": "os.system() is vulnerable to shell injection. Use subprocess.run() with shell=False.",
    "os.popen": "os.popen() is vulnerable to shell injection. Use subprocess with shell=False.",
}

SECRET_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]"), "hardcoded_password"),
    (re.compile(r"(?i)(secret|api_key|apikey)\s*=\s*['\"][^'\"]+['\"]"), "hardcoded_secret"),
    (re.compile(r"(?i)(token|access_token)\s*=\s*['\"][^'\"]+['\"]"), "hardcoded_token"),
    (re.compile(r"(?i)aws_access_key_id\s*=\s*['\"][A-Z0-9]{20}['\"]"), "aws_key_exposure"),
    (re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]"), "aws_secret_exposure"),
    (re.compile(r"['\"]ghp_[A-Za-z0-9]{36}['\"]"), "github_token_exposure"),
    (re.compile(r"['\"]sk-[A-Za-z0-9]{48}['\"]"), "openai_key_exposure"),
    (re.compile(r"['\"]AIza[0-9A-Za-z_-]{35}['\"]"), "google_api_key_exposure"),
]

SQL_PATTERNS = [
    re.compile(r"(?i)(execute|executemany)\s*\(\s*['\"].*%\s*.['\"]"),
    re.compile(r"(?i)(execute|executemany)\s*\(\s*['\"].*\+\s*.*['\"]"),
    re.compile(r"(?i)(execute|executemany)\s*\(\s*f['\"].*\{.*\}.*['\"]"),
    re.compile(r"(?i)SELECT\s+.*\s+FROM\s+.*\+"),
    re.compile(r"(?i)INSERT\s+INTO\s+.*\+"),
    re.compile(r"(?i)UPDATE\s+.*SET\s+.*\+"),
]


def check(module: ModuleInfo, config: Config, filepath: Path) -> list["Issue"]:
    """Check security-related rules.

    Args:
        module: Parsed module information.
        config: Configuration object.
        filepath: Path to the file being analyzed.

    Returns:
        List of Issue objects for security violations.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    rule_cfg = config.rules.get("security", {})
    scan_secrets = rule_cfg.get("scan_secrets", True)

    # Check for dangerous function calls
    issues.extend(_check_dangerous_calls(module, filepath))

    # Check for dangerous imports
    issues.extend(_check_dangerous_imports(module, filepath))

    # Check for hardcoded secrets
    if scan_secrets:
        issues.extend(_check_hardcoded_secrets(filepath))

    # Check for SQL injection patterns
    issues.extend(_check_sql_injection(module, filepath))

    # Check for assert statements
    issues.extend(_check_assert_statements(module, filepath))

    # Check for wildcard imports
    issues.extend(_check_wildcard_imports(module, filepath))

    # Check for hardcoded IPs
    issues.extend(_check_hardcoded_ips(filepath))

    # Check for weak hash algorithms
    issues.extend(_check_weak_hashes(module, filepath))

    logger.debug("Security check found %d issues in %s", len(issues), filepath)
    return issues


def _check_dangerous_calls(module: ModuleInfo, filepath: Path) -> list:
    """Check for dangerous function calls.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in DANGEROUS_FUNCTIONS:
                issues.append(
                    Issue(
                        rule=f"dangerous_{func_name}_call",
                        message=f"Potentially dangerous call to {func_name}()",
                        severity="critical",
                        filepath=str(filepath),
                        lineno=node.lineno,
                        category="security",
                        suggestion=DANGEROUS_FUNCTIONS[func_name],
                    )
                )

    return issues


def _check_dangerous_imports(module: ModuleInfo, filepath: Path) -> list:
    """Check for dangerous imports.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of security issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for imp in module.imports:
        module_name = imp.module or ""
        if module_name in DANGEROUS_MODULES:
            issues.append(
                Issue(
                    rule="dangerous_import",
                    message=f"Import of '{module_name}' detected",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=imp.lineno,
                    category="security",
                    suggestion=DANGEROUS_MODULES[module_name],
                )
            )

    return issues


def _check_hardcoded_secrets(filepath: Path) -> list:
    """Scan for hardcoded secrets and credentials.

    Args:
        filepath: Path to file.

    Returns:
        List of secret exposure issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return issues

    for pattern, rule_name in SECRET_PATTERNS:
        for match in pattern.finditer(source):
            line_num = source[: match.start()].count("\n") + 1
            issues.append(
                Issue(
                    rule=rule_name,
                    message=f"Potential secret/credential hardcoded: "
                    f"{rule_name}",
                    severity="critical",
                    filepath=str(filepath),
                    lineno=line_num,
                    category="security",
                    suggestion="Move secrets to environment variables or "
                    "a secure secrets manager. Use os.environ or "
                    "python-dotenv.",
                )
            )

    return issues


def _check_sql_injection(module: ModuleInfo, filepath: Path) -> list:
    """Check for SQL injection vulnerabilities.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of SQL injection issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    try:
        source = filepath.read_text(encoding="utf-8")
        lines = source.split("\n")
    except (OSError, UnicodeDecodeError):
        return issues

    for lineno, line in enumerate(lines, 1):
        for pattern in SQL_PATTERNS:
            if pattern.search(line):
                issues.append(
                    Issue(
                        rule="sql_injection_risk",
                        message="Potential SQL injection vulnerability: "
                        "string concatenation/formatting in SQL query",
                        severity="critical",
                        filepath=str(filepath),
                        lineno=lineno,
                        category="security",
                        suggestion="Use parameterized queries with "
                        "placeholders (e.g., cursor.execute('SELECT * "
                        "FROM t WHERE id = ?', (user_id,))).",
                    )
                )
                break  # One issue per line is enough

    # Check f-strings in likely SQL contexts
    for node in ast.walk(module.tree):
        if isinstance(node, ast.JoinedStr):
            # Heuristic: check if parent is a call to execute
            issues.append(
                Issue(
                    rule="sql_fstring_risk",
                    message="f-string used in potential SQL context",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=node.lineno,
                    category="security",
                    suggestion="Use parameterized queries instead of "
                    "f-strings for SQL.",
                )
            )

    return issues


def _check_assert_statements(module: ModuleInfo, filepath: Path) -> list:
    """Check for assert statements that may be removed with -O.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of assert-related issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Assert):
            # Only flag asserts that seem to guard against security issues
            if node.msg and isinstance(node.msg, ast.Constant):
                msg = str(node.msg.value).lower()
                if any(
                    word in msg
                    for word in ["auth", "permission", "security", "access", "validate"]
                ):
                    issues.append(
                        Issue(
                            rule="assert_for_security",
                            message="Assert used for security validation "
                            "- asserts are removed with -O flag",
                            severity="error",
                            filepath=str(filepath),
                            lineno=node.lineno,
                            category="security",
                            suggestion="Replace assert with an explicit "
                            "if/raise for security-critical checks.",
                        )
                    )

    return issues


def _check_wildcard_imports(module: ModuleInfo, filepath: Path) -> list:
    """Check for wildcard imports.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of wildcard import issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    for imp in module.imports:
        if "*" in imp.names:
            issues.append(
                Issue(
                    rule="wildcard_import",
                    message=f"Wildcard import from '{imp.module}' detected",
                    severity="warning",
                    filepath=str(filepath),
                    lineno=imp.lineno,
                    category="security",
                    suggestion="Explicitly import only the names you need "
                    "to avoid namespace pollution and potential "
                    "security risks.",
                )
            )

    return issues


def _check_hardcoded_ips(filepath: Path) -> list:
    """Check for hardcoded IP addresses.

    Args:
        filepath: Path to file.

    Returns:
        List of hardcoded IP issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return issues

    ip_pattern = re.compile(
        r"['\"](\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})['\"]"
    )
    for match in ip_pattern.finditer(source):
        ip = match.group(1)
        if ip.startswith("127.") or ip == "0.0.0.0" or ip.startswith("10."):
            continue  # Local IPs are usually fine
        line_num = source[: match.start()].count("\n") + 1
        issues.append(
            Issue(
                rule="hardcoded_ip",
                message=f"Hardcoded IP address: {ip}",
                severity="info",
                filepath=str(filepath),
                lineno=line_num,
                category="security",
                suggestion="Consider using DNS names or configuration "
                "files instead of hardcoded IPs.",
            )
        )

    return issues


def _check_weak_hashes(module: ModuleInfo, filepath: Path) -> list:
    """Check for usage of weak hash algorithms.

    Args:
        module: Parsed module information.
        filepath: Path to file.

    Returns:
        List of weak hash issues.
    """
    from src.analyzer import Issue

    issues: list[Issue] = []
    weak_hashes = {"md5", "sha1"}

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node.func)
            if func_name in weak_hashes or any(
                func_name.endswith(f".{h}") for h in weak_hashes
            ):
                issues.append(
                    Issue(
                        rule="weak_hash_algorithm",
                        message=f"Weak hash algorithm '{func_name}' used",
                        severity="warning",
                        filepath=str(filepath),
                        lineno=node.lineno,
                        category="security",
                        suggestion="Use SHA-256 or stronger hashing "
                        "algorithms for security-sensitive operations.",
                    )
                )

    return issues


def _get_call_name(node: ast.expr) -> str:
    """Extract the full name from a function call node.

    Args:
        node: AST expression node.

    Returns:
        Full function name as string.
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        parts = []
        current: ast.expr = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return "<unknown>"
