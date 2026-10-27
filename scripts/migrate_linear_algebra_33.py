#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from import_existing_notes import split_existing_markdown_into_items  # noqa: E402
from mapping_audit import infer_subject_id, project_file_candidates  # noqa: E402
from mapping_store import item_reference_label  # noqa: E402


PROJECT_ID = "la33ebc39539"
DEFAULT_DOC_PATH = Path("/home/arnold/arnold/github/math-notes/docs/linear-algebra/33.md")
DEFAULT_PROJECT_PATH = ROOT / "projects" / PROJECT_ID / "project.json"
DEFAULT_MKDOCS_ROOT = Path("/home/arnold/arnold/github/math-notes")
DEFAULT_MAPPING_PATH = DEFAULT_MKDOCS_ROOT / "docs" / "linear-algebra" / "mapping.md"
SOURCE_PART1 = DEFAULT_MKDOCS_ROOT / "docs" / "linear-algebra" / "Stephen H. Friedberg, Arnold J. Insel, Lawrence E. Spence - Linear Algebra (Part 1) (1).md"
LEGACY_MAP = DEFAULT_MKDOCS_ROOT / "docs" / "linear-algebra" / "ORIGINAL_TO_NOTES_NUMBERING_MAP.md"
SUBJECT_PATH = ROOT / "projects" / "_subjects" / "linear-algebra.json"
ENTRY_LABEL_RE = re.compile(
    r"\b(Definition|Theorem|Lemma|Corollary|Example|Exercise|Concept|Proposition)"
    r"\s+33\.(\d+)\b"
)


HEADER_REPLACEMENTS = {
    '!!! concept "Concept 33.1 : "': (
        '!!! concept "Concept 33.1 : Adjoints for transformations between inner product spaces"'
    ),
    '!!! theorem "Theorem 33.2 : "': (
        '!!! theorem "Theorem 33.2 : Singular value theorem for linear transformations"'
    ),
    '!!! theorem "Theorem 33.2 : Singular Value Theorem for Linear Transformations"': (
        '!!! theorem "Theorem 33.2 : Singular value theorem for linear transformations"'
    ),
    '!!! definition "Definition 33.3 : "': (
        '!!! definition "Definition 33.3 : Singular Values of a Linear Transformation"'
    ),
    '!!! example "Example 33.4 : "': (
        '!!! example "Example 33.4 : Singular values for the derivative map on polynomials"'
    ),
    '!!! example "Example 33.5 : "': (
        '!!! example "Example 33.5 : Image of the unit circle under an invertible operator"'
    ),
    '!!! definition "Definition 33.6 : "': (
        '!!! definition "Definition 33.6 : Singular Values of a Matrix"'
    ),
    '!!! theorem "Theorem 33.7 : "': (
        '!!! theorem "Theorem 33.7 : Singular value decomposition theorem for matrices"'
    ),
    '!!! theorem "Theorem 33.7 : Singular Value Decomposition Theorem for Matrices"': (
        '!!! theorem "Theorem 33.7 : Singular value decomposition theorem for matrices"'
    ),
    '!!! definition "Definition 33.8 : "': (
        '!!! definition "Definition 33.8 : Singular Value Decomposition"'
    ),
    '!!! example "Example 33.9 : "': (
        '!!! example "Example 33.9 : A singular value decomposition of a rank-one matrix"'
    ),
    '!!! theorem "Theorem 33.10 : "': (
        '!!! theorem "Theorem 33.10 : Polar decomposition"'
    ),
    '!!! theorem "Theorem 33.10 : Polar Decomposition"': (
        '!!! theorem "Theorem 33.10 : Polar decomposition"'
    ),
    '!!! example "Example 33.11 : "': (
        '!!! example "Example 33.11 : Polar decomposition of a $2 \\times 2$ matrix"'
    ),
    '!!! definition "Definition 33.12 : "': (
        '!!! definition "Definition 33.12 : Pseudoinverse of a Linear Transformation"'
    ),
    '!!! concept "Concept 33.13 : "': (
        '!!! concept "Concept 33.13 : Pseudoinverse from singular values"'
    ),
    '!!! example "Example 33.14 : "': (
        '!!! example "Example 33.14 : Pseudoinverse of the derivative map on polynomials"'
    ),
    '!!! definition "Definition 33.15 : "': (
        '!!! definition "Definition 33.15 : Pseudoinverse of a Matrix"'
    ),
    '!!! theorem "Theorem 33.16 : "': (
        '!!! theorem "Theorem 33.16 : SVD formula for the pseudoinverse"'
    ),
    '!!! example "Example 33.17 : "': (
        '!!! example "Example 33.17 : Pseudoinverse of a rank-one matrix"'
    ),
    '!!! theorem "Lemma 33.18 : "': (
        '!!! theorem "Lemma 33.18 : Projection identities for the pseudoinverse"'
    ),
    '!!! theorem "Theorem 33.19 : "': (
        '!!! theorem "Theorem 33.19 : Least-squares and minimum-norm solutions from the pseudoinverse"'
    ),
    '!!! example "Example 33.20 : "': (
        '!!! example "Example 33.20 : Minimum-norm and best-approximation solutions"'
    ),
}


