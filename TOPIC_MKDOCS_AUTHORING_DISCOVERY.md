# Topic-to-MkDocs AI Authoring: Discovery Findings

Date: 2026-08-09

Status: discovery only. This document records what the existing systems and writing corpus imply. It deliberately does not choose an implementation or define an implementation plan yet.

## 1. Executive conclusion

The proposed tool should not be understood as a generic summarizer that converts a pile of text into Markdown.

The stronger product idea is an **evidence-aware technical coauthoring workspace**:

1. The user supplies a topic, a rough sketch, and editorial intent.
2. The workspace accepts heterogeneous source material: papers, exact excerpts, ChatGPT records, local notes, code, and web pages or saved HTML.
3. The AI helps organize the sketch, identifies useful evidence, exposes gaps or conflicts, and expands the material into a coherent article.
4. The output follows a selected local MkDocs writing profile rather than a universal template.
5. The user reviews source use, prose, equations, code, assets, and structure before publication.
6. A final quality pass checks the actual MkDocs result, not only the Markdown text.

The existing `notes-helper` is a useful starting point because it already has project state, source viewing, AI-assisted editing, per-item review, a rendered MkDocs preview, project chat, logs, cross-reference maintenance, and export. Its current conceptual model is narrower, however: it is optimized for turning exact excerpts from local Markdown textbooks into individually generated semantic blocks. A publication-ready multi-source article requires source provenance, article-wide reasoning, richer draft units, multiple output profiles, and stronger final quality control.

The most important design decision is therefore not initially “frontend/backend or Codex skill?” It is the **authoring and evidence contract** that both forms would need to implement.

## 2. Scope and evidence boundary

I inspected the live working trees, not only their committed `HEAD` versions:

| Repository | Branch / `HEAD` | Working-tree state at inspection | Why it matters |
| --- | --- | --- | --- |
| `notes-helper` | `init` / `3bd4351` | 30 tracked changes, 15 untracked entries | The live implementation contains substantial work beyond `HEAD`; it is the relevant architecture snapshot. |
| `ps-notes` | `main` / `0b0c989` | 2 tracked changes, 3 untracked entries | Some contest material is in progress and should not automatically become a style exemplar. |
| `math-notes` | `main` / `7b64410a` | 6 tracked changes, 20 untracked entries, including 3 deletions | The linear-algebra corpus is mature, while much of the current abstract-algebra material is generated or under active revision. |
| `cs-notes` | `main` / `3a5447b` | 9 tracked changes, 10 untracked entries | The requested paper reviews are modified, and `qcqi/` is currently untracked; these are useful live artifacts, not all confirmed committed publication state. |

No files in the three note repositories were changed during this discovery.

The principal examples reviewed were:

- `cs-notes/docs/paper-review/1.md`
- `cs-notes/docs/paper-review/5.md`
- the nonempty pages under `cs-notes/docs/qcqi/`
- all numbered pages under `math-notes/docs/linear-algebra/`
- the article, idea, solution, study, and contest-post pages under `ps-notes/docs/`
- each repository's `mkdocs.yml`, custom CSS, navigation, and asset conventions
- the current `notes-helper` backend, frontend, tests, persisted subjects/projects, prompts, preview path, and export path

“Publication-ready” below is inferred from the strongest pages and repeated conventions. It does not mean every page in every inspected directory is complete or error-free.

## 3. What “MkDocs blog format” means here

None of the three note sites currently enables the MkDocs Material `blog` plugin. “Blog” in this project therefore means a polished documentation/article page published through MkDocs Material, not a date-indexed Material blog post with blog-plugin metadata.

### 3.1 Shared rendering contract

The repositories have a common technical base:

- MkDocs Material
- MathJax through `pymdownx.arithmatex`
- syntax highlighting and fenced code
- tables, attribute lists, Markdown-in-HTML, and captions
- `pymdownx.superfences`
- Material admonitions and collapsible details
- a repository-specific `extra.css`
- relative page assets such as `./assets/5.1.jpg`
- the search and tags plugins

