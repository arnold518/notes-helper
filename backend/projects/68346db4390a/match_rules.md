# Match Rules — Edit freely, these are loaded at runtime

Extraction rules:
1. Extract sentence-wise. Do NOT start or end a chunk in the middle of a sentence.
2. When $$...$$ math appears inside a sentence, include the full surrounding sentence.
3. Expand start/end lines as needed so each chunk contains complete sentences.
4. Keep text verbatim from the source — no paraphrasing.
5. If multiple chunks are needed for one item, include all of them.
6. If a current excerpt is provided, build on it — add, remove, or replace chunks as instructed.
7. For section headers, match only the relevant header.

Output format for each excerpt file:
- Format each chunk as: [filename line X~Y]\n\n{verbatim text}
- Separate multiple chunks with: a blank line, then ---, then a blank line
- Write backslashes as-is (e.g. \sigma, \begin{pmatrix}). Do not double-escape.
