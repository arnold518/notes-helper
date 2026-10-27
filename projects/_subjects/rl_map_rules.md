# Map Rules - Edit freely, these are loaded at runtime

Mapping rules:
1. Read each item's excerpt to determine what it is called in the original textbook.
2. The excerpt header [filename line X~Y] shows the current reference name; use the reference name mapping to find the original file path.
3. Use the original file path as the section header in the mapping file: ## Reference: <original-path>
4. Find or create a row where New ref = the item's new ref label and Location = the canonical notes output path (relative to MkDocs docs/ when available).
5. Set Original ref to one or more narrow, canonical source-side identifiers for the item itself.
6. Prefer explicit source-side labels when available: section title, Example number, Figure number, Exercise number, equation tag, algorithm title, or named result.
7. For algorithm boxes, use the exact algorithm title as an Original ref, for example **Sarsa (on-policy TD control)** or **n-step TD for estimating V**. Include a nearby equation tag only if the algorithm item is explicitly about that equation.
8. For figure-backed examples or testbed results, include the Figure identifier as an Original ref, and include the named experiment/result if it is the item's main target.
9. For concepts with no formal label, use the exact named concept from the source text, not a broad section title.
10. If an item has multiple equally canonical source-side identifiers, separate them with "; " in the Original ref cell.
11. Do not use dependencies, supporting mentions, or downstream references inside the excerpt as Original ref.
12. Do not try to encode exhaustive synonyms or alias variants in the mapping file; generation will do semantic search over canonical rows.
13. Surround each Original ref value with ** for bold.
14. If the excerpt has no identifiable original reference, omit the item from the map.
15. Preserve all existing rows - only add or update rows for the given items.
16. If the mapping table includes References and Referenced by columns, preserve them; the system maintains those columns separately.