TEXT_REPLACEMENTS = {
    "Psuedoinverse": "Pseudoinverse",
    "any operator T for": "any operator $T$ for",
    "cigenvalues": "eigenvalues",
    "cigenvectors": "eigenvectors",
    "cigenvalucs": "eigenvalues",
    "cigenvalue": "eigenvalue",
    "corrcsponding": "corresponding",
    "Thercfore": "Therefore",
    "cxists": "exists",
    "lincar": "linear",
    "incousistent": "inconsistent",
    "In Exercise 15 of Section 6.3, the definition": (
        "In **Exercise 29.15**, the definition"
    ),
    "where V and W are": "where $V$ and $W$ are",
    "from W to V": "from $W$ to $V$",
    "Let V and W be": "Let $V$ and $W$ be",
    "for V and": "for $V$ and",
    "for W and": "for $W$ and",
    "for V consisting": "for $V$ consisting",
    "on V ;": "on $V$;",
    "on V;": "on $V$;",
    "orthonormal subset of W .": "orthonormal subset of $W$.",
    "orthogonal projection of V on": "orthogonal projection of $V$ on",
    "orthogonal projection of W on": "orthogonal projection of $W$ on",
    "of T is a linear": "of $T$ is a linear",
    "by Exercise 18 of Section 6.4.": "by **Exercise 30.18**.",
    "By Exercises 18 of Section 6.4 and $15(\\mathrm{~d})$ of Section $6.3, T^{*} T$": (
        "By **Exercise 30.18** and **Exercise 29.15**(d), $T^{*}T$"
    ),
    "by Exercise 15(d) of Section 6.3.": "by **Exercise 29.15**(d).",
    "By Theorem 6.7(a) (p. 352)": "By **Theorem 28.20**(a)",
    "By Theorem 2.13(a) (p. 90)": "By **Theorem 10.12**(a)",
    "by Theorem 2.13(a) and (b)": "by **Theorem 10.12**(a) and (b)",
    "(See Exercise 15 of Section 6.3.)": "(See **Exercise 29.15**.)",
    "Exercise 21(a) of Section 6.2": "source Exercise 21(a) from source subsection 6.2",
    "in Theorem 6.26": "in **Theorem 33.2**",
    "We apply Theorem 6.26": "We apply **Theorem 33.2**",
    "satisfying (4) in Theorem 6.26": "satisfying (4) in **Theorem 33.2**",
    "as in Theorem 6.26.": "as in **Theorem 33.2**.",
    "By Theorem 6.26": "By **Theorem 33.2**",
    "By Theorem 6.27": "By **Theorem 33.7**",
    "as in the proof of Theorem 6.27": "as in the proof of **Theorem 33.7**",
    "as in Theorem 6.27": "as in **Theorem 33.7**",
    "in the notation of Theorem 6.28": "in the notation of **Theorem 33.10**",
    "By Theorem 6.29": "By **Theorem 33.16**",
    "Theorem 6.29": "**Theorem 33.16**",
    "Theorem 6.30(a)": "**Theorem 33.19**(a)",
    "Theorem 6.30(b)": "**Theorem 33.19**(b)",
    "Exercise 14 of Section 6.5": "**Exercise 31.14**",
    "Exercise 17 of Section 6.4": "**Exercise 30.17**",
    "the corollary to Theorem 6.6 (p. 350)": "the corollary to **Theorem 28.17**",
    "the corollary to Theorem 6.6 (p.350)": "the corollary to **Theorem 28.17**",
    "as in Example 1.": "as in **Example 33.4**.",
    "in Example 1.": "in **Example 33.4**.",
    "By Example 6,": "By **Example 33.17**,",
    "Since $A$ is the matrix of Example 3,": (
        "Since $A$ is the matrix of **Example 33.9**,"
    ),
    "from W to $\\checkmark$": "from $W$ to $V$",
    "linear transformation or rank": "linear transformation of rank",
    "singular values of T .": "singular values of $T$.",
    "Let T be": "Let $T$ be",
    "Suppose that V and W": "Suppose that $V$ and $W$",
    "singular values of T satisfying": "singular values of $T$ satisfying",
    "$a \\top^{\\dagger}(1)": "$a \\mathrm{T}^{\\dagger}(1)",
    "a \\top^{\\dagger}(1)": "a \\mathrm{T}^{\\dagger}(1)",
    "\\frac{1}{\\sigma_{i}} L_{A}\\left(v_{1}\\right)": (
        "\\frac{1}{\\sigma_{1}} L_{A}\\left(v_{1}\\right)"
    ),
    "\\frac{1}{\\sigma_{i}} A v_{1}": "\\frac{1}{\\sigma_{1}} A v_{1}",
    "\\text { if } i=j \\leq r  \\tag{5}": "\\text { if } i \\leq r  \\tag{5}",
    "$\\mathrm{T}(f(x))=$ $f^{\\prime}(x)$": "$\\mathrm{T}(f(x))=f^{\\prime}(x)$",
    "adjoint of T.": "adjoint of $T$.",
    "$T^{*}$ $T$": "$T^{*}T$",
    "T* $T$": "$T^{*}T$",
    "$\\mathrm{T} . \\mathrm{P}_{2}(R)$.": "$\\mathrm{T}: \\mathrm{P}_{2}(R)$",
    "(See Figure 6.6.)": "(See Figure 33.1.)",
    "Then.\n    $$": "Then\n    $$",
    "on $V$ ;": "on $V$;",
    "By the lemma.": "By the lemma,",
    "by Exercise 23;": "by source Exercise 23;",
    "$A z=A A^{\\dagger} b=$ $\\mathrm{TT}^{\\dagger}(b)=b$ is the orthogonal projection": (
        "$A z=A A^{\\dagger} b=\\mathrm{TT}^{\\dagger}(b)$ is the orthogonal projection"
    ),
    "$A x=b$ is incousistent": "$A x=b$ is inconsistent",
}