This common base is important: the authoring tool can share a Markdown/rendering core while still supporting different editorial profiles.

### 3.2 The corpus contains several distinct article profiles

| Profile | Strong examples | Characteristic structure | Important semantic blocks |
| --- | --- | --- | --- |
| Paper review / technical synthesis | `paper-review/1.md`, `paper-review/5.md` | Sources first, conceptual narrative, equations and diagrams, model or method details, implementation, experiments, interpretation | `definition`, `concept`, `code`, figures, captions, internal references |
| Formal textbook notes | `qcqi/*.md`, `linear-algebra/*.md` | Numbered sections, tightly sequenced definitions/theorems/proofs/examples/exercises, explicit internal cross-references | `definition`, `theorem`, `corollary`, `proof`, `example`, `exercise`, `concept` |
| Algorithm / data-structure article | pages such as Segment Tree Beats and Potential Method in `ps-notes` | Motivation or problem, formal properties, proof, algorithm, complexity, implementation, references | `definition`, `property`, `proof`, `algorithm`, `complexity`, `observation` |
| Problem solution | `ps-notes` solution pages | Problem links and constraints, key observations, staged reasoning, checkpoints, complexity, code | `observation`, `checkpoint`, `inout`, `failure`, `question`, code |
| Contest study log / post | `ps-notes` study and post pages | Lightweight sections per problem, compressed insights, links, and partial follow-up notes | Headings, short prose, code, occasional semantic blocks |

These should be profiles, not one hard-coded shape. For example, `ps-notes` pages usually have YAML front matter with `title` and `tags`; the inspected paper-review, QCQI, and linear-algebra pages do not. A tool that always adds or always omits front matter would be wrong for part of the corpus.

### 3.3 Repository-specific semantic vocabulary

The custom admonition types form a local authoring language:

- `ps-notes`: `algorithm`, `checkpoint`, `complexity`, `definition`, `inout`, `observation`, `proof`, and `property`
- `math-notes`: `concept`, `definition`, `example`, `exercise`, `proof`, and `theorem`, alongside related standard blocks such as corollaries
- `cs-notes`: `algorithm`, `code`, `concept`, `definition`, `example`, `proof`, and `theorem`

The CSS is not just visual decoration. The block type communicates the role of the content. Selecting the right type is part of organizing the reasoning.

## 4. What the strongest finished writing actually does

### 4.1 Paper reviews are synthesized articles, not extract summaries

The two specified paper reviews together contain roughly 8,000 words, 28 headings, 18 image references, many semantic definition/concept/code blocks, equations, and executable-looking implementation material.

Their recurring shape is:

1. Identify papers and supporting blogs.
2. Establish the concepts and notation needed by the reader.
3. Explain the mechanism step by step with math and diagrams.
4. Relate components into a complete architecture or algorithm.
5. Show an implementation.
6. Report experiments or results.
7. Interpret those results in the author's own narrative.

This is a major requirement for the proposed tool. A good page is not a list of source summaries. It reorganizes source material around a pedagogical argument.

The reviews also mix different epistemic roles:

- sourced facts and definitions
- derivations or explanatory restatements
- code written or adapted by the author
- experimental observations
- interpretation and judgment

A future data model should preserve these distinctions instead of placing all prose in a single undifferentiated generated field.

The pages identify their principal papers and blogs near the beginning, but they do not retain a visible claim-by-claim evidence trail. That presentation can remain a valid publication style while the authoring workspace keeps finer provenance internally.

### 4.2 Formal notes optimize for preservation and internal consistency

The inspected linear-algebra corpus is large: 28 numbered pages, about 80,000 words, more than 100 definitions, more than 180 theorem/corollary blocks, more than 200 exercises, and extensive nested proofs and internal references.

