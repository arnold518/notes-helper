#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from agent_runner import _validate_prepared_text  # noqa: E402


def run_tests() -> None:
    original = """### 2.2.1 State space

Quantum mechanics does not tell us what the state space is. Figuring that out is difficult. For example, QED describes how atoms and light interact.

The qubit has a two-dimensional state space. Suppose |0> and |1> form an orthonormal basis.
"""

    sentence_reflow = """### 2.2.1 State space

Quantum mechanics does not tell us what the state space is.
Figuring that out is difficult.
For example, QED describes how atoms and light interact.

The qubit has a two-dimensional state space.
Suppose |0> and |1> form an orthonormal basis.
"""

    _validate_prepared_text(original, sentence_reflow)

    wrapped_word_by_word = """### 2.2.1 State space

Quantum mechanics
does not
tell us
what the
state space
is.
Figuring that
out is
difficult.
For example,
QED describes
how atoms
and light
interact.

The qubit
has a
two-dimensional state
space.
Suppose |0>
and |1>
form an
orthonormal basis.
"""

    try:
        _validate_prepared_text(original, wrapped_word_by_word)
    except ValueError as exc:
        assert "line-count drift" in str(exc)
    else:
        raise AssertionError("Expected excessive line-wrap candidate to be rejected")

    print("PASS: prepare reference validation")


if __name__ == "__main__":
    run_tests()
