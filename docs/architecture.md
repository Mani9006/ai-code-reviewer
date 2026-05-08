# CodeReview AI - Architecture Documentation

## Overview

CodeReview AI is a Python-based automated code review tool that performs static analysis on Python source files. It uses Python's `ast` module for deep code understanding and provides comprehensive quality reports.

## System Architecture

```
                    +---------------------+
                    |     CLI Entry       |
                    |      (cli.py)       |
                    +----------+----------+
                               |
                    +----------v----------+
                    |    CodeAnalyzer     |
                    |    (analyzer.py)    |
                    +----------+----------+
                               |
              +----------------+----------------+
              |                |                |
    +---------v------+ +------v------+ +------v-------+
    |  Rule Modules   | | Detectors   | |  Scoring      |
    |                 | |             | |               |
    | - complexity    | | - code      | | - calculator  |
    | - naming        | |   smells    | | - grading     |
    | - documentation | | - security  | +---------------+
    | - security      | |   risks     |
    | - performance   | | - anti      |
    | - style         | |   patterns  |
    +-----------------+ +-------------+
              |                |
              +----------------+
                      |
           +----------v-----------+
           |    AST Parser        |
           |    (ast_parser.py)   |
           +----------------------+
                      |
           +----------v-----------+
           |    Config Engine     |
           |    (config.py)       |
           +----------------------+
```

## Module Descriptions

### CLI (`cli.py`)
Entry point for the tool. Handles argument parsing, orchestrates analysis, and displays colorful output. Supports commands:
- `analyze` - Analyze files or directories
- `config` - Manage configuration
- `self-analyze` - Analyze the tool itself

### CodeAnalyzer (`analyzer.py`)
Core orchestration module. Manages the analysis pipeline:
1. Parses source files via ASTParser
2. Runs all rule checks
3. Runs all detectors
4. Generates fix suggestions
5. Calculates scores and grades
6. Produces FileReport and ReviewReport objects

### AST Parser (`ast_parser.py`)
Provides comprehensive AST-based code analysis:
- `ModuleInfo` - Complete module metadata
- `FunctionInfo` - Function/method details with complexity
- `ClassInfo` - Class structure and methods
- `ImportInfo` - Import statements with usage tracking
- `ASTVisitor` - Custom AST visitor for specific patterns

### Rules Engine (`rules/`)
Pluggable rule system for code quality checks:

| Rule Module | Purpose |
|-------------|---------|
| `complexity.py` | Cyclomatic/cognitive complexity, nesting depth |
| `naming.py` | PEP 8 naming conventions, built-in shadowing |
| `documentation.py` | Docstring coverage, quality, TODO detection |
| `security.py` | Dangerous functions, secrets, SQL injection |
| `performance.py` | Inefficient patterns, list concat in loops |
| `style.py` | Line length, whitespace, imports, mutable defaults |

### Detectors (`detectors/`)
Deep analysis modules for complex patterns:

| Detector Module | Purpose |
|-----------------|---------|
| `code_smells.py` | Duplication, God classes, feature envy |
| `security_risks.py` | SSRF, timing attacks, unsafe deserialization |
| `anti_patterns.py` | except:pass, type() vs isinstance(), bare raise |

### Scoring (`scoring/`)
Score calculation and grade assignment:
- **ScoreCalculator** - Weighted category scoring with penalty system
- **GradeAssigner** - Letter grade assignment (A+ through F)
- **Grade** - Enum with descriptions and colors

### Reports (`reports/`)
Multi-format report generation:
- **HTMLReporter** - Dark-themed, interactive HTML with CSS animations
- **MarkdownReporter** - GitHub-flavored Markdown with badges
- **JSONReporter** - Machine-readable JSON with full metadata

### Suggestions (`suggestions/`)
AI-powered fix recommendation engine:
- Rule-specific suggestion templates
- Context-aware suggestions from AST analysis
- Code fix examples

### Configuration (`config.py`)
Centralized configuration management:
- JSON/TOML config file support
- Hierarchical config search
- Rule enable/disable toggles
- Severity level customization

## Data Flow

```
Source File(s)
      |
      v
[AST Parser] ----> ModuleInfo (AST + metadata)
      |
      +-----> [Rules] --------> Issues
      |                          (rule, message, severity, suggestion)
      |
      +-----> [Detectors] ----> Issues
      |
      +-----> [Suggestions] --> Enhanced Issues
      |
      v
[Scoring] ---------> Score + Grade
      |
      v
[Reports] ---------> HTML / Markdown / JSON
```

## Issue Lifecycle

1. **Detection**: Rule or detector identifies a pattern
2. **Classification**: Issue is assigned severity (info/warning/error/critical)
3. **Enrichment**: Suggestion engine adds fix recommendations
4. **Scoring**: ScoreCalculator applies weighted penalties
5. **Reporting**: Issue is rendered in the output format

## Severity Levels

| Level | Color | Weight | Example |
|-------|-------|--------|---------|
| Info | Blue | 1 | Line too long, trailing whitespace |
| Warning | Yellow | 3 | High complexity, missing docstring |
| Error | Red | 5 | Built-in shadowing, mutable default |
| Critical | Magenta | 10 | eval() usage, hardcoded secrets |

## Scoring Algorithm

1. Start with base score of 100
2. For each issue, subtract severity-based penalty
3. Apply category weights (security = 2.0x, style = 0.5x)
4. Apply critical issue penalty (-10 points each, max -50)
5. Add documentation coverage bonus (+2 for module docstring)
6. Round to 1 decimal place

## Configuration Hierarchy

1. Command-line arguments (highest priority)
2. `.codereview.json` in current directory
3. `.codereview.toml` in current directory
4. `[tool.codereview]` in `pyproject.toml`
5. `~/.config/codereview/config.json`
6. Default values (lowest priority)

## Testing Strategy

| Test Module | Coverage |
|-------------|----------|
| `test_analyzer.py` | Core analyzer, AST parser, report serialization |
| `test_complexity.py` | Cyclomatic complexity, function length, nesting |
| `test_naming.py` | Naming conventions, built-in shadowing |
| `test_security.py` | Security rules and detectors |
| `test_scoring.py` | Score calculation, grade assignment |
| `test_suggestions.py` | Suggestion engine, fix examples |

## Future Enhancements

1. **Plugin System**: Allow custom rules via entry points
2. **Incremental Analysis**: Cache results for unchanged files
3. **IDE Integration**: VS Code extension
4. **Git Integration**: PR comment generation
5. **ML-based Scoring**: Train on code review datasets
6. **Type Checking**: mypy/pyright integration
7. **License Scanning**: Check dependency licenses
8. **Metrics Dashboard**: Track quality over time
