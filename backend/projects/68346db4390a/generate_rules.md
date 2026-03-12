# Generate Rules — Edit freely, these are loaded at runtime

Writing rules:
1. Use each item's excerpt as the ONLY factual source.
2. Preserve mathematical meaning and notation from the excerpt exactly.
3. Keep markdown valid for MkDocs Material.
4. kind=admonition → output a valid admonition block using the item's type.
5. kind=section → output a heading only, at the level implied by h1/h2/h3.
6. kind=text → output regular markdown paragraph(s), no admonition wrapper.
7. Style reference files are for tone/structure only — do not copy facts from them.
8. If a current document is provided, you may build on it — revise, extend, or rewrite as instructed.
9. Write backslashes as-is (e.g. \sigma, \begin{pmatrix}). Do not double-escape.