Its stable conventions include:

- page titles shaped like `# § N. Title`
- meaningful section headings
- precise numbering of semantic blocks
- theorem/definition/exercise references treated as first-class content
- display-math spacing rules
- four-space indentation inside admonitions and nested proofs
- relative, centered figures
- preservation of the source author's wording, context, and sequence

The local `linear-algebra/AGENTS.md` makes preservation explicit: do not delete source content, keep proof/admonition structure valid, and maintain mappings when numbering changes.

QCQI has a similar formal character but is even denser in definitions, theorems, equations, and nested proofs. This is close to the workflow that `notes-helper` currently supports best.

### 4.3 PS articles make reasoning structure visible

Across 41 nonempty PS article files, the corpus contains approximately 42,000 words, 300 headings, 50 images, and a broad range of code and semantic blocks.

The strongest pages externalize the thinking process:

- an `observation` isolates a useful fact
- a `property` states a reusable invariant
- a `proof` establishes why it holds
- an `algorithm` turns the fact into steps
- a `complexity` block records cost
- a `checkpoint` verifies that the reasoning is still on track
- a `failure` or `question` can preserve an unresolved path

This suggests a valuable organizing function for the AI: it should not merely make prose longer. It should help classify each idea by its role in the argument.

Most of the PS explanatory prose is Korean, with English mathematical and programming terms mixed in naturally. Language and terminology behavior are therefore part of the profile, not a global formatting choice.

The PS corpus also contains short, unfinished, or scratchpad-like pages. Style retrieval must use an explicitly curated set or a quality signal; blindly sampling nearby pages could teach the AI incomplete structure.

## 5. Inferred publication-ready contract

A generated page should satisfy all of the following, with the exact mix depending on its profile.

### 5.1 Editorial intent remains authoritative

The user's sketch should be the governing expression of scope, emphasis, ordering, and personal interpretation. The AI may propose structure, identify omissions, and improve the explanation, but it should make changes to the user's thesis visible rather than silently replacing it.

### 5.2 Every factual contribution has recoverable evidence

The system should retain:

- which source supports a claim or block
- the exact source span where possible
- a stable locator such as page, section, line range, timestamp, or URL fragment
- the difference between exact quotation, paraphrase, inference, and user-authored interpretation
- the source version or snapshot used during generation

The final page does not necessarily need a citation marker after every sentence. The authoring workspace still needs claim-to-source traceability so the user can audit the draft and choose the visible citation style.

### 5.3 The article has a coherent whole-page argument

Per-section drafting is useful for review, but a publication pass must also check:

- definitions appear before use
- notation is consistent
- repeated explanations are consolidated
- transitions explain why the next section follows
- the introduction promises what the article actually delivers
- results are separated from their interpretation
- conclusions do not overstate the supplied evidence

### 5.4 Technical material remains valid

Equations, code, tables, admonition indentation, figure paths, captions, and cross-references are content, not formatting trivia. They must survive editing and render under the target repository's actual MkDocs configuration.

### 5.5 Source transparency and prose quality are separate checks

A sentence can be well written but unsupported. It can also be perfectly sourced but poorly integrated. The review workflow should expose both axes.

### 5.6 “Done” includes rendered and repository-level quality

Publication readiness should include at least:

- successful target-profile rendering
- broken asset and link detection
- valid admonition nesting and math formatting
- unique and consistent semantic-block numbering where numbering is used
- valid internal references
- citation/source coverage review
- spelling and terminology consistency
- no unresolved placeholders unless intentionally published
- explicit user approval of the version being exported

## 6. What `notes-helper` currently does

The existing README accurately describes a five-stage workflow:

```text
blueprint + local reference Markdown
        ↓
AI matches exact excerpts to blueprint items
        ↓
user reviews or edits excerpts
        ↓
AI generates one MkDocs block per item
        ↓
user approves items and exports the concatenated page
```

