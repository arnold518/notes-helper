# Map Rules — Edit freely, these are loaded at runtime

Mapping rules:
1. Read each item's excerpt to determine what it is called in the original textbook.
2. The excerpt header [filename line X~Y] shows the current reference name; use the reference name mapping to find the original file path.
3. Use the original file path as the section header in the mapping file: ## Reference: <original-path>
4. Find or create a row where New ref = the item's new ref label and Location = the notes output file.
5. Set Original ref to the item's identifier in the original text (e.g. "Theorem 2.3", "Definition 1", "Replacement Theorem", section title).
6. Surround the Original ref value with ** for bold.
7. If the excerpt has no identifiable original reference, omit the item from the map.
8. Preserve all existing rows — only add or update rows for the given items.
