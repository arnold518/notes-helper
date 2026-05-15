#!/usr/bin/env python3
"""Regression tests for multiple source refs stored in the Original ref column."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import agent_runner  # noqa: E402
from mapping_store import parse_mapping_file, serialize_mapping_file  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_deterministic_original_refs_preserve_multiple_equations() -> None:
    item = type(
        "Item",
        (),
        {
            "kind": "admonition",
            "type": "theorem",
            "content": "basic properties of tensor product",
            "excerpt": (
                "[textbook.md line 680~703]\n\n"
                "By definition the tensor product satisfies the following basic properties:\n"
                "(1) For an arbitrary scalar $z$ and elements $|v\\rangle$ of $V$ and $|w\\rangle$ of $W$,\n\n"
                "$$\n"
                "\\begin{equation*}\n"
                "z(|v\\rangle \\otimes|w\\rangle)=(z|v\\rangle) \\otimes|w\\rangle=|v\\rangle \\otimes(z|w\\rangle) \\tag{2.42}\n"
                "\\end{equation*}\n"
                "$$\n\n"
                "(2) For arbitrary $|v_1\\rangle$ and $|v_2\\rangle$ in $V$ and $|w\\rangle$ in $W$,\n\n"
                "$$\n"
                "\\begin{equation*}\n"
                "(|v_1\\rangle+|v_2\\rangle) \\otimes|w\\rangle=|v_1\\rangle \\otimes|w\\rangle+|v_2\\rangle \\otimes|w\\rangle . \\tag{2.43}\n"
                "\\end{equation*}\n"
                "$$\n\n"
                "(3) For arbitrary $|v\\rangle$ in $V$ and $|w_1\\rangle$ and $|w_2\\rangle$ in $W$,\n\n"
                "$$\n"
                "\\begin{equation*}\n"
                "|v\\rangle \\otimes(|w_1\\rangle+|w_2\\rangle)=|v\\rangle \\otimes|w_1\\rangle+|v\\rangle \\otimes|w_2\\rangle . \\tag{2.44}\n"
                "\\end{equation*}\n"
                "$$"
            ),
        },
    )()

    refs = agent_runner._deterministic_original_refs(item, "Theorem 2.1.48")
    assert refs == [
        "Equation (2.42)",
        "Equation (2.43)",
        "Equation (2.44)",
        "basic properties of tensor product",
    ], refs


def run_tests() -> None:
    test_deterministic_original_refs_preserve_multiple_equations()
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        source_doc = root / "refs" / "[NC2010]QCQI.md"
        mapping_path = root / "mapping.md"

        _write(
            mapping_path,
            (
                f"## Reference: {source_doc}\n\n"
                "| New ref | Original ref | Location |\n"
                "| --- | --- | --- |\n"
                "| Definition 2.1.11 | **Pauli matrices**; **2.1.3 The Pauli matrices** | qcqi/2.1.md |\n"
                "| Theorem 2.1.18 | **Gram-Schmidt procedure; orthonormal basis extension** | qcqi/2.1.md |\n"
            ),
        )

        rows = parse_mapping_file(str(mapping_path))
        assert len(rows) == 2, rows
        assert rows[0].original_refs == ["Pauli matrices", "2.1.3 The Pauli matrices"], rows[0].original_refs
        assert rows[1].original_refs == ["Gram-Schmidt procedure", "orthonormal basis extension"], rows[1].original_refs

        rendered = serialize_mapping_file(rows)
        assert "**Pauli matrices**; **2.1.3 The Pauli matrices**" in rendered, rendered
        assert "**Gram-Schmidt procedure**; **orthonormal basis extension**" in rendered, rendered

    print("PASS: mapping original refs regression")


if __name__ == "__main__":
    run_tests()