### 6.1 Current project model

The central `Project` contains a subject, title, output and blueprint paths, references, ordered items, and numbering metadata. Each `Item` has:

- a kind: `admonition`, `section`, or `text`
- an intent in `content`
- one combined `excerpt` string
- one generated `document` string
- a status: `pending`, `matched`, `generated`, or `approved`
- optional numbering and internal item references

The backend explicitly treats `projects/<id>/project.json`, especially each `item.document`, as canonical. Preview output, stage files, distribution output, and logs are derived artifacts.

This separation is sound and should be retained in any future design.

### 6.2 Current AI stages

The main agents are specialized:

- **Match** rereads local reference files and extracts exact, line-addressed evidence for one outline item.
- **Generate** treats the selected excerpt as the factual source and produces one valid MkDocs section or admonition, optionally learning local style from nearby numeric Markdown pages.
- **Edit** revises an excerpt or generated document from a user instruction.
- **Prepare** can extract and clean a section from a large local reference document.
- **Project AI chat** can inspect the workspace and make broader project changes, with a persistent conversation and changed-file reporting.

Bulk operations use parallel workers and per-item stage files. This is useful for throughput, but the default unit of thought is still an isolated item.

### 6.3 Current frontend workflow

The React frontend provides:

- subjects and per-subject MkDocs settings
- project creation from a blueprint and output path
- a three-pane item editor
- item navigation and approval controls
- exact line selection from local references
- editable excerpt and generated-document panels
- Match All and Generate All operations
- AI chat and detailed logs
- mapping and reverse-reference synchronization
- a final assembled view and direct export

This is already a substantial human-in-the-loop surface. It is particularly strong for reviewing many structured blocks without losing the original source.

### 6.4 Preview behavior is a reusable strength

The preview does more than run a generic Markdown renderer. It derives a synthetic build from the target `mkdocs.yml`, keeps the document at its source-relative path, merges site-wide assets with document-local assets, and serves the resulting MkDocs HTML. That is the right general direction because relative images and custom CSS can appear correct in a Markdown editor while failing in the real site layout.

## 7. What can be reused and what is too narrow

### 7.1 Strong reusable foundations

- subject-specific target repository and MkDocs configuration
- canonical persisted project state
- local reference copying and side-by-side source selection
- per-unit intent, evidence, draft, status, and approval concepts
- AI activity logs and persistent project conversation
- editable stage outputs rather than opaque one-shot generation
- source-relative, target-style MkDocs preview
- custom admonition discovery from repository CSS
- style-example injection as a concept
- internal reference graphs and mapping synchronization
- import of an existing Markdown page for continued editing
- final assembled view and explicit export

### 7.2 Current limitations for the proposed goal

#### Source ingestion

- A reference is essentially a local Markdown file.
- There is no first-class paper/PDF, pasted excerpt, chat transcript, URL, fetched HTML, local code, or image source type.
- There is no original-versus-normalized source distinction.
- There is no source snapshot hash, access date, bibliographic record, or ingestion history.

#### Evidence and provenance

- One `excerpt` string collapses all evidence for an item.
- Line annotations are embedded in text rather than represented as structured evidence spans.
- There is no claim-level connection to sources.
- Style examples and factual sources are not modeled as fundamentally different roles.
- An imported mature page can become `approved` even though it has no retained evidence lineage.

#### Authoring model

- The blueprint parser supports headings and a simple `- prefix : intent` list.
- Draft units are optimized for one semantic block, not a flexible paragraph, figure, code experiment, bibliography entry, or multi-block section.
- Generation is intentionally constrained to the matched excerpt as its only factual source. That is safe for textbook transcription but too restrictive for multi-source synthesis.
- There is no explicit article thesis, audience, desired depth, open question, or author interpretation field.
- There is no dedicated article-wide coherence or editorial pass.

#### Review state

