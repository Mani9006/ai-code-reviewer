"""AI-powered fix suggestion engine for code review issues."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

from src.ast_parser import ModuleInfo

if TYPE_CHECKING:
    from src.analyzer import Issue
    from src.config import Config

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Generate intelligent fix suggestions for code review issues."""

    # Rule-specific suggestion templates
    SUGGESTION_TEMPLATES: dict[str, list[str]] = {
        "line_too_long": [
            "Break the line after an operator or comma.",
            "Use implicit continuation inside parentheses.",
            "Assign sub-expressions to intermediate variables.",
        ],
        "high_cyclomatic_complexity": [
            "Extract each branch into a separate helper function.",
            "Use early returns to reduce nesting depth.",
            "Replace conditionals with polymorphism using Strategy pattern.",
            "Consider using a lookup dictionary for dispatch.",
        ],
        "missing_function_docstring": [
            "Add a Google-style docstring with Args, Returns, and Raises.",
            "Use '{func_name} does X. Args: ... Returns: ...' format.",
        ],
        "missing_class_docstring": [
            "Add a class docstring describing its purpose and usage.",
            "Include example usage code in the docstring.",
        ],
        "dangerous_eval_call": [
            "Replace eval() with ast.literal_eval() for safe evaluation.",
            "Use json.loads() for parsing JSON data.",
            "Implement a safe expression parser for your use case.",
        ],
        "hardcoded_password": [
            "Move password to environment variable: os.environ.get('PASSWORD')",
            "Use python-dotenv to load from .env file.",
            "Consider using a secrets manager (AWS Secrets Manager, Vault).",
        ],
        "sql_injection_risk": [
            "Use parameterized queries: cursor.execute('SELECT * FROM t WHERE id = %s', (user_id,))",
            "Use an ORM like SQLAlchemy for safe query building.",
            "Validate and sanitize all user inputs before use in queries.",
        ],
        "mutable_default_argument": [
            "Use 'def func(arg=None): if arg is None: arg = []' pattern.",
            "Use a sentinel object for distinguishing None from missing.",
        ],
        "trailing_whitespace": [
            "Configure your editor to trim trailing whitespace on save.",
            "Run: sed -i 's/[[:space:]]*$//' filename.py",
        ],
        "bare_except": [
            "Use 'except Exception:' to catch standard exceptions.",
            "Catch specific exceptions: 'except ValueError as e:'.",
        ],
        "wildcard_import": [
            "Explicitly import needed names: 'from module import name1, name2'.",
        ],
        "except_pass": [
            "At minimum, log the exception: logging.warning('Error: %s', e)",
            "Re-raise the exception if it cannot be handled properly.",
        ],
        "type_vs_isinstance": [
            "Replace 'type(x) is T' with 'isinstance(x, T)'.",
        ],
        "use_enumerate": [
            "Replace manual counter with: for i, item in enumerate(items):",
        ],
        "recursive_without_memoization": [
            "Add @functools.lru_cache(maxsize=128) decorator.",
            "Implement memoization with a dictionary cache.",
        ],
        "missing_context_manager": [
            "Use 'with open(path) as f:' for automatic resource cleanup.",
        ],
        "string_is_comparison": [
            "Replace 'is' with '==' for string value comparison.",
        ],
        "duplicate_code": [
            "Extract the duplicated code into a shared helper function.",
            "Use a mixin class for shared functionality.",
        ],
        "too_many_arguments": [
            "Group related parameters into a dataclass or config object.",
            "Use **kwargs for optional parameters.",
            "Apply the Builder pattern for complex construction.",
        ],
        "function_too_long": [
            "Extract logical sections into named helper functions.",
            "Each function should do one thing well (Single Responsibility).",
        ],
        "global_variable_usage": [
            "Pass the variable as a function parameter.",
            "Encapsulate state in a class.",
        ],
        "use_dataclass": [
            "Add @dataclass decorator and remove manual __init__.",
            "Use @dataclass(frozen=True) for immutable data classes.",
        ],
        "unused_import": [
            "Remove the unused import statement.",
            "If needed later, re-add when used.",
        ],
        "import_order": [
            "Order: stdlib, third-party, local. Separate groups with blank lines.",
        ],
        "catch_base_exception": [
            "Use 'except Exception:' unless you need to catch system exits.",
        ],
    }

    def __init__(self, config: Config) -> None:
        """Initialize the suggestion engine.

        Args:
            config: Configuration object.
        """
        self.config = config

    def generate_suggestion(
        self, issue: "Issue", module: ModuleInfo
    ) -> Optional[str]:
        """Generate a fix suggestion for an issue.

        Args:
            issue: The code review issue.
            module: Parsed module information.

        Returns:
            Suggestion string or None if no suggestion available.
        """
        # Try rule-specific template first
        templates = self.SUGGESTION_TEMPLATES.get(issue.rule, [])
        if templates:
            return templates[0]

        # Try category-based suggestion
        category_suggestion = self._category_suggestion(issue)
        if category_suggestion:
            return category_suggestion

        # Try to generate from context
        if module is not None:
            context_suggestion = self._context_suggestion(issue, module)
            if context_suggestion:
                return context_suggestion

        return None

    def _category_suggestion(self, issue: "Issue") -> Optional[str]:
        """Generate suggestion based on issue category.

        Args:
            issue: The code review issue.

        Returns:
            Category-based suggestion or None.
        """
        category_suggestions: dict[str, list[str]] = {
            "complexity": [
                "Refactor to reduce complexity. Extract helpers.",
                "Consider using design patterns to simplify logic.",
            ],
            "naming": [
                "Follow PEP 8 naming conventions.",
                "Use descriptive, intention-revealing names.",
            ],
            "documentation": [
                "Add docstrings following Google/NumPy/Sphinx style.",
                "Document parameters, return values, and exceptions.",
            ],
            "security": [
                "Review security best practices for this pattern.",
                "Use established security libraries when available.",
            ],
            "performance": [
                "Profile the code to confirm the bottleneck.",
                "Consider algorithmic improvements.",
            ],
            "style": [
                "Follow PEP 8 style guidelines.",
                "Configure auto-formatters like Black or autopep8.",
            ],
            "code_smell": [
                "Apply the Single Responsibility Principle.",
                "Consider refactoring to improve code clarity.",
            ],
            "anti_pattern": [
                "Use Pythonic idioms for this pattern.",
                "Refer to Python best practices documentation.",
            ],
        }

        suggestions = category_suggestions.get(issue.category, [])
        return suggestions[0] if suggestions else None

    def _context_suggestion(
        self, issue: "Issue", module: ModuleInfo
    ) -> Optional[str]:
        """Generate suggestion based on code context.

        Args:
            issue: The code review issue.
            module: Parsed module information.

        Returns:
            Context-aware suggestion or None.
        """
        # Find the relevant function/class for context
        context = None
        for func in module.functions:
            if func.lineno <= issue.lineno <= (func.end_lineno or func.lineno):
                context = func
                break

        if not context:
            return None

        if "missing" in issue.rule and "docstring" in issue.rule:
            return (
                f"Add a docstring to '{context.name}' describing "
                f"what it does, its {len(context.args)} parameters, "
                f"and what it returns."
            )

        if "complexity" in issue.rule:
            if context.is_async:
                return (
                    f"Simplify async function '{context.name}'. "
                    f"Consider breaking it into smaller coroutines."
                )
            return (
                f"Refactor '{context.name}' into smaller functions. "
                f"Current complexity: {context.complexity}."
            )

        return None

    def generate_fix_example(
        self, issue: "Issue", module: ModuleInfo
    ) -> Optional[str]:
        """Generate a code example showing the fix.

        Args:
            issue: The code review issue.
            module: Parsed module information.

        Returns:
            Code example string or None.
        """
        fix_examples: dict[str, str] = {
            "line_too_long": "# Instead of:\nresult = very_long_function_name(first_argument, second_argument, third_argument)\n\n# Use:\nresult = very_long_function_name(\n    first_argument,\n    second_argument,\n    third_argument,\n)",
            "mutable_default_argument": "# Instead of:\ndef func(items=[]):\n    ...\n\n# Use:\ndef func(items=None):\n    if items is None:\n        items = []",
            "bare_except": "# Instead of:\nexcept:\n    pass\n\n# Use:\nexcept Exception as e:\n    logger.error('Error: %s', e)",
            "use_enumerate": "# Instead of:\ni = 0\nfor item in items:\n    ...\n    i += 1\n\n# Use:\nfor i, item in enumerate(items):\n    ...",
            "string_is_comparison": "# Instead of:\nif s is 'hello':\n\n# Use:\nif s == 'hello':",
            "type_vs_isinstance": "# Instead of:\nif type(x) is dict:\n\n# Use:\nif isinstance(x, dict):",
            "missing_context_manager": "# Instead:\nf = open('file.txt')\ndata = f.read()\nf.close()\n\n# Use:\nwith open('file.txt') as f:\n    data = f.read()",
            "recursive_without_memoization": "# Use:\nfrom functools import lru_cache\n\n@lru_cache(maxsize=128)\ndef fibonacci(n):\n    ...",
        }

        return fix_examples.get(issue.rule)
