"""Configuration management for CodeReview AI."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


DEFAULT_CONFIG: dict[str, Any] = {
    "max_line_length": 88,
    "max_function_length": 50,
    "max_cyclomatic_complexity": 10,
    "max_cognitive_complexity": 15,
    "max_function_parameters": 5,
    "max_class_methods": 20,
    "max_file_lines": 500,
    "max_nesting_depth": 4,
    "min_docstring_coverage": 80.0,
    "severity_levels": {
        "info": {"color": "blue", "weight": 1},
        "warning": {"color": "yellow", "weight": 3},
        "error": {"color": "red", "weight": 5},
        "critical": {"color": "magenta", "weight": 10},
    },
    "rules": {
        "complexity": {"enabled": True, "threshold": 10},
        "naming": {"enabled": True, "convention": "snake_case"},
        "documentation": {"enabled": True, "require_docstrings": True},
        "security": {"enabled": True, "scan_secrets": True},
        "performance": {"enabled": True},
        "style": {"enabled": True, "max_line_length": 88},
    },
    "detectors": {
        "code_smells": {"enabled": True, "duplicate_threshold": 6},
        "security_risks": {"enabled": True, "strict_mode": False},
        "anti_patterns": {"enabled": True},
    },
    "ignore_patterns": [
        "__pycache__",
        "*.pyc",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".tox",
        ".pytest_cache",
        "build",
        "dist",
    ],
    "file_extensions": [".py"],
    "exclude_files": [],
    "report_format": "html",
    "output_directory": "./code_review_reports",
    "parallel_workers": 4,
    "cache_enabled": True,
    "cache_directory": ".code_review_cache",
    "ai_suggestions": True,
    "fail_threshold": 70.0,
}


@dataclass
class Config:
    """Application configuration with validation and defaults."""

    max_line_length: int = 88
    max_function_length: int = 50
    max_cyclomatic_complexity: int = 10
    max_cognitive_complexity: int = 15
    max_function_parameters: int = 5
    max_class_methods: int = 20
    max_file_lines: int = 500
    max_nesting_depth: int = 4
    min_docstring_coverage: float = 80.0
    severity_levels: dict[str, dict[str, Any]] = field(
        default_factory=lambda: DEFAULT_CONFIG["severity_levels"].copy()
    )
    rules: dict[str, Any] = field(
        default_factory=lambda: DEFAULT_CONFIG["rules"].copy()
    )
    detectors: dict[str, Any] = field(
        default_factory=lambda: DEFAULT_CONFIG["detectors"].copy()
    )
    ignore_patterns: list[str] = field(
        default_factory=lambda: DEFAULT_CONFIG["ignore_patterns"].copy()
    )
    file_extensions: list[str] = field(
        default_factory=lambda: DEFAULT_CONFIG["file_extensions"].copy()
    )
    exclude_files: list[str] = field(default_factory=list)
    report_format: str = "html"
    output_directory: str = "./code_review_reports"
    parallel_workers: int = 4
    cache_enabled: bool = True
    cache_directory: str = ".code_review_cache"
    ai_suggestions: bool = True
    fail_threshold: float = 70.0

    @classmethod
    def from_file(cls, filepath: str | Path) -> Config:
        """Load configuration from a JSON or TOML file.

        Args:
            filepath: Path to configuration file.

        Returns:
            Config instance with loaded settings.

        Raises:
            FileNotFoundError: If configuration file does not exist.
            ValueError: If configuration file format is invalid.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        try:
            content = filepath.read_text(encoding="utf-8")
            if filepath.suffix == ".json":
                data = json.loads(content)
            elif filepath.suffix in (".toml", ".cfg"):
                try:
                    import tomllib
                    data = tomllib.loads(content)
                except ImportError:
                    try:
                        import tomli
                        data = tomli.loads(content)
                    except ImportError:
                        raise ValueError(
                            "TOML support requires 'tomli' package for Python < 3.11"
                        )
            else:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    raise ValueError(f"Unsupported config file format: {filepath.suffix}")
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid configuration file: {e}") from e

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create configuration from dictionary.

        Args:
            data: Dictionary with configuration values.

        Returns:
            Config instance.
        """
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_file(self, filepath: str | Path) -> None:
        """Save configuration to a JSON file.

        Args:
            filepath: Destination path for configuration file.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            json.dumps(asdict(self), indent=2, default=str), encoding="utf-8"
        )
        logger.info("Configuration saved to %s", filepath)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration.
        """
        return asdict(self)

    def get_rule_config(self, rule_name: str) -> dict[str, Any]:
        """Get configuration for a specific rule.

        Args:
            rule_name: Name of the rule.

        Returns:
            Rule configuration dictionary.
        """
        return self.rules.get(rule_name, {})

    def is_rule_enabled(self, rule_name: str) -> bool:
        """Check if a rule is enabled.

        Args:
            rule_name: Name of the rule.

        Returns:
            True if rule is enabled.
        """
        return self.rules.get(rule_name, {}).get("enabled", True)

    def is_detector_enabled(self, detector_name: str) -> bool:
        """Check if a detector is enabled.

        Args:
            detector_name: Name of the detector.

        Returns:
            True if detector is enabled.
        """
        return self.detectors.get(detector_name, {}).get("enabled", True)

    def should_ignore(self, path: str | Path) -> bool:
        """Check if a path should be ignored based on patterns.

        Args:
            path: File or directory path to check.

        Returns:
            True if path should be ignored.
        """
        path = Path(path)
        for pattern in self.ignore_patterns:
            if pattern in str(path) or path.match(pattern):
                return True
        for pattern in self.exclude_files:
            if pattern in str(path) or path.match(pattern):
                return True
        return False


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or use defaults.

    Args:
        config_path: Optional path to configuration file.

    Returns:
        Configuration instance.
    """
    if config_path:
        return Config.from_file(config_path)

    # Search for config files in common locations
    search_paths = [
        Path(".codereview.json"),
        Path(".codereview.toml"),
        Path("pyproject.toml"),
        Path.home() / ".config" / "codereview" / "config.json",
    ]

    for path in search_paths:
        if path.exists():
            try:
                if path.name == "pyproject.toml":
                    try:
                        import tomllib
                        content = path.read_text(encoding="utf-8")
                        data = tomllib.loads(content)
                        tool_config = data.get("tool", {}).get("codereview", {})
                        if tool_config:
                            return Config.from_dict(tool_config)
                    except (ImportError, KeyError):
                        continue
                else:
                    return Config.from_file(path)
            except (ValueError, FileNotFoundError):
                continue

    return Config()
