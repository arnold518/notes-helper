# Match Rules - Edit freely, these are loaded at runtime

Extraction rules:
1. Extract sentence-wise. Do NOT start or end a chunk in the middle of a sentence.
2. When $$...$$ math appears inside a sentence, include the full surrounding sentence.
3. Expand start/end lines as needed so each chunk contains complete sentences.
4. Keep text verbatim from the source - no paraphrasing.
5. If multiple chunks are needed for one item, include all of them.
6. If a previous excerpt is provided, treat it as a hint only and re-extract from the current reference files; replace stale file names, line numbers, and chunk boundaries when needed.
7. For section headers, match only the relevant header.
8. For theorem-like items (Theorem, Corollary, Lemma, Proposition), include the complete statement and the complete proof whenever the source provides a proof. Do not stop at the theorem statement. Continue through the last sentence of the proof, including all displayed equations and proof paragraphs. A theorem-like excerpt that omits an available proof is invalid.
9. For examples, include the full example, including any Solution paragraph and all computations needed to finish the example. Do not stop at the first displayed equation or first conclusion if the example continues.
10. For definitions, include the full definition, including all numbered conditions, displayed equations, and immediately attached explanatory text that is part of the definition. Do not cut a displayed list or equation block.
11. For concept items, include the full contiguous explanation needed for the concept. Prefer complete neighboring paragraphs over a fragment that starts or ends mid-argument.
12. Stop before the next unrelated numbered item, section heading, exercise block, figure-only block, or historical/sidebar material unless the blueprint item explicitly asks for it.

Output format for each excerpt file:
- Format each chunk as: [filename line X~Y]\n\n{verbatim text}
- Separate multiple chunks with: a blank line, then ---, then a blank line
- Write backslashes as-is (e.g. \sigma, \begin{pmatrix}). Do not double-escape.
