#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from import_existing_notes import split_existing_markdown_into_items  # noqa: E402
from mapping_store import item_reference_label  # noqa: E402


DEFAULT_DOC_PATH = Path("/home/arnold/arnold/github/math-notes/docs/linear-algebra/31.md")
DEFAULT_PROJECT_PATH = ROOT / "projects" / "la31551578c1" / "project.json"


EXERCISE_SECTION = r'''## Exercise

!!! exercise "Exercise 31.6"
    Let $V$ be the inner product space of complex-valued continuous functions on $[0,1]$ with the inner product

    $$
    \langle f, g\rangle=\int_{0}^{1} f(t) \overline{g(t)} d t.
    $$

    Let $h \in V$, and define $T: V \rightarrow V$ by $T(f)=h f$.
    Prove that $T$ is a unitary operator if and only if $|h(t)|=1$ for $0 \leq t \leq 1$.

!!! exercise "Exercise 31.7"
    Prove that if $T$ is a unitary operator on a finite-dimensional inner product space $V$, then $T$ has a unitary square root.
    That is, prove that there exists a unitary operator $U$ such that $T=U^{2}$.

!!! exercise "Exercise 31.8"
    Let $T$ be a self-adjoint linear operator on a finite-dimensional inner product space.
    Prove that $(T+i I)(T-i I)^{-1}$ is unitary using **Exercise 30.10**.

!!! exercise "Exercise 31.9"
    Let $U$ be a linear operator on a finite-dimensional inner product space $V$.
    If $\|U(x)\|=\|x\|$ for all $x$ in some orthonormal basis for $V$, must $U$ be unitary?
    Justify your answer with a proof or a counterexample.

!!! exercise "Exercise 31.10"
    Let $A$ be an $n \times n$ real symmetric or complex normal matrix.
    Prove that

    $$
    \operatorname{tr}(A)=\sum_{i=1}^{n} \lambda_{i}
    \quad \text { and } \quad
    \operatorname{tr}\left(A^{*} A\right)=\sum_{i=1}^{n}\left|\lambda_{i}\right|^{2},
    $$

    where the $\lambda_{i}$ are the not necessarily distinct eigenvalues of $A$.

!!! exercise "Exercise 31.12"
    Let $A$ be an $n \times n$ real symmetric or complex normal matrix.
    Prove that

    $$
    \operatorname{det}(A)=\prod_{i=1}^{n} \lambda_{i},
    $$

    where the $\lambda_{i}$ are the not necessarily distinct eigenvalues of $A$.

!!! exercise "Exercise 31.13"
    Suppose that $A$ and $B$ are diagonalizable matrices.
    Prove or disprove that $A$ is similar to $B$ if and only if $A$ and $B$ are unitarily equivalent.

!!! exercise "Exercise 31.14"
    Prove that if $A$ and $B$ are unitarily equivalent matrices, then $A$ is positive definite [semidefinite] if and only if $B$ is positive definite [semidefinite].
    See **Definition 30.13**.

!!! exercise "Exercise 31.15"
    Let $U$ be a unitary operator on an inner product space $V$, and let $W$ be a finite-dimensional $U$-invariant subspace of $V$.
    Prove the following results.

    - (a) $U(W)=W$.
    - (b) $W^{\perp}$ is $U$-invariant.

    Contrast (b) with **Exercise 31.16**.

!!! exercise "Exercise 31.16"
    Find an example of a unitary operator $U$ on an inner product space and a $U$-invariant subspace $W$ such that $W^{\perp}$ is not $U$-invariant.

!!! exercise "Exercise 31.20"
    Let $V$ be a finite-dimensional inner product space.
    A linear operator $U$ on $V$ is called a **partial isometry** if there exists a subspace $W$ of $V$ such that $\|U(x)\|=\|x\|$ for all $x \in W$ and $U(x)=0$ for all $x \in W^{\perp}$.
    Observe that $W$ need not be $U$-invariant.
    Suppose that $U$ is such an operator and $\left\{v_{1}, v_{2}, \ldots, v_{k}\right\}$ is an orthonormal basis for $W$.
    Prove the following results.

    - (a) $\langle U(x), U(y)\rangle=\langle x, y\rangle$ for all $x, y \in W$.

        Hint: Use **Exercise 26.20**.
    - (b) $\left\{U\left(v_{1}\right), U\left(v_{2}\right), \ldots, U\left(v_{k}\right)\right\}$ is an orthonormal basis for $R(U)$.
    - (c) There exists an orthonormal basis $\gamma$ for $V$ such that the first $k$ columns of $[U]_{\gamma}$ form an orthonormal set and the remaining columns are zero.
    - (d) Let $\left\{w_{1}, w_{2}, \ldots, w_{j}\right\}$ be an orthonormal basis for $R(U)^{\perp}$ and

        $$
        \beta=\left\{U\left(v_{1}\right), U\left(v_{2}\right), \ldots, U\left(v_{k}\right), w_{1}, \ldots, w_{j}\right\}.
        $$

        Then $\beta$ is an orthonormal basis for $V$.
    - (e) Let $T$ be the linear operator on $V$ that satisfies $T\left(U\left(v_{i}\right)\right)=v_{i}$ for $1 \leq i \leq k$ and $T\left(w_{i}\right)=0$ for $1 \leq i \leq j$.
        Then $T$ is well-defined and $T=U^{*}$.

        Hint: Show that $\langle U(x), y\rangle=\langle x, T(y)\rangle$ for all $x, y \in \beta$.
        There are four cases.
    - (f) $U^{*}$ is a partial isometry.

    This exercise is continued in **Exercise 32.9**.

!!! exercise "Exercise 31.21"
    Let $A$ and $B$ be $n \times n$ matrices that are unitarily equivalent.

    - (a) Prove that $\operatorname{tr}\left(A^{*} A\right)=\operatorname{tr}\left(B^{*} B\right)$.
    - (b) Use (a) to prove that

        $$
        \sum_{i, j=1}^{n}\left|A_{i j}\right|^{2}=\sum_{i, j=1}^{n}\left|B_{i j}\right|^{2}.
        $$

!!! exercise "Exercise 31.24"
    Let $T$ and $U$ be orthogonal operators on $\mathbb{R}^{2}$.
    Use **Theorem 31.22** to prove the following results.

    - (a) If $T$ and $U$ are both reflections about lines through the origin, then $UT$ is a rotation.
    - (b) If $T$ is a rotation and $U$ is a reflection about a line through the origin, then both $UT$ and $TU$ are reflections about lines through the origin.

!!! exercise "Exercise 31.25"
    Suppose that $T$ and $U$ are reflections of $\mathbb{R}^{2}$ about the respective lines $L$ and $L^{\prime}$ through the origin and that $\phi$ and $\psi$ are the angles from the positive $x$-axis to $L$ and $L^{\prime}$, respectively.
    By **Exercise 31.24**, $UT$ is a rotation.
    Find its angle of rotation.

!!! exercise "Exercise 31.26"
    Suppose that $T$ and $U$ are orthogonal operators on $\mathbb{R}^{2}$ such that $T$ is the rotation by the angle $\phi$ and $U$ is the reflection about the line $L$ through the origin.
    Let $\psi$ be the angle from the positive $x$-axis to $L$.
    By **Exercise 31.24**, both $UT$ and $TU$ are reflections about lines $L_{1}$ and $L_{2}$, respectively, through the origin.

    - (a) Find the angle $\theta$ from the positive $x$-axis to $L_{1}$.
    - (b) Find the angle $\theta$ from the positive $x$-axis to $L_{2}$.

!!! exercise "Exercise 31.29"
    $Q R$-factorization.
    Let $w_{1}, w_{2}, \ldots, w_{n}$ be linearly independent vectors in $F^{n}$, and let $v_{1}, v_{2}, \ldots, v_{n}$ be the orthogonal vectors obtained from $w_{1}, w_{2}, \ldots, w_{n}$ by the Gram-Schmidt process.
    Let $u_{1}, u_{2}, \ldots, u_{n}$ be the orthonormal basis obtained by normalizing the $v_{i}$.

    - (a) Solving the Gram-Schmidt formula for $w_{k}$ in terms of $u_{k}$, show that

        $$
        w_{k}=\left\|v_{k}\right\| u_{k}+\sum_{j=1}^{k-1}\left\langle w_{k}, u_{j}\right\rangle u_{j}
        \quad(1 \leq k \leq n).
        $$

    - (b) Let $A$ and $Q$ denote the $n \times n$ matrices whose $k$th columns are $w_{k}$ and $u_{k}$, respectively.
        Define $R \in M_{n \times n}(F)$ by

        $$
        R_{j k}= \begin{cases}
        \left\|v_{j}\right\| & \text { if } j=k, \\
        \left\langle w_{k}, u_{j}\right\rangle & \text { if } j<k, \\
        0 & \text { if } j>k.
        \end{cases}
        $$

        Prove that $A=Q R$.

    - (c) Compute $Q$ and $R$ as in (b) for the $3 \times 3$ matrix whose columns are the vectors $(1,1,0)$, $(2,0,1)$, and $(2,2,1)$.
    - (d) Since $Q$ is unitary [orthogonal] and $R$ is upper triangular in (b), every invertible matrix is the product of a unitary [orthogonal] matrix and an upper triangular matrix.
        Suppose that $A \in M_{n \times n}(F)$ is invertible and

        $$
        A=Q_{1} R_{1}=Q_{2} R_{2},
        $$

        where $Q_{1}, Q_{2} \in M_{n \times n}(F)$ are unitary and $R_{1}, R_{2} \in M_{n \times n}(F)$ are upper triangular.
        Prove that $D=R_{2} R_{1}^{-1}$ is a unitary diagonal matrix.

        Hint: Use the fact that an upper triangular unitary matrix is diagonal.
    - (e) The $Q R$ factorization described in (b) provides an orthogonalization method for solving a linear system $A x=b$ when $A$ is invertible.
        Decompose $A$ as $Q R$ by the Gram-Schmidt process or another method, where $Q$ is unitary and $R$ is upper triangular.
        Then $Q R x=b$, and hence $R x=Q^{*} b$.
        This last system can be solved easily since $R$ is upper triangular.

        Use the orthogonalization method and (c) to solve the system

        $$
        \begin{aligned}
        x_{1}+2 x_{2}+2 x_{3} & =1, \\
        x_{1}+2 x_{3} & =11, \\
        x_{2}+x_{3} & =-1.
        \end{aligned}
        $$

!!! exercise "Exercise 31.30"
    Suppose that $\beta$ and $\gamma$ are ordered bases for an $n$-dimensional real [complex] inner product space $V$.
    Prove that if $Q$ is an orthogonal [unitary] $n \times n$ matrix that changes $\gamma$-coordinates into $\beta$-coordinates, then $\beta$ is orthonormal if and only if $\gamma$ is orthonormal.

!!! definition "Definition 31.27 : Householder Operator"
    Let $V$ be a finite-dimensional complex [real] inner product space, and let $u$ be a unit vector in $V$.
    Define the **Householder operator** $H_{u}:V\rightarrow V$ by

    $$
    H_{u}(x)=x-2\langle x, u\rangle u
    $$

    for all $x \in V$.

!!! exercise "Exercise 31.31"
    Let $H_{u}$ be a Householder operator on a finite-dimensional inner product space $V$.
    Prove the following results.

    - (a) $H_{u}$ is linear.
    - (b) $H_{u}(x)=x$ if and only if $x$ is orthogonal to $u$.
    - (c) $H_{u}(u)=-u$.
    - (d) $H_{u}^{*}=H_{u}$ and $H_{u}^{2}=I$; hence $H_{u}$ is a unitary [orthogonal] operator on $V$.

    Note: If $V$ is a real inner product space, then $H_{u}$ is a reflection.

!!! exercise "Exercise 31.32"
    Let $V$ be a finite-dimensional inner product space over $F$.
    Let $x$ and $y$ be linearly independent vectors in $V$ such that $\|x\|=\|y\|$.

    - (a) If $F=\mathbb{C}$, prove that there exists a unit vector $u$ in $V$ and a complex number $\theta$ with $|\theta|=1$ such that $H_{u}(x)=\theta y$.

        Hint: Choose $\theta$ so that $\langle x, \theta y\rangle$ is real, and set

        $$
        u=\frac{1}{\|x-\theta y\|}(x-\theta y).
        $$

    - (b) If $F=\mathbb{R}$, prove that there exists a unit vector $u$ in $V$ such that $H_{u}(x)=y$.
'''


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize linear-algebra 31.md exercises and migrate them into the project file."
    )
    parser.add_argument("--doc-path", default=str(DEFAULT_DOC_PATH))
    parser.add_argument("--project-path", default=str(DEFAULT_PROJECT_PATH))
    parser.add_argument("--write", action="store_true", help="Write files. Default is dry-run.")
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    return parser.parse_args()


