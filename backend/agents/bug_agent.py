from __future__ import annotations

import ast
import re
from typing import Any

from backend.models.finding import Finding, FindingSeverity
from backend.models.project import AnalysisContext


def _finding(
    *,
    severity: FindingSeverity,
    confidence: float,
    title: str,
    description: str,
    filename: str,
    line: int,
    evidence: str,
    recommendation: str,
    line_end: int | None = None,
) -> Finding:
    return Finding(
        agent="Bug Agent",
        severity=severity,
        confidence=confidence,
        title=title,
        description=description,
        file=filename,
        line_start=line,
        line_end=line_end or line,
        evidence=evidence[:500],
        recommendation=recommendation,
    )


def _python_ast_findings(
    code: str,
    filename: str,
) -> list[Finding]:
    findings: list[Finding] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        line = exc.lineno or 1
        evidence = (
            code.splitlines()[line - 1]
            if code.splitlines() and line <= len(code.splitlines())
            else str(exc)
        )

        findings.append(
            _finding(
                severity=FindingSeverity.HIGH,
                confidence=0.99,
                title="Python syntax error",
                description=f"The Python parser could not parse this file: {exc.msg}.",
                filename=filename,
                line=line,
                evidence=evidence,
                recommendation="Fix the syntax error before running or testing this code.",
            )
        )
        return findings

    class Visitor(ast.NodeVisitor):
        def visit_Compare(self, node: ast.Compare) -> None:
            for operator in node.ops:
                if isinstance(operator, (ast.Is, ast.IsNot)):
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant) and comparator.value is not None:
                            findings.append(
                                _finding(
                                    severity=FindingSeverity.MEDIUM,
                                    confidence=0.88,
                                    title="Suspicious identity comparison",
                                    description=(
                                        "Python identity operators 'is' and 'is not' are "
                                        "intended for object identity, not ordinary value comparison."
                                    ),
                                    filename=filename,
                                    line=node.lineno,
                                    evidence=ast.unparse(node),
                                    recommendation=(
                                        "Use == or != when comparing ordinary values. "
                                        "Reserve 'is' for singleton checks such as 'is None'."
                                    ),
                                )
                            )

            self.generic_visit(node)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.type is None and not node.body:
                findings.append(
                    _finding(
                        severity=FindingSeverity.MEDIUM,
                        confidence=0.9,
                        title="Empty exception handler",
                        description="An exception handler without useful handling can silently hide runtime failures.",
                        filename=filename,
                        line=node.lineno,
                        evidence="except:",
                        recommendation="Handle the exception explicitly or re-raise it after appropriate logging.",
                    )
                )

            elif node.type is None:
                for statement in node.body:
                    if isinstance(statement, ast.Pass):
                        findings.append(
                            _finding(
                                severity=FindingSeverity.MEDIUM,
                                confidence=0.94,
                                title="Exception is silently ignored",
                                description="A bare exception handler containing only pass can hide unexpected failures.",
                                filename=filename,
                                line=node.lineno,
                                evidence="except: pass",
                                recommendation=(
                                    "Catch the specific exception types you expect and "
                                    "handle or log them instead of silently ignoring failures."
                                ),
                            )
                        )

            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.value, (ast.List, ast.Tuple)):
                if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                    index = node.slice.value
                    length = len(node.value.elts)

                    if index >= length or index < -length:
                        findings.append(
                            _finding(
                                severity=FindingSeverity.HIGH,
                                confidence=0.99,
                                title="Out-of-range collection access",
                                description="The code accesses a list or tuple using an index that is outside its known bounds.",
                                filename=filename,
                                line=node.lineno,
                                evidence=ast.unparse(node),
                                recommendation="Use a valid index or check the collection length before accessing it.",
                            )
                        )

            self.generic_visit(node)

        def visit_BinOp(self, node: ast.BinOp) -> None:
            if isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    findings.append(
                        _finding(
                            severity=FindingSeverity.HIGH,
                            confidence=0.99,
                            title="Division by zero",
                            description="The expression divides a value by the constant zero.",
                            filename=filename,
                            line=node.lineno,
                            evidence=ast.unparse(node),
                            recommendation="Ensure the denominator cannot be zero before performing the division.",
                        )
                    )

            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                if node.func.id == "eval":
                    findings.append(
                        _finding(
                            severity=FindingSeverity.HIGH,
                            confidence=0.94,
                            title="Dynamic evaluation may fail at runtime",
                            description="eval() executes dynamically constructed Python code and can introduce unpredictable runtime behavior.",
                            filename=filename,
                            line=node.lineno,
                            evidence=ast.unparse(node),
                            recommendation="Avoid dynamic evaluation and use explicit parsing or dispatch logic.",
                        )
                    )

            self.generic_visit(node)

        def visit_For(self, node: ast.For) -> None:
            if isinstance(node.iter, ast.Constant) and node.iter.value is None:
                findings.append(
                    _finding(
                        severity=FindingSeverity.HIGH,
                        confidence=0.98,
                        title="Loop iterates over None",
                        description="The loop attempts to iterate over None, which raises TypeError at runtime.",
                        filename=filename,
                        line=node.lineno,
                        evidence=ast.unparse(node),
                        recommendation="Ensure the iterable contains a valid collection before starting the loop.",
                    )
                )

            self.generic_visit(node)

        def visit_While(self, node: ast.While) -> None:
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                has_break = any(
                    isinstance(child, ast.Break)
                    for child in ast.walk(node)
                )

                if not has_break:
                    findings.append(
                        _finding(
                            severity=FindingSeverity.HIGH,
                            confidence=0.94,
                            title="Potential infinite loop",
                            description="A while True loop has no break statement in its body and may never terminate.",
                            filename=filename,
                            line=node.lineno,
                            evidence=ast.unparse(node),
                            recommendation="Add a reachable termination condition or break statement.",
                        )
                    )

            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node.body:
                last = node.body[-1]

                if isinstance(last, ast.Pass):
                    findings.append(
                        _finding(
                            severity=FindingSeverity.MEDIUM,
                            confidence=0.85,
                            title="Function contains an unimplemented body",
                            description="The function ends with pass and may not implement its intended behavior.",
                            filename=filename,
                            line=last.lineno,
                            evidence=ast.unparse(last),
                            recommendation="Implement the function logic or explicitly document why the function is intentionally empty.",
                        )
                    )

            self.generic_visit(node)

    Visitor().visit(tree)

    return findings


