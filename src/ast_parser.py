"""AST-based code parsing and analysis utilities for CodeReview AI."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    """Information about a function or method extracted from AST."""

    name: str
    lineno: int
    col_offset: int
    end_lineno: Optional[int] = None
    args: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    body: list[ast.stmt] = field(default_factory=list)
    complexity: int = 0
    cognitive_complexity: int = 0
    returns: bool = False
    is_method: bool = False
    is_async: bool = False
    is_generator: bool = False
    nesting_depth: int = 0


@dataclass
class ClassInfo:
    """Information about a class extracted from AST."""

    name: str
    lineno: int
    col_offset: int
    end_lineno: Optional[int] = None
    methods: list[FunctionInfo] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    body: list[ast.stmt] = field(default_factory=list)


@dataclass
class ImportInfo:
    """Information about an import statement."""

    module: Optional[str]
    names: list[str]
    lineno: int
    is_from_import: bool = False
    is_unused: bool = True
    level: int = 0


@dataclass
class ModuleInfo:
    """Comprehensive information about a Python module."""

    filepath: Path
    tree: ast.AST
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    docstring: Optional[str] = None
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    global_variables: list[str] = field(default_factory=list)


class ASTParser:
    """Parser that extracts comprehensive AST-based code metrics."""

    def __init__(self) -> None:
        """Initialize the AST parser."""
        self._cache: dict[Path, ModuleInfo] = {}

    def parse_file(self, filepath: str | Path) -> ModuleInfo:
        """Parse a Python source file and extract all information.

        Args:
            filepath: Path to the Python file.

        Returns:
            ModuleInfo with complete file analysis.

        Raises:
            FileNotFoundError: If file does not exist.
            SyntaxError: If file contains invalid Python syntax.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Source file not found: {filepath}")

        if filepath in self._cache:
            return self._cache[filepath]

        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
        line_stats = self._analyze_line_stats(source)

        module = ModuleInfo(
            filepath=filepath,
            tree=tree,
            total_lines=line_stats["total"],
            code_lines=line_stats["code"],
            comment_lines=line_stats["comment"],
            blank_lines=line_stats["blank"],
        )

        module.docstring = ast.get_docstring(tree)
        module.functions = self._extract_functions(tree)
        module.classes = self._extract_classes(tree)
        module.imports = self._extract_imports(tree)
        module.global_variables = self._extract_global_variables(tree)

        # Mark used imports
        self._mark_used_imports(tree, module.imports)

        # Calculate complexity for all functions
        for func in module.functions:
            func.complexity = self._calculate_cyclomatic_complexity(func.body)
            func.cognitive_complexity = self._calculate_cognitive_complexity(
                func.body
            )
            func.is_generator = self._is_generator(func.body)

        for cls in module.classes:
            for method in cls.methods:
                method.complexity = self._calculate_cyclomatic_complexity(method.body)
                method.cognitive_complexity = self._calculate_cognitive_complexity(
                    method.body
                )
                method.is_generator = self._is_generator(method.body)

        self._cache[filepath] = module
        return module

    def parse_source(self, source: str, filename: str = "<string>") -> ModuleInfo:
        """Parse Python source code from a string.

        Args:
            source: Python source code.
            filename: Virtual filename for error reporting.

        Returns:
            ModuleInfo with complete analysis.

        Raises:
            SyntaxError: If source contains invalid Python syntax.
        """
        tree = ast.parse(source, filename=filename)
        line_stats = self._analyze_line_stats(source)

        module = ModuleInfo(
            filepath=Path(filename),
            tree=tree,
            total_lines=line_stats["total"],
            code_lines=line_stats["code"],
            comment_lines=line_stats["comment"],
            blank_lines=line_stats["blank"],
        )

        module.docstring = ast.get_docstring(tree)
        module.functions = self._extract_functions(tree)
        module.classes = self._extract_classes(tree)
        module.imports = self._extract_imports(tree)
        module.global_variables = self._extract_global_variables(tree)

        self._mark_used_imports(tree, module.imports)

        for func in module.functions:
            func.complexity = self._calculate_cyclomatic_complexity(func.body)
            func.cognitive_complexity = self._calculate_cognitive_complexity(func.body)
            func.is_generator = self._is_generator(func.body)

        return module

    def _analyze_line_stats(self, source: str) -> dict[str, int]:
        """Analyze line statistics from source code.

        Args:
            source: Raw source code.

        Returns:
            Dictionary with total, code, comment, and blank line counts.
        """
        lines = source.split("\n")
        stats = {"total": len(lines), "code": 0, "comment": 0, "blank": 0}

        for line in lines:
            stripped = line.strip()
            if not stripped:
                stats["blank"] += 1
            elif stripped.startswith("#"):
                stats["comment"] += 1
            else:
                stats["code"] += 1

        return stats

    def _extract_functions(self, tree: ast.AST) -> list[FunctionInfo]:
        """Extract all function definitions from AST.

        Args:
            tree: AST tree to analyze.

        Returns:
            List of FunctionInfo objects.
        """
        functions: list[FunctionInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_async = isinstance(node, ast.AsyncFunctionDef)
                args = [arg.arg for arg in node.args.args]
                defaults = len(node.args.defaults)

                info = FunctionInfo(
                    name=node.name,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    end_lineno=getattr(node, "end_lineno", None),
                    args=args,
                    decorators=[self._node_to_string(d) for d in node.decorator_list],
                    docstring=ast.get_docstring(node),
                    body=node.body,
                    returns=node.returns is not None,
                    is_async=is_async,
                    nesting_depth=self._calculate_nesting_depth(node),
                )
                functions.append(info)

        return functions

    def _extract_classes(self, tree: ast.AST) -> list[ClassInfo]:
        """Extract all class definitions from AST.

        Args:
            tree: AST tree to analyze.

        Returns:
            List of ClassInfo objects.
        """
        classes: list[ClassInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods: list[FunctionInfo] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        is_async = isinstance(item, ast.AsyncFunctionDef)
                        args = [arg.arg for arg in item.args.args]
                        info = FunctionInfo(
                            name=item.name,
                            lineno=item.lineno,
                            col_offset=item.col_offset,
                            end_lineno=getattr(item, "end_lineno", None),
                            args=args,
                            decorators=[
                                self._node_to_string(d) for d in item.decorator_list
                            ],
                            docstring=ast.get_docstring(item),
                            body=item.body,
                            returns=item.returns is not None,
                            is_method=True,
                            is_async=is_async,
                            nesting_depth=self._calculate_nesting_depth(item),
                        )
                        methods.append(info)

                info = ClassInfo(
                    name=node.name,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    end_lineno=getattr(node, "end_lineno", None),
                    methods=methods,
                    bases=[self._node_to_string(base) for base in node.bases],
                    decorators=[
                        self._node_to_string(d) for d in node.decorator_list
                    ],
                    docstring=ast.get_docstring(node),
                    body=node.body,
                )
                classes.append(info)

        return classes

    def _extract_imports(self, tree: ast.AST) -> list[ImportInfo]:
        """Extract all import statements from AST.

        Args:
            tree: AST tree to analyze.

        Returns:
            List of ImportInfo objects.
        """
        imports: list[ImportInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            names=[alias.asname or alias.name],
                            lineno=node.lineno,
                            is_from_import=False,
                            level=0,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                imports.append(
                    ImportInfo(
                        module=node.module,
                        names=[alias.name for alias in node.names],
                        lineno=node.lineno,
                        is_from_import=True,
                        level=node.level,
                    )
                )

        return imports

    def _mark_used_imports(
        self, tree: ast.AST, imports: list[ImportInfo]
    ) -> None:
        """Mark imports that are actually used in the code.

        Args:
            tree: AST tree to analyze.
            imports: List of imports to update.
        """
        used_names: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)

        for imp in imports:
            for name in imp.names:
                if name in used_names or name == "*":
                    imp.is_unused = False
                    break

    def _extract_global_variables(self, tree: ast.AST) -> list[str]:
        """Extract global variable assignments from module level.

        Args:
            tree: AST tree to analyze.

        Returns:
            List of global variable names.
        """
        variables: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                variables.append(node.target.id)

        return variables

    def _calculate_cyclomatic_complexity(self, body: list[ast.stmt]) -> int:
        """Calculate cyclomatic complexity of a code block.

        Args:
            body: List of AST statements.

        Returns:
            Cyclomatic complexity score.
        """
        complexity = 1

        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                    ast.comprehension,
                    ast.Try,
                ),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.IfExp):
                complexity += 1
            elif isinstance(node, ast.Match):
                complexity += len(node.cases)

        return complexity

    def _calculate_cognitive_complexity(self, body: list[ast.stmt]) -> int:
        """Calculate cognitive complexity of a code block.

        Args:
            body: List of AST statements.

        Returns:
            Cognitive complexity score.
        """
        complexity = 0
        tree = ast.Module(body=body, type_ignores=[])

        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.Assert,
                    ast.Try,
                    ast.With,
                ),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += 1

        return complexity

    def _calculate_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth of a node.

        Args:
            node: AST node to analyze.

        Returns:
            Maximum nesting depth.
        """
        depth = 0
        current = node
        while hasattr(current, "parent"):
            depth += 1
            current = getattr(current, "parent", None)
        return depth

    def _is_generator(self, body: list[ast.stmt]) -> bool:
        """Check if function body contains yield statements.

        Args:
            body: List of AST statements.

        Returns:
            True if function is a generator.
        """
        tree = ast.Module(body=body, type_ignores=[])
        for node in ast.walk(tree):
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _node_to_string(self, node: ast.AST) -> str:
        """Convert an AST node to its string representation.

        Args:
            node: AST node to convert.

        Returns:
            String representation of the node.
        """
        try:
            return ast.unparse(node)
        except AttributeError:
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                return f"{self._node_to_string(node.value)}.{node.attr}"
            elif isinstance(node, ast.Call):
                return f"{self._node_to_string(node.func)}()"
            elif isinstance(node, ast.Constant):
                return repr(node.value)
            return "<unknown>"

    def clear_cache(self) -> None:
        """Clear the parse cache."""
        self._cache.clear()


class ASTVisitor(ast.NodeVisitor):
    """Custom AST visitor for collecting specific node types."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.nodes: dict[str, list[ast.AST]] = {
            "calls": [],
            "assignments": [],
            "comparisons": [],
            "loops": [],
            "conditionals": [],
            "exceptions": [],
            "returns": [],
            "expressions": [],
        }

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Visit function call nodes."""
        self.nodes["calls"].append(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        """Visit assignment nodes."""
        self.nodes["assignments"].append(node)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        """Visit comparison nodes."""
        self.nodes["comparisons"].append(node)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        """Visit for loop nodes."""
        self.nodes["loops"].append(node)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        """Visit while loop nodes."""
        self.nodes["loops"].append(node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        """Visit if statement nodes."""
        self.nodes["conditionals"].append(node)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:  # noqa: N802
        """Visit try statement nodes."""
        self.nodes["exceptions"].append(node)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
        """Visit return statement nodes."""
        self.nodes["returns"].append(node)
        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:  # noqa: N802
        """Visit expression statement nodes."""
        self.nodes["expressions"].append(node)
        self.generic_visit(node)


def get_source_segment(filepath: str | Path, node: ast.AST) -> Optional[str]:
    """Extract source code segment for an AST node.

    Args:
        filepath: Path to source file.
        node: AST node to extract.

    Returns:
        Source code segment or None if not available.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return None

    source = filepath.read_text(encoding="utf-8")
    try:
        return ast.get_source_segment(source, node)
    except (ValueError, TypeError):
        return None


def parse_expression(expression: str) -> Optional[ast.expr]:
    """Parse a Python expression string into AST.

    Args:
        expression: Expression string to parse.

    Returns:
        AST expression node or None if parsing fails.
    """
    try:
        tree = ast.parse(expression, mode="eval")
        return tree.body
    except SyntaxError:
        return None
