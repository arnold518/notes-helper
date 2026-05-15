"""Shared subject-level rule defaults."""
from __future__ import annotations

RULE_KINDS = frozenset({"match", "generate", "map"})

DEFAULT_MATCH_RULES = """\
# Match Rules — Edit freely, these are loaded at runtime

Extraction rules:
1. Extract sentence-wise. Do NOT start or end a chunk in the middle of a sentence.
2. When $$...$$ math appears inside a sentence, include the full surrounding sentence.
3. Expand start/end lines as needed so each chunk contains complete sentences.
4. Keep text verbatim from the source — no paraphrasing.
5. If multiple chunks are needed for one item, include all of them.
6. If a previous excerpt is provided, treat it as a hint only and re-extract from the current reference files; replace stale file names, line numbers, and chunk boundaries when needed.
7. For section headers, match only the relevant header.

Output format for each excerpt file:
- Format each chunk as: [filename line X~Y]\\n\\n{verbatim text}
- Separate multiple chunks with: a blank line, then ---, then a blank line
- Write backslashes as-is (e.g. \\sigma, \\begin{pmatrix}). Do not double-escape.
"""

DEFAULT_GENERATE_RULES = """\
# Generate Rules — Edit freely, these are loaded at runtime

Writing rules:
1. Use each item's excerpt as the ONLY factual source.
2. Preserve mathematical meaning and notation from the excerpt exactly.
3. Keep markdown valid for MkDocs Material.
4. kind=admonition → output a valid admonition block using the item's type.
   Write a concise title based on the excerpt content, capitalize only the first letter unless notation, acronyms, or proper nouns require otherwise, and format it like: !!! definition "Definition 2.1.1 : Complex vector space"
5. kind=section → output a heading only, at the level implied by h1/h2/h3.
6. kind=text → output regular markdown paragraph(s), no admonition wrapper.
7. Style reference files are for tone/structure only — do not copy facts from them.
8. If a current document is provided, you may build on it — revise, extend, or rewrite as instructed.
9. Write backslashes as-is (e.g. \\sigma, \\begin{pmatrix}). Do not double-escape.
10. If resolved cross-reference candidates are provided in the prompt, use them to replace corresponding original-source references already present in the excerpt or current document.
11. Do not add new notes-side references beyond those already present in the excerpt or current document unless the user explicitly asks for additional references.
12. Unless the user explicitly asks for additional references, do not auto-insert definition/concept references for ordinary term mentions; reserve non-formal semantic cross-references for clearly named theorem/lemma/corollary/example-style results.
13. When referencing other items, integrate the bold reference naturally into prose, for example: "according to **Definition 3.5.1**" or "Using the gram-schmidt theorem (**Theorem 2.5.1**)".
14. Bold only the notes-side reference label itself; keep the surrounding prose outside the bold span.
15. In definitions, newly defined concepts must be bolded.
16. Capture inline and display math with $...$ and $$...$$ only; do not use \\( or \\).
17. For every $$...$$ display-math block, include one empty line before the opening $$ and one empty line after the closing $$.
18. Hard-wrap prose at sentence boundaries: each complete sentence must occupy exactly one line, and use single newlines between consecutive sentences unless starting a new paragraph, list, heading, code block, or display-math block.
19. If a theorem, corollary, or lemma is missing a proof and the excerpt supports one, add it using a nested `!!! proof` block inside the item.
20. For a theorem, lemma, proposition, corollary, or proof with multiple labeled parts such as (a), (b), (c), write the parts as a markdown unordered list using entries like `- (a)`, `- (b)`, `- (c)` on their own lines.
    Put the content of each list item on the same line when short.
    If a proof is also split by parts, format the proof the same way: each proof part should begin with its own list item such as `- (a)`, and the body of that proof part should start on the next indented line under that item.
    Keep all continuation paragraphs and display math indented so they remain inside the same list item and admonition block.
21. Remove unreferenced \\tag annotations in LaTeX expressions.
"""

DEFAULT_MAP_RULES = """\
# Map Rules — Edit freely, these are loaded at runtime

Mapping rules:
1. Read each item's excerpt to determine what it is called in the original textbook.
2. The excerpt header [filename line X~Y] shows the current reference name; use the reference name mapping to find the original file path.
3. Use the original file path as the section header in the mapping file: ## Reference: <original-path>
4. Find or create a row where New ref = the item's new ref label and Location = the canonical notes output path (relative to MkDocs docs/ when available).
5. Set Original ref to one or more narrow, canonical source-side identifiers for the item itself.
6. If the item has multiple equally canonical source-side identifiers, separate them with "; " in the Original ref cell.
7. Prefer explicit source-side labels when available (for example: "Theorem 2.3", "Exercise 2.19", "Equation (2.61)", "Box 2.1", "Figure 2.2", section title).
8. If no formal label exists, use the exact named result or concept from the source text.
9. Do not use dependencies, supporting mentions, or downstream references inside the excerpt as Original ref.
10. Do not try to encode exhaustive synonyms or alias variants in the mapping file; generation will do semantic search over canonical rows.
11. Surround each Original ref value with ** for bold.
12. If the excerpt has no identifiable original reference, omit the item from the map.
13. Preserve all existing rows — only add or update rows for the given items.
14. If the mapping table includes References and Referenced by columns, preserve them; the system maintains those columns separately.
"""


def default_rules(kind: str) -> str:
    if kind == "match":
        return DEFAULT_MATCH_RULES
    if kind == "generate":
        return DEFAULT_GENERATE_RULES
    if kind == "map":
        return DEFAULT_MAP_RULES
    raise ValueError("kind must be 'match', 'generate', or 'map'")