EXERCISE_SECTION = r'''## Exercise

!!! exercise "Exercise 33.9"
    Let $V$ and $W$ be finite-dimensional inner product spaces over $F$, and suppose that $\left\{v_{1}, v_{2}, \ldots, v_{n}\right\}$ and $\left\{u_{1}, u_{2}, \ldots, u_{m}\right\}$ are orthonormal bases for $V$ and $W$, respectively.
    Let $\mathrm{T}: V \rightarrow W$ be a linear transformation of rank $r$, and suppose that $\sigma_{1} \geq \sigma_{2} \geq \cdots \geq \sigma_{r}>0$ satisfy

    $$
    \mathrm{T}\left(v_{i}\right)= \begin{cases}\sigma_{i} u_{i} & \text { if } 1 \leq i \leq r \\ 0 & \text { if } r<i.\end{cases}
    $$

    - (a) Prove that $\left\{u_{1}, u_{2}, \ldots, u_{m}\right\}$ is a set of eigenvectors of $\mathrm{T}\mathrm{T}^{*}$ with corresponding eigenvalues $\lambda_{1}, \lambda_{2}, \ldots, \lambda_{m}$, where

        $$
        \lambda_{i}= \begin{cases}\sigma_{i}^{2} & \text { if } 1 \leq i \leq r \\ 0 & \text { if } r<i.\end{cases}
        $$

    - (b) Let $A$ be an $m \times n$ matrix with real or complex entries.
        Prove that the nonzero singular values of $A$ are the positive square roots of the nonzero eigenvalues of $A A^{*}$, including repetitions.
    - (c) Prove that $\mathrm{T}\mathrm{T}^{*}$ and $\mathrm{T}^{*}\mathrm{T}$ have the same nonzero eigenvalues, including repetitions.
    - (d) State and prove a result for matrices analogous to (c).

!!! exercise "Exercise 33.11"
    This exercise relates the singular values of a well-behaved linear operator or matrix to its eigenvalues.

    - (a) Let $T$ be a normal linear operator on an $n$-dimensional inner product space with eigenvalues $\lambda_{1}, \lambda_{2}, \ldots, \lambda_{n}$.
        Prove that the singular values of $T$ are $\left|\lambda_{1}\right|,\left|\lambda_{2}\right|, \ldots,\left|\lambda_{n}\right|$.
    - (b) State and prove a result for matrices analogous to (a).

!!! exercise "Exercise 33.12"
    Let $A$ be a normal matrix with an orthonormal basis of eigenvectors $\beta=\left\{v_{1}, v_{2}, \ldots, v_{n}\right\}$ and corresponding eigenvalues $\lambda_{1}, \lambda_{2}, \ldots, \lambda_{n}$.
    Let $V$ be the $n \times n$ matrix whose columns are the vectors in $\beta$.
    Prove that for each $i$ there is a scalar $\theta_{i}$ of absolute value $1$ such that if $U$ is the $n \times n$ matrix with $\theta_{i}v_{i}$ as column $i$ and $\Sigma$ is the diagonal matrix such that $\Sigma_{ii}=\left|\lambda_{i}\right|$ for each $i$, then $U\Sigma V^{*}$ is a singular value decomposition of $A$.

!!! exercise "Exercise 33.13"
    Prove that if $A$ is a positive semidefinite matrix, then the singular values of $A$ are the same as the eigenvalues of $A$.

!!! exercise "Exercise 33.14"
    Prove that if $A$ is a positive definite matrix and $A=U\Sigma V^{*}$ is a singular value decomposition of $A$, then $U=V$.

!!! exercise "Exercise 33.15"
    Let $A$ be a square matrix with a polar decomposition $A=W P$.

    - (a) Prove that $A$ is normal if and only if $W P^{2}=P^{2} W$.
    - (b) Use (a) to prove that $A$ is normal if and only if $W P=P W$.

!!! exercise "Exercise 33.16"
    Let $A$ be a square matrix.
    Prove an alternate form of the polar decomposition for $A$: there exists a unitary matrix $W$ and a positive semidefinite matrix $P$ such that $A=P W$.

!!! exercise "Exercise 33.17"
    Let $T$ and $U$ be linear operators on $\mathbb{R}^{2}$ defined for all $\left(x_{1}, x_{2}\right) \in \mathbb{R}^{2}$ by

    $$
    \mathrm{T}\left(x_{1}, x_{2}\right)=\left(x_{1}, 0\right)
    \quad \text { and } \quad
    \mathrm{U}\left(x_{1}, x_{2}\right)=\left(x_{1}+x_{2}, 0\right).
    $$

    - (a) Prove that $(UT)^{\dagger} \neq T^{\dagger} U^{\dagger}$.
    - (b) Exhibit matrices $A$ and $B$ such that $AB$ is defined, but $(AB)^{\dagger} \neq B^{\dagger}A^{\dagger}$.

!!! exercise "Exercise 33.18"
    Let $A$ be an $m \times n$ matrix.
    Prove the following results.

    - (a) For any $m \times m$ unitary matrix $G$, $(GA)^{\dagger}=A^{\dagger}G^{*}$.
    - (b) For any $n \times n$ unitary matrix $H$, $(AH)^{\dagger}=H^{*}A^{\dagger}$.

!!! exercise "Exercise 33.19"
    Let $A$ be a matrix with real or complex entries.
    Prove the following results.

    - (a) The nonzero singular values of $A$ are the same as the nonzero singular values of $A^{*}$, which are the same as the nonzero singular values of $A^{t}$.
    - (b) $\left(A^{\dagger}\right)^{*}=\left(A^{*}\right)^{\dagger}$.
    - (c) $\left(A^{\dagger}\right)^{t}=\left(A^{t}\right)^{\dagger}$.

!!! exercise "Exercise 33.20"
    Let $A$ be a square matrix such that $A^{2}=O$.
    Prove that $\left(A^{\dagger}\right)^{2}=O$.

!!! exercise "Exercise 33.21"
    Let $V$ and $W$ be finite-dimensional inner product spaces, and let $T: V \rightarrow W$ be linear.
    Prove the following results.

    - (a) $\mathrm{T}\mathrm{T}^{\dagger}\mathrm{T}=\mathrm{T}$.
    - (b) $\mathrm{T}^{\dagger}\mathrm{T}\mathrm{T}^{\dagger}=\mathrm{T}^{\dagger}$.
    - (c) Both $\mathrm{T}^{\dagger}\mathrm{T}$ and $\mathrm{T}\mathrm{T}^{\dagger}$ are self-adjoint.

    The preceding three statements are called the Penrose conditions, and they characterize the pseudoinverse of a linear transformation as shown in **Exercise 33.22**.

!!! exercise "Exercise 33.22"
    Let $V$ and $W$ be finite-dimensional inner product spaces.
    Let $T: V \rightarrow W$ and $U: W \rightarrow V$ be linear transformations such that $TUT=T$, $UTU=U$, and both $UT$ and $TU$ are self-adjoint.
    Prove that $U=T^{\dagger}$.

!!! exercise "Exercise 33.25"
    Let $V$ and $W$ be finite-dimensional inner product spaces, and let $\mathrm{T}: V \rightarrow W$ be linear.
    Prove the following results.

    - (a) If $T$ is one-to-one, then $T^{*}T$ is invertible and $T^{\dagger}=\left(T^{*}T\right)^{-1}T^{*}$.
    - (b) If $T$ is onto, then $\mathrm{T}\mathrm{T}^{*}$ is invertible and $\mathrm{T}^{\dagger}=\mathrm{T}^{*}\left(\mathrm{T}\mathrm{T}^{*}\right)^{-1}$.

!!! exercise "Exercise 33.26"
    Let $V$ and $W$ be finite-dimensional inner product spaces with orthonormal bases $\beta$ and $\gamma$, respectively, and let $\mathrm{T}: V \rightarrow W$ be linear.
    Prove that

    $$
    \left([\mathrm{T}]_{\beta}^{\gamma}\right)^{\dagger}
    =
    \left[\mathrm{T}^{\dagger}\right]_{\gamma}^{\beta}.
    $$

!!! exercise "Exercise 33.27"
    Let $V$ and $W$ be finite-dimensional inner product spaces, and let $\mathrm{T}: V \rightarrow W$ be a linear transformation.
    Prove part (b) of **Lemma 33.18**: $\mathrm{T}\mathrm{T}^{\dagger}$ is the orthogonal projection of $W$ on $R(T)$.
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize linear-algebra 33.md and migrate it into a notes-helper project."
    )
    parser.add_argument("--doc-path", default=str(DEFAULT_DOC_PATH))
    parser.add_argument("--project-path", default=str(DEFAULT_PROJECT_PATH))
    parser.add_argument("--write", action="store_true", help="Write files. Default is dry-run.")
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    return parser.parse_args()


def add_opening_section(head: str) -> str:
    if "## The Singular Value Decomposition" in head:
        return head
    for marker in ('\n!!! concept "Concept 33.1', '\n!!! theorem "Theorem 33.2'):
        if marker in head:
            return head.replace(marker, f"\n## The Singular Value Decomposition\n{marker}", 1)
    return head


def remove_top_level_admonition_by_label(text: str, label: str) -> tuple[str, bool]:
    lines = text.splitlines()
    out: list[str] = []
    removed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("!!! ") and f'"{label} ' in line:
            removed = True
            i += 1
            while i < len(lines):
                candidate = lines[i]
                if candidate.strip() and not candidate.startswith((" ", "\t")):
                    break
                i += 1
            while out and out[-1] == "":
                out.pop()
            if i < len(lines) and out:
                out.append("")
            continue
        out.append(line)
        i += 1
    return "\n".join(out), removed


def renumber_after_removed_33_1(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        number = int(match.group(2))
        if number <= 1:
            return match.group(0)
        return f"{match.group(1)} 33.{number - 1}"

    return ENTRY_LABEL_RE.sub(replace, text)


def bulletize_plain_lettered_subparts(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    active_indent: str | None = None
    for line in lines:
        if not line.strip():
            out.append("")
            continue

        match = re.match(r"^(\s{4,})\(([a-z])\)(?:\s+)?(.*)$", line)
        if match:
            active_indent = match.group(1)
            out.append(f"{active_indent}- ({match.group(2)}) {match.group(3)}".rstrip())
            continue

        if active_indent and line.startswith(active_indent + "!!! "):
            active_indent = None
            out.append(line)
        elif active_indent and line.startswith(active_indent):
            out.append("    " + line)
        else:
            active_indent = None
            out.append(line)
    return "\n".join(out)


def normalize_display_math_spacing(text: str) -> str:
    lines = ["" if not line.strip() else line.rstrip() for line in text.splitlines()]
    out: list[str] = []
    i = 0
    inside_math = False
    while i < len(lines):
        line = lines[i]
        if line.strip() != "$$":
            out.append(line)
            i += 1
            continue

        if not inside_math:
            while out and out[-1] == "":
                out.pop()
            if out:
                out.append("")
            out.append(line)
            inside_math = True
            i += 1
            continue

        out.append(line)
        inside_math = False
        i += 1
        while i < len(lines) and lines[i] == "":
            i += 1
        if i < len(lines):
            out.append("")

    return "\n".join(out)


def normalize_math_notation(text: str) -> str:
    text = re.sub(
        r"\\mathrm\{P\}_\{([^}]+)\}\(R\)",
        r"\\mathrm{P}_{\1}(\\mathbb{R})",
        text,
    )
    text = text.replace(r"\mathrm{P}(R)", r"\mathrm{P}(\mathbb{R})")
    text = re.sub(r"\\mathrm\{R\}(\^\{[^}]+\})", r"\\mathbb{R}\1", text)

    replacements = {
        r"\mathbf{T}": "T",
        r"\mathbf{U}": "U",
        r"\mathrm{~TT}": "TT",
        r"\mathrm{TT}": "TT",
        r"\mathrm{~T}": "T",
        r"\mathrm{T}": "T",
        r"\mathrm{~U}": "U",
        r"\mathrm{U}": "U",
        r"\mathrm{~V}": "V",
        r"\mathrm{V}": "V",
        r"\mathrm{~W}": "W",
        r"\mathrm{W}": "W",
        r"\mathrm{~F}": "F",
        r"\mathrm{F}": "F",
        r"\mathrm{~N}": "N",
        r"\mathrm{N}": "N",
        r"\mathrm{~R}": "R",
        r"\mathrm{R}": "R",
        r"\mathrm{~L}": "L",
        r"\mathrm{L}": "L",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    prose_replacements = {
        "singular values of T ,": "singular values of $T$,",
        "pseudoinverse (or Moore-Penrose generalized inverse) of T ,": (
            "pseudoinverse (or Moore-Penrose generalized inverse) of $T$,"
        ),
        "The pseudoinverse of a linear transformation T on": (
            "The pseudoinverse of a linear transformation $T$ on"
        ),
        " even if T is not invertible": " even if $T$ is not invertible",
        " if T is invertible": " if $T$ is invertible",
    }
    for old, new in prose_replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"(\\langle)([A-Z])", r"\1 \2", text)

    return text


def nest_proof_blocks(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not lines[i].startswith("!!! "):
            out.append(lines[i])
            i += 1
            continue

        block: list[str] = [lines[i]]
        i += 1
        while i < len(lines):
            candidate = lines[i]
            if candidate.strip() and not candidate.startswith((" ", "\t")):
                break
            block.append(candidate)
            i += 1

        proof_index = next(
            (
                idx
                for idx, line in enumerate(block)
                if line.startswith("    Proof.")
                and not any(prev.strip() == "!!! proof" for prev in block[:idx])
            ),
            None,
        )
        if proof_index is None:
            out.extend(block)
            continue

        converted = block[:proof_index]
        if converted and converted[-1] != "":
            converted.append("")
        proof_first = block[proof_index]
        proof_text = proof_first.removeprefix("    Proof.").lstrip()
        converted.append("    !!! proof")
        if proof_text:
            converted.append(f"        {proof_text}")
        for line in block[proof_index + 1:]:
            converted.append("" if line == "" else f"    {line}")
        out.extend(converted)

    return "\n".join(out)


def normalize_head(head: str) -> str:
    text = add_opening_section(head.rstrip())
    for old, new in HEADER_REPLACEMENTS.items():
        text = text.replace(old, new)

    text = re.sub(
        r"(?m)^    Theorem 6\.26 \(Singular Value Theorem for Linear Transformations\)\. ",
        "    ",
        text,
    )
    text = re.sub(
        r"(?m)^    Theorem 6\.27 \(Singular Value Decomposition Theorem for Matrices\)\. ",
        "    ",
        text,
    )
    text = re.sub(r"(?m)^    Theorem 6\.28 \(Polar Decomposition\)\. ", "    ", text)
    text = re.sub(r"(?m)^    Theorem 6\.29\. ", "    ", text)
    text = re.sub(r"(?m)^    Theorem 6\.30\. ", "    ", text)
    text = re.sub(r"(?m)^    Definition\. ", "    ", text)
    text = re.sub(r"(?m)^    Lemma\. ", "    ", text)

    for old, new in TEXT_REPLACEMENTS.items():
        text = text.replace(old, new)

    figure_path = DEFAULT_DOC_PATH.parent / "assets" / "33.1.jpg"
    text = re.sub(r"\n\s*///caption\n\s*Figure 33\.1\.\n\s*///", "", text)

    if figure_path.is_file() and "./assets/33.1.jpg" not in text:
        text = text.replace(
            (
                "If $\\sigma_{1}=\\sigma_{2}$, this is the equation of a circle of radius "
                "$\\sigma_{1}$, and if $\\sigma_{1}>\\sigma_{2}$, this is the equation of an "
                "ellipse with major axis and minor axis oriented along the $x^{\\prime}$-axis "
                "and the $y^{\\prime}$-axis, respectively."
            ),
            (
                "If $\\sigma_{1}=\\sigma_{2}$, this is the equation of a circle of radius "
                "$\\sigma_{1}$, and if $\\sigma_{1}>\\sigma_{2}$, this is the equation of an "
                "ellipse with major axis and minor axis oriented along the $x^{\\prime}$-axis "
                "and the $y^{\\prime}$-axis, respectively. (See Figure 33.1.)\n\n"
                "    ![](./assets/33.1.jpg){: .center style=\"width:100%;\"}"
            ),
            1,
        )
    elif not figure_path.is_file():
        text = re.sub(
            r" \(See Figure 33\.1\.\)\n\n"
            r"    !\[\]\(\./assets/33\.1\.jpg\)\{:\s*\.center style=\"width:100%;\"\}\n"
            r"    ///caption\n"
            r"    Figure 33\.1\.\n"
            r"    ///",
            "",
            text,
        )

    text = text.replace("T*T", "T^{*}T")
    text = text.replace("TT*", "TT^{*}")
    text = text.replace("L (as just defined)", "$L$ (as just defined)")

    text = nest_proof_blocks(text)
    text = bulletize_plain_lettered_subparts(text)
    text, removed_33_1 = remove_top_level_admonition_by_label(text, "Concept 33.1")
    if removed_33_1:
        text = renumber_after_removed_33_1(text)
    return text.strip() + "\n"


def render_doc(original: str) -> str:
    marker = "## Exercise"
    if marker not in original:
        raise ValueError(f"Could not find {marker!r} in document")
    head = normalize_head(original.split(marker, 1)[0])
    exercise_section = bulletize_plain_lettered_subparts(EXERCISE_SECTION.rstrip())
    exercise_section = renumber_after_removed_33_1(exercise_section)
    doc_text = head.rstrip() + "\n\n" + exercise_section + "\n"
    doc_text = normalize_math_notation(doc_text)
    return normalize_display_math_spacing(doc_text).rstrip() + "\n"


def unique_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def apply_reference_graph(item_dicts: list[dict], prefix: str) -> None:
    labels: dict[str, str] = {}
    ambiguous: set[str] = set()
    for item in item_dicts:
        label = item_reference_label(type("ItemProxy", (), item), prefix).strip()
        if not label:
            continue
        if label in labels:
            ambiguous.add(label)
            continue
        labels[label] = item["id"]
    for label in ambiguous:
        labels.pop(label, None)

    references: dict[str, list[str]] = {item["id"]: [] for item in item_dicts}
    referenced_by: dict[str, list[str]] = {item["id"]: [] for item in item_dicts}
    for item in item_dicts:
        seen_targets: set[str] = set()
        for match in re.finditer(r"\*\*(.+?)\*\*", item.get("document") or ""):
            target_id = labels.get(match.group(1).strip())
            if not target_id or target_id == item["id"] or target_id in seen_targets:
                continue
            references[item["id"]].append(target_id)
            referenced_by[target_id].append(item["id"])
            seen_targets.add(target_id)

    for item in item_dicts:
        item["references"] = unique_preserve(references[item["id"]])
        item["referencedBy"] = unique_preserve(referenced_by[item["id"]])


def reference_files(project_path: Path) -> list[dict]:
    project_dir = project_path.parent
    refs_dir = project_dir / "refs"
    return [
        {
            "id": "source33",
            "name": "source_part1.md",
            "path": str(refs_dir / "source_part1.md"),
            "originalPath": str(SOURCE_PART1),
            "prepared": False,
        },
        {
            "id": "legacy33",
            "name": "legacy_numbering_map.md",
            "path": str(refs_dir / "legacy_numbering_map.md"),
            "originalPath": str(LEGACY_MAP),
            "prepared": False,
        },
    ]


def copy_reference_files(project_path: Path) -> None:
    refs_dir = project_path.parent / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    for source, name in [(SOURCE_PART1, "source_part1.md"), (LEGACY_MAP, "legacy_numbering_map.md")]:
        if source.is_file():
            shutil.copy2(source, refs_dir / name)


def migrate_project(project_path: Path, doc_text: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    if project_path.exists():
        data = json.loads(project_path.read_text(encoding="utf-8"))
        created_at = str(data.get("createdAt") or now)
    else:
        data = {}
        created_at = now

    title, items = split_existing_markdown_into_items(doc_text, default_prefix="33")
    item_dicts = [item.model_dump() for item in items]
    apply_reference_graph(item_dicts, "33")

    return {
        "id": PROJECT_ID,
        "subjectId": "linear-algebra",
        "title": f"[Linear Algebra] {title}",
        "blueprintPath": "",
        "references": reference_files(project_path),
        "mkdocsRoot": str(DEFAULT_MKDOCS_ROOT),
        "outputPath": str(DEFAULT_DOC_PATH),
        "mappingPath": str(DEFAULT_MAPPING_PATH),
        "items": item_dicts,
        "numberPrefix": "33",
        "syncedNumberPrefix": "33",
        "createdAt": created_at,
        "updatedAt": now,
    }


def count_linear_algebra_projects() -> int:
    count = 0
    for path in project_file_candidates(ROOT / "projects"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and infer_subject_id(data) == "linear-algebra":
            count += 1
    return count


def update_subject_project_count() -> None:
    if not SUBJECT_PATH.exists():
        return
    data = json.loads(SUBJECT_PATH.read_text(encoding="utf-8"))
    data["projectCount"] = count_linear_algebra_projects()
    data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    SUBJECT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summarize(project_data: dict, doc_text: str) -> dict:
    exercise_count = sum(
        1 for item in project_data["items"]
        if item.get("kind") == "admonition" and item.get("type") == "exercise"
    )
    admonition_count = sum(1 for item in project_data["items"] if item.get("kind") == "admonition")
    labels = [
        item_reference_label(type("ItemProxy", (), item), "33")
        for item in project_data["items"]
        if item.get("kind") == "admonition"
    ]
    return {
        "projectId": project_data.get("id"),
        "itemCount": len(project_data["items"]),
        "admonitionCount": admonition_count,
        "exerciseCount": exercise_count,
        "docLineCount": len(doc_text.splitlines()),
        "admonitionLabels": labels,
    }


def main() -> int:
    args = parse_args()
    doc_path = Path(os.path.abspath(os.path.expanduser(args.doc_path)))
    project_path = Path(os.path.abspath(os.path.expanduser(args.project_path)))
    doc_text = render_doc(doc_path.read_text(encoding="utf-8"))
    project_data = migrate_project(project_path, doc_text)
    report = summarize(project_data, doc_text)
    report["wrote"] = bool(args.write)
    report["docPath"] = str(doc_path)
    report["projectPath"] = str(project_path)

    if args.write:
        doc_path.write_text(doc_text, encoding="utf-8")
        project_path.parent.mkdir(parents=True, exist_ok=True)
        project_path.write_text(json.dumps(project_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        copy_reference_files(project_path)
        update_subject_project_count()
        report["subjectProjectCount"] = count_linear_algebra_projects()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Project: {report['projectPath']}")
        print(f"Doc: {report['docPath']}")
        print(f"Items: {report['itemCount']}")
        print(f"Admonitions: {report['admonitionCount']}")
        print(f"Exercises: {report['exerciseCount']}")
        print(f"Mode: {'wrote files' if args.write else 'dry-run only'}")
        if "subjectProjectCount" in report:
            print(f"Subject projects: {report['subjectProjectCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
