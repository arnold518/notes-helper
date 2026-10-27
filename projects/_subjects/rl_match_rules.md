# Match Rules - Edit freely, these are loaded at runtime

Extraction rules:
1. Extract sentence-wise. Do NOT start or end a chunk in the middle of a sentence.
2. When $$...$$ math appears inside a sentence, include the full surrounding sentence.
3. Expand start/end lines as needed so each chunk contains complete sentences, complete display-math blocks, complete markdown tables, and complete fenced code blocks.
4. Keep text verbatim from the source - no paraphrasing.
5. If multiple chunks are needed for one item, include all of them in source order.
6. If a previous excerpt is provided, treat it as a hint only and re-extract from the current reference files; replace stale file names, line numbers, and chunk boundaries when needed.
7. For section headers, match only the relevant header line.

RL textbook-specific boundaries:
8. The Sutton-Barto RL textbook is mostly prose, equations, figures, and algorithm boxes rather than theorem-proof format. Match the complete conceptual unit, not just the first sentence that mentions a term.
9. For definition items, include the paragraph(s) that define the term, all defining equations, and the immediate "where..." or notation-explanation paragraph. Do not cut off a displayed equation or a list of cases.
10. For concept items, include the full contiguous explanation needed for the blueprint phrase. If the blueprint names several related pieces (for example "equation, intuition, gradient" or "Bellman equation, backup diagram"), include multiple chunks when the source separates those pieces.
11. For theorem-like items, include the named result, the complete equation or condition, and any proof, derivation, justification, or explanatory paragraph supplied by the source. RL often states results without a literal "Proof" label; in those cases include the surrounding argument that establishes the result.
12. For derivation items, include every displayed equation in the derivation sequence and the prose connecting the steps. Do not stop at the final equation if the source continues with a quotient-rule, expectation, baseline, or convergence explanation.
13. For algorithm items, include the algorithm title/heading, inputs, parameters, initialization, the entire pseudocode or fenced code block, and any short lead-in needed to identify the algorithm. Do not cut a code block, display-math pseudocode block, or loop body. If a blueprint item was parsed as kind=text but its content says "algorithm", apply this algorithm rule anyway.
14. For example items, include the complete numbered example or experiment description. If the item asks for results, a testbed, a comparison, or a backup diagram, include the relevant image line and Figure caption as well as the prose interpreting the figure.
15. For figure-backed concepts, include the figure image/caption when the figure is the evidence or named object in the blueprint item. If an image interrupts a sentence in the OCR text, expand the chunk so the sentence and caption are complete.
16. For update rules, returns, value functions, policies, Bellman equations, importance-sampling ratios, or backup diagrams, include all displayed formulas in the named group and their variable definitions. Do not omit equation tags present in the source.
17. Stop before exercises, summaries, bibliographical remarks, the next unrelated numbered example, the next unrelated algorithm box, or the next section heading unless the blueprint item explicitly asks for that material.

Output format for each excerpt file:
- Format each chunk as: [filename line X~Y]\n\n{verbatim text}
- Separate multiple chunks with: a blank line, then ---, then a blank line
- Write backslashes as-is (e.g. \pi, \begin{equation*}). Do not double-escape.
