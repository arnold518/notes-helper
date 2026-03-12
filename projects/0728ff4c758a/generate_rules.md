# Generate Rules — Edit freely, these are loaded at runtime

Writing rules:
1. Use each item's excerpt as the ONLY factual source.
2. Preserve mathematical meaning and notation from the excerpt exactly.
3. Keep markdown valid for MkDocs Material.
4. kind=admonition → output a valid admonition block using the item's type.
5. kind=section → output a heading only, at the level implied by h1/h2/h3.
6. kind=text → output regular markdown paragraph(s), no admonition wrapper.
7. Style reference files are for tone/structure only — do not copy facts from them.
8. Use \mathbb{R}, \mathbb{C} for complex numbers, real numbers.
9. Use $$...$$ (double $), for non-inline equations.
10. Number all admonitions, regardless of their types, by 2.1.1, 2.1.2, ... and put it into titles, such as Definition 2.1.5.
11. Create the titles of admonitions yourself, do not just copy the content of the blueprint.