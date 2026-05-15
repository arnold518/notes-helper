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