- Approval is sticky: editing an approved item does not automatically invalidate that approval.
- The approval does not identify the exact evidence and draft versions that were approved.
- Background job state is held in memory rather than a durable job record.

#### Style selection

- Automatic examples are chosen from nearby numeric `.md` files.
- This happens to fit linear algebra and QCQI better than PS filenames such as `algorithm.md`, `idea.md`, `solution.md`, and `post.md`.
- Proximity is not a quality signal and can select an unfinished neighbor.

#### Safety boundary

- The configured Codex execution path currently uses a sandbox-bypass flag.
- The file API accepts broad filesystem paths and does not itself show a project-root authorization boundary.
- Adding untrusted HTML, web content, or chat logs would introduce prompt-injection and content-trust concerns beyond the current local-reference workflow.

These are not reasons to discard the application. They identify the contracts that must be tightened before expanding its input surface.

## 8. Inferred target authoring workflow

This is a workflow finding, not an implementation sequence.

### 8.1 Establish the article brief

The user provides:

- topic and working title
- rough sketch or current entry
- intended audience and assumed background
- desired article profile
- what the article should explain or argue
- desired depth, length, and completion boundary
- target MkDocs subject/repository

The original sketch should remain visible throughout the project.

### 8.2 Ingest and preserve sources

Each source is stored in its original form when possible and gets a normalized, searchable representation. Possible source types include:

- paper metadata plus local PDF or extracted text
- pasted exact excerpt
- ChatGPT or other conversation transcript
- URL plus a saved HTML/text snapshot
- external blog article
- local Markdown note
- code file, output log, or experiment result
- user-authored note or claim
- image or diagram with origin and caption notes

Normalization must not erase where the content came from.

### 8.3 Build an evidence workspace

The user and AI create evidence cards or spans that record:

- exact source location
- selected text or object
- a short interpretation
- which article questions it may answer
- agreement, conflict, uncertainty, or missing context
- whether it is factual evidence, style inspiration, user opinion, or experimental output

This makes “organize the topic” a visible stage rather than an invisible side effect of prompting.

### 8.4 Develop the sketch into an outline

The AI can propose:

- grouping related notes
- prerequisite definitions
- a pedagogical ordering
- missing evidence or unanswered questions
- where a diagram, proof, example, code listing, or experiment is needed
- which material should be omitted as off-scope

Changes from the user's original organization should be presented as proposals. The user decides the outline that governs drafting.

### 8.5 Draft with evidence attached

Each draft unit should know its intent and supporting evidence. The unit may be a paragraph, semantic block, subsection, figure, code block, or bibliography entry—not only an admonition.

The UI or workflow should allow the user to compare:

```text
intent / user sketch
        ↕
supporting evidence and source locations
        ↕
current draft and AI revision history
        ↕
rendered MkDocs result
```

### 8.6 Perform an article-wide synthesis pass

After local drafting, the system checks the entire article for ordering, transitions, terminology, notation, duplication, unsupported conclusions, and consistent cross-references. This pass should propose changes without destroying individually approved technical content.

### 8.7 Validate and publish deliberately

The target repository profile determines front matter, navigation expectations, semantic types, math rules, asset paths, citation form, and build checks. The exact draft version and evidence state are approved before export. Export should not be confused with publication or Git delivery unless the user explicitly requests those later operations.

## 9. Data concepts implied by the workflow

The following are conceptual requirements, not a finalized schema.

### 9.1 Source

A source needs at least:

- type
- title and origin
- author/publication metadata when applicable
- original artifact or stable link
- local snapshot or normalized representation
- retrieval/access time for web material
- content fingerprint/version
- citation metadata
- trust and usage notes

### 9.2 Evidence span

An evidence span should be a structured object rather than text embedded in an excerpt:

- source identifier
- locator: page, line range, section, timestamp, DOM fragment, or code lines
- exact selected material
- optional normalization
- user annotation
- intended role in the article
- quotation/paraphrase/inference classification