def _pattern_findings(
    code: str,
    filename: str,
    language: str,
) -> list[Finding]:
    findings: list[Finding] = []
    lines = code.splitlines()
    normalized_language = (language or "generic").casefold()

    def add(
        line_number: int,
        severity: FindingSeverity,
        confidence: float,
        title: str,
        description: str,
        recommendation: str,
    ) -> None:
        stripped = lines[line_number - 1].strip()

        findings.append(
            _finding(
                severity=severity,
                confidence=confidence,
                title=title,
                description=description,
                filename=filename,
                line=line_number,
                evidence=stripped,
                recommendation=recommendation,
            )
        )

    for line_number, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()

        if not stripped:
            continue

        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        # ---------------------------------------------------------
        # NULL / UNDEFINED COMPARISONS
        # ---------------------------------------------------------

        if re.search(r"==\s*null|!=\s*null", stripped):
            add(
                line_number,
                FindingSeverity.MEDIUM,
                0.88,
                "Unsafe null comparison",
                "The code performs a direct null comparison that may not cover all missing-value cases.",
                "Use the language's recommended null-safe comparison pattern.",
            )
            continue

        if "=== undefined" in stripped or "== undefined" in stripped:
            add(
                line_number,
                FindingSeverity.MEDIUM,
                0.9,
                "Unsafe undefined comparison",
                "The code directly compares a value with undefined.",
                "Prefer an explicit undefined check such as typeof value === 'undefined' where appropriate.",
            )
            continue

        # ---------------------------------------------------------
        # JAVASCRIPT / TYPESCRIPT
        # ---------------------------------------------------------

        if normalized_language in {"javascript", "typescript"}:
            if re.search(r"\bJSON\.parse\s*\(", stripped):
                add(
                    line_number,
                    FindingSeverity.MEDIUM,
                    0.86,
                    "JSON parsing may throw",
                    "JSON.parse() throws when the supplied value is not valid JSON.",
                    "Validate or safely handle malformed JSON before parsing.",
                )

            if re.search(r"\b[a-zA-Z_$][\w$]*\s*\[[^\]]+\]", stripped):
                if ".length" not in stripped and "if (" not in stripped:
                    add(
                        line_number,
                        FindingSeverity.INFO,
                        0.62,
                        "Unchecked collection access",
                        "The code accesses a collection without an obvious bounds or existence check.",
                        "Validate the collection and index before accessing the element.",
                    )

            if re.search(r"\bwhile\s*\(\s*true\s*\)", stripped):
                if "break" not in code:
                    add(
                        line_number,
                        FindingSeverity.HIGH,
                        0.95,
                        "Potential infinite loop",
                        "The while(true) loop has no detected break statement.",
                        "Add a reachable termination condition or break statement.",
                    )

        # ---------------------------------------------------------
        # JAVA / C / C++ / C#
        # ---------------------------------------------------------

        if normalized_language in {
            "java",
            "c",
            "c++",
            "c#",
        }:
            if re.search(r"/\s*0(?:\D|$)", stripped):
                add(
                    line_number,
                    FindingSeverity.HIGH,
                    0.99,
                    "Division by zero",
                    "The expression contains division by a constant zero.",
                    "Ensure the denominator is non-zero before performing the division.",
                )

            if re.search(r"\bwhile\s*\(\s*true\s*\)", stripped):
                if "break" not in code:
                    add(
                        line_number,
                        FindingSeverity.HIGH,
                        0.95,
                        "Potential infinite loop",
                        "The loop has no detected break statement and may never terminate.",
                        "Add a reachable termination condition.",
                    )

        # ---------------------------------------------------------
        # GENERIC BUG PATTERNS
        # ---------------------------------------------------------

        if re.search(r"\bTODO\b|\bFIXME\b", stripped, re.IGNORECASE):
            if re.search(r"\bpass\b|throw\s+new|raise\s+NotImplemented|NotImplementedError", stripped):
                add(
                    line_number,
                    FindingSeverity.MEDIUM,
                    0.9,
                    "Incomplete implementation",
                    "The code contains a TODO/FIXME marker together with an unimplemented operation.",
                    "Implement the missing logic before considering the code complete.",
                )

        if re.search(
            r"\b(?:raise|throw)\s+(?:NotImplementedError|NotImplementedException)",
            stripped,
        ):
            add(
                line_number,
                FindingSeverity.MEDIUM,
                0.98,
                "Unimplemented code path",
                "This statement deliberately raises a not-implemented exception.",
                "Implement the missing behavior or remove the unfinished code path.",
            )

        # Common accidental assignment/comparison patterns.
        if re.search(r"\bif\s*\([^)]*\b\w+\s*=\s*[^=]", stripped):
            add(
                line_number,
                FindingSeverity.HIGH,
                0.88,
                "Possible assignment inside condition",
                "An assignment appears inside a conditional expression and may be an accidental use of '=' instead of a comparison operator.",
                "Verify whether the condition should use ==, ===, or another comparison operator.",
            )

        # Empty catch blocks in common C-style languages.
        if re.search(r"\bcatch\s*\([^)]*\)\s*\{\s*\}", stripped):
            add(
                line_number,
                FindingSeverity.MEDIUM,
                0.96,
                "Empty exception handler",
                "The exception is caught but no handling logic is present.",
                "Handle, log, or deliberately propagate the exception.",
            )

    return findings


