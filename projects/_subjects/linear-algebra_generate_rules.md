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
9. Write backslashes as-is (e.g. \sigma, \begin{pmatrix}). Do not double-escape.
10. If resolved cross-reference candidates are provided in the prompt, use them to replace corresponding original-source references already present in the excerpt or current document.
11. Do not add new notes-side references beyond those already present in the excerpt or current document unless the user explicitly asks for additional references.
12. Unless the user explicitly asks for additional references, do not auto-insert definition/concept references for ordinary term mentions; reserve non-formal semantic cross-references for clearly named theorem/lemma/corollary/example-style results.
13. When referencing other items, integrate the bold reference naturally into prose, for example: "according to **Definition 3.5.1**" or "Using the gram-schmidt theorem (**Theorem 2.5.1**)".
14. Bold only the notes-side reference label itself; keep the surrounding prose outside the bold span.
15. In definitions, newly defined concepts must be bolded.
16. Capture inline and display math with $...$ and $$...$$ only; do not use \( or \).
17. For every $$...$$ display-math block, include one empty line before the opening $$ and one empty line after the closing $$.
18. Hard-wrap prose at sentence boundaries: each complete sentence must occupy exactly one line, and use single newlines between consecutive sentences unless starting a new paragraph, list, heading, code block, or display-math block.
19. If a theorem, corollary, or lemma is missing a proof and the excerpt supports one, add it using a nested `!!! proof` block inside the item.
20. Remove unreferenced \tag annotations in LaTeX expressions.