### 9.3 Draft unit

A draft unit needs:

- type and semantic role
- user intent
- user-authored seed text
- linked evidence spans
- generated or edited draft
- article position and dependencies
- version and approval state
- visible and internal references

### 9.4 Article-level state

The project also needs whole-page concepts that do not belong to one block:

- thesis and scope
- audience and prerequisites
- outline versions
- terminology and notation registry
- bibliography/source policy
- unresolved questions
- selected style profile and curated exemplars
- whole-page review results

## 10. Architectural forms to discuss later

No option is selected here. All of them must satisfy the same provenance and authoring contract.

| Form | Natural strengths | Natural weaknesses for this goal |
| --- | --- | --- |
| Extend the current frontend/backend | Best fit for persistent sources, side-by-side evidence review, structured approval, long-running projects, actual rendered preview, and visible job history | Requires meaningful schema, ingestion, security, migration, and UI work; can become complex if all reasoning is embedded in endpoints and prompts |
| Codex skill | Fastest way to encode a focused, repo-native authoring protocol; easy to invoke while working directly in a notes repository; can package instructions, references, assets, and helper scripts | Weaker by itself for persistent multi-source state, fine-grained evidence review, visual comparison, durable approval, and a source library |
| Hybrid application plus skill | The application can own sources, provenance, state, and preview while a skill provides a reusable authoring/review protocol that also works directly in a repository | Requires a clear ownership boundary so the app and skill do not develop two conflicting sources of truth |
| Shared core plus CLI, used by either surface | Makes ingestion, validation, profile rules, and provenance reusable and testable; keeps a future UI and skill aligned | Adds an abstraction boundary early and still needs one primary user experience |