def _duplicate_findings(
    code: str,
    filename: str,
) -> list[Finding]:
    findings: list[Finding] = []
    lines = code.splitlines()

    normalized: dict[str, list[int]] = {}

    for number, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("#") or stripped.startswith("//"):
            continue

        compact = re.sub(r"\s+", " ", stripped)

        if len(compact) < 12:
            continue

        normalized.setdefault(compact, []).append(number)

    for text, occurrences in normalized.items():
        if len(occurrences) >= 3:
            first_line = occurrences[0]

            findings.append(
                _finding(
                    severity=FindingSeverity.LOW,
                    confidence=0.82,
                    title="Repeated code statement",
                    description=(
                        f"The same statement appears {len(occurrences)} times. "
                        "Repeated logic can cause maintenance bugs when one copy is changed and another is not."
                    ),
                    filename=filename,
                    line=first_line,
                    evidence=text,
                    recommendation="Consider extracting repeated logic into a function or reusable operation.",
                )
            )

    return findings


def analyze_bugs(
    code: str,
    filename: str = "",
    language: str = "generic",
    context: AnalysisContext | None = None,
) -> list[Finding]:
    """
    Main Bug Agent.

    Performs:
    1. Python AST analysis when the submitted language is Python.
    2. Cross-language pattern detection.
    3. Duplicate/repeated statement detection.
    4. Project-level unresolved import detection.
    """

    findings: list[Finding] = []

    if not code or not code.strip():
        return findings

    normalized_language = (language or "generic").casefold()

    # ---------------------------------------------------------
    # PYTHON STATIC ANALYSIS
    # ---------------------------------------------------------

    if normalized_language == "python":
        findings.extend(
            _python_ast_findings(
                code,
                filename,
            )
        )

    # ---------------------------------------------------------
    # GENERAL LANGUAGE ANALYSIS
    # ---------------------------------------------------------

    findings.extend(
        _pattern_findings(
            code,
            filename,
            language,
        )
    )

    # ---------------------------------------------------------
    # DUPLICATED CODE
    # ---------------------------------------------------------

    findings.extend(
        _duplicate_findings(
            code,
            filename,
        )
    )

    # ---------------------------------------------------------
    # PROJECT RELATIONSHIP ANALYSIS
    # ---------------------------------------------------------

    if context:
        for relationship in context.relationships:
            if (
                relationship.source == filename
                and relationship.resolution_status == "unresolved"
                and relationship.import_name.startswith(".")
            ):
                findings.append(
                    _finding(
                        severity=FindingSeverity.MEDIUM,
                        confidence=0.9,
                        title="Unresolved relative project import",
                        description=(
                            "A relative import does not match any source file "
                            "included in this project review."
                        ),
                        filename=filename,
                        line=1,
                        evidence=relationship.import_name,
                        recommendation=(
                            "Check the import path and ensure the referenced "
                            "module is included in the submitted project."
                        ),
                    )
                )

    # ---------------------------------------------------------
    # REMOVE EXACT DUPLICATES
    # ---------------------------------------------------------

    unique: list[Finding] = []
    seen: set[tuple[Any, ...]] = set()

    for finding in findings:
        key = (
            finding.title,
            finding.file,
            finding.line_start,
            finding.evidence,
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(finding)

    return unique