def normalize_existing_text(text: str) -> str:
    replacements = {
        "Theorem 31.10 : Rows and columns of orthogonal / unitary matrix forms an orthonormal basis for $F^{n}$.": (
            "Theorem 31.10 : Rows and columns of orthogonal / unitary matrices form orthonormal bases for $F^{n}$."
        ),
        "Also, the condition $A^{*} A=I$ is equivalent to the statement that the rows of $A$ form an orthonormal basis for $F^{n}$.": (
            "Also, the condition $A^{*} A=I$ is equivalent to the statement that the columns of $A$ form an orthonormal basis for $F^{n}$."
        ),
        "The proof on the remark about the columns of $A$ and the condition $A^{*} A=I$ is same.": (
            "The proof for the statement about the columns of $A$ and the condition $A^{*} A=I$ is the same."
        ),
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def render_doc(original: str) -> str:
    marker = "## Exercise"
    if marker not in original:
        raise ValueError(f"Could not find {marker!r} in document")
    head = original.split(marker, 1)[0].rstrip()
    exercise_section = bulletize_plain_lettered_subparts(EXERCISE_SECTION.rstrip())
    exercise_section = exercise_section.replace(
        "M_{n \\times n}(F)",
        "\\mathrm{M}_{n \\times n}(F)",
    )
    doc_text = normalize_existing_text(head) + "\n\n" + exercise_section + "\n"
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


def migrate_project(project_path: Path, doc_text: str) -> dict:
    data = json.loads(project_path.read_text(encoding="utf-8"))
    _, items = split_existing_markdown_into_items(doc_text, default_prefix="31")
    item_dicts = [item.model_dump() for item in items]
    apply_reference_graph(item_dicts, "31")
    data["items"] = item_dicts
    data["numberPrefix"] = "31"
    data["syncedNumberPrefix"] = "31"
    data["updatedAt"] = datetime.now(timezone.utc).isoformat()
    return data


def summarize(project_data: dict, doc_text: str) -> dict:
    exercise_count = sum(
        1 for item in project_data["items"]
        if item.get("kind") == "admonition" and item.get("type") == "exercise"
    )
    definition_count = sum(
        1 for item in project_data["items"]
        if item.get("kind") == "admonition" and item.get("type") == "definition"
    )
    labels = [
        item_reference_label(type("ItemProxy", (), item), "31")
        for item in project_data["items"]
        if item.get("kind") == "admonition"
    ]
    return {
        "projectId": project_data.get("id"),
        "itemCount": len(project_data["items"]),
        "exerciseCount": exercise_count,
        "definitionCount": definition_count,
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
        project_path.write_text(json.dumps(project_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Project: {report['projectPath']}")
        print(f"Doc: {report['docPath']}")
        print(f"Items: {report['itemCount']}")
        print(f"Exercises: {report['exerciseCount']}")
        print(f"Definitions: {report['definitionCount']}")
        print(f"Mode: {'wrote files' if args.write else 'dry-run only'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
