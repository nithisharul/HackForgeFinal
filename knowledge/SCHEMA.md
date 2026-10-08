# Second Brain schema

Every page is markdown with a small `key: value` header between `---` lines.
Pages link to each other with `[[PageName]]`; the name is the file name without `.md`.

## Page types
- `patterns/<pattern>.md`   one per FWA pattern: definition, detection signals, policy basis,
  known innocent explanations, lessons from closed cases, notes from sources, every closed case.
- `providers/<P###>.md`     one per investigated or networked provider: investigation history.
- `networks/<N##>.md`       one per detected provider network: members, shared ownership, cases.
- `cases/<id>.md`           one per closed case: verdict, reasoning, lesson, evidence summary.
- `sources/<SRC-###>.md`    one summary per raw document added to `knowledge/sources/documents/`.
- `notes/<NOTE-###>.md`     an answer to a question that a human chose to keep.
- `index.md`                catalog of all pages, read first on every query.
- `log.md`                  append-only record of every change, newest last.

## Rules
1. Raw files in `knowledge/sources/` are never edited.
2. Nothing is written without a named human approving the previewed change.
3. Blocks between `<!-- auto:... -->` and `<!-- /auto -->` are regenerated from other pages;
   edit anything outside them by hand.
4. Every case links to exactly one pattern and one provider. Every page is reachable from the index.
5. A cleared case adds its reasoning to the pattern's "Known innocent explanations".
6. Verdict values: `confirmed`, `cleared`, `inconclusive`.
7. The system proposes; it never states that fraud occurred. Wording is "flagged", "consistent with".
8. Text written by the LLM may only use IDs and dollar figures that appear in its input.