Official Codex guidance describes a skill as a directory containing `SKILL.md` plus optional scripts, references, and assets; skills can be invoked explicitly or selected from their description. It also recommends keeping a skill focused on one job and using deterministic scripts where repeatability matters. This makes a skill plausible for an authoring protocol or validation workflow, but the guidance does not provide the persistent review workspace required by this idea on its own. Source: [OpenAI, “Build skills”](https://learn.chatgpt.com/docs/build-skills).

## 11. Questions that should drive the later plan

### 11.1 Editorial product

- Which profile should be the first complete use case: paper review, formal study note, PS algorithm article, or a new general-topic article?
- Should the AI preserve the user's heading order unless asked, or may it freely propose a new argument?
- How should user-written prose be marked so an AI revision cannot silently replace the author's voice?
- Is Korean, English, or mixed-language writing required in the first version?

### 11.2 Source and evidence policy

- Must every generated factual paragraph have attached evidence, or only claims selected as important?
- What visible citation style should each profile use?
- Should web pages be stored as snapshots for reproducibility, and for how long?
- How should paywalled, copyrighted, dynamic, or login-only sources be handled?
- Should ChatGPT transcripts be treated as evidence, brainstorming context, or both?
- When two sources disagree, should the draft stop for a user decision or present the disagreement?

### 11.3 Drafting and review

- What is the smallest useful review unit: paragraph, semantic block, subsection, or section?
- Should article-wide AI edits be allowed to touch approved units?
- What exact change invalidates approval: draft text, evidence, outline position, terminology, or any dependency?
- Should the system show a sentence-to-source coverage view?
- How much autonomous source discovery is desired, as distinct from reading user-supplied sources?

### 11.4 MkDocs integration

- Should profiles live in the target repository, in `notes-helper`, or in a portable skill/core package?
- Is automatic `mkdocs.yml` navigation editing in scope, or only page export?
- Should assets be copied into the target page directory automatically?
- Is a successful non-strict build enough, or must publication pass strict mode after repository warnings are fixed?
- Should bibliography entries, tags, titles, numbering, and block types be suggested or enforced?

### 11.5 Product surface and safety

- Is the primary experience a dedicated long-running workspace or direct editing inside Codex?
- Which state must survive restarts and be auditable later?
- May the system fetch arbitrary URLs, or must the user explicitly approve each network source?
- How should untrusted page text be isolated from agent instructions?
- What filesystem roots may an agent read and write?

## 12. Findings that should shape planning priority

1. **Define the evidence model before choosing the UI.** A frontend, skill, and CLI all fail in the same way if multi-source provenance is reduced to one excerpt string.
2. **Select one article profile for an end-to-end first milestone.** The shared Markdown base is real, but the editorial contracts differ substantially.
3. **Keep factual sources separate from style exemplars.** A polished neighboring page can teach form but must never silently become evidence.
4. **Treat the user sketch as versioned source material.** The proposed value is flourishing the user's entry, not replacing it with an unrelated AI outline.
5. **Make article-wide coherence explicit.** Parallel item generation is useful, but it cannot by itself produce the strongest paper-review narrative.
6. **Preserve the real MkDocs preview early.** Rendering correctness is already a hard-won strength of `notes-helper`.
7. **Version approval against both draft and evidence.** “Approved” should not survive a material edit invisibly.
8. **Curate profiles and examples.** Directory proximity and numeric filenames are not sufficient quality controls.
9. **Add untrusted-source boundaries before web ingestion.** The current local, trusted-source assumptions should not be carried over implicitly.
10. **Define publication quality as a checkable state.** Build success, asset integrity, evidence coverage, internal consistency, and user approval should be observable rather than prompt aspirations.

## 13. Validation and quality observations

### 13.1 Existing `notes-helper` baseline

The current Python test suite passes under the available system Python:

```text
26 passed in 2.93s
```

The backend virtual environment does not include `pytest`, so invoking the suite through `backend/.venv/bin/python` fails with `No module named pytest`. This is an environment/dependency observation, not a test failure.

### 13.2 MkDocs builds

Non-strict builds of all three note sites produced rendered HTML in isolated `/tmp` site directories. Strict builds were blocked by the repositories' current deprecated Material tags configuration (`tags_file`), before page-specific strict validation could complete.

The non-strict builds also exposed repository-level warnings, including pages omitted from navigation and missing navigation targets. These should not all be attributed to the example pages.

### 13.3 Example pages are strong but still benefit from a final gate

Concrete observations from the live checkout include:

- `paper-review/1.md` references `./assets/1.1.png`, which is absent; the other referenced `1.*` images are present.
- The paper reviews contain a small number of visible spelling errors, such as `orignal`, `occuring`, `Defintion`, and `casual masking` where “causal” is intended.
- QCQI contains at least one literal escaped `\n` sequence inside displayed mathematical material, which is a rendering/content defect.
- Numbered formal notes make duplicate or inconsistent semantic numbering especially costly and worth validating mechanically.
- Some PS pages are intentionally light, incomplete, or scratchpad-like and should not be selected automatically as publication-style examples.

These do not undermine the selected pages as design exemplars. They demonstrate why publication readiness needs deterministic checks in addition to a writing prompt.

## 14. Overall interpretation

The current system already embodies a valuable idea: AI writing should be decomposed into evidence selection, draft generation, human review, real rendering, and explicit export. The new goal extends that idea from **structured textbook transcription** to **multi-source technical authorship**.

The extension is substantial but coherent. It asks the tool to manage four things at once:

```text
user intent
    + source provenance
    + article reasoning
    + repository-specific publication rules
```

If one of these is missing, the result will fall short:

- no user intent → generic AI article
- no provenance → fluent but unauditable synthesis
- no article reasoning → disconnected block summaries
- no repository profile → Markdown that does not match the actual notes sites

The later planning discussion should therefore begin by selecting the first article profile and agreeing on the source/evidence contract. Only then will the frontend/backend, skill, hybrid, or shared-core choice be concrete enough to evaluate responsibly.
