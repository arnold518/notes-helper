# Generate Rules - Edit freely, these are loaded at runtime

Writing rules:
1. Use each item's excerpt as the ONLY factual source.
2. Preserve mathematical meaning and notation from the excerpt exactly.
3. Keep markdown valid for MkDocs Material.
4. kind=admonition -> output a valid admonition block using the item's type.
   Write a concise title based on the excerpt content, capitalize only the first letter unless notation, acronyms, or proper nouns require otherwise, and format it like: !!! concept "Epsilon-greedy methods".
5. kind=section -> output a heading only, at the level implied by h1/h2/h3.
6. kind=text -> output regular markdown paragraph(s), no admonition wrapper. If the text item is an algorithm because it came from an "algo" blueprint bullet, use the algorithm formatting rules below.
7. Style reference files are for tone/structure only - do not copy facts from them.
8. If a current document is provided, you may build on it - revise, extend, or rewrite as instructed.
9. Write backslashes as-is (e.g. \pi, \begin{equation*}). Do not double-escape.
10. Capture inline and display math with $...$ and $$...$$ only; do not use \( or \).
11. For every $$...$$ display-math block, include one empty line before the opening $$ and one empty line after the closing $$.
12. Hard-wrap prose at sentence boundaries: each complete sentence must occupy exactly one line, and use single newlines between consecutive sentences unless starting a new paragraph, list, heading, code block, or display-math block.
13. If resolved cross-reference candidates are provided, use them only to replace corresponding original-source references already present in the excerpt or current document.
14. Do not add new notes-side references beyond those already present in the excerpt or current document unless the user explicitly asks for additional references.
15. When referencing other items, integrate the bold reference naturally in prose, for example: "the Bellman equation (**Concept 3.12**)".
16. Bold only the notes-side reference label itself; keep the surrounding prose outside the bold span.
17. In definitions, newly defined concepts must be bolded.
18. For theorem-like results, convergence conditions, or named properties, include the statement and the supporting derivation or proof from the excerpt when present.
19. For algorithms, prefer `!!! code "Algorithm: <name>"` when the item type is `code`; if the item is kind=text because of an older project, use a short heading or paragraph plus a fenced code/math block. Preserve initialization, parameters, loop structure, and update equations.
20. For examples with figures or experimental results, include the figure reference/caption content from the excerpt when it is needed to understand the result. Do not invent visual details not present in the excerpt.
21. Keep equation tags from the source when they are useful identifiers for mapping or cross-references. Remove only clearly unreferenced or malformed duplicate tag text.
