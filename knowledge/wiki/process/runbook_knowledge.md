---
type: process
id: runbook_knowledge
title: Runbook: adding and approving knowledge
written_by: code
---
# Runbook: adding and approving knowledge

> Reference page written by code from the pipeline. Rebuilt on every change; do not edit by hand.

## Purpose
How new knowledge enters the Second Brain and who may approve it.

## Three ways in
- **A verdict** on a case: see [[runbook_verdict]].
- **A source document** (policy, bulletin, audit memo): the LLM summarises it and proposes notes for the patterns it affects. If it describes a scheme not in the library, the LLM proposes a new pattern; the approver creates it, adds it to an existing pattern, or saves the document only.
- **A kept answer**: a good answer to a question is saved as a note page.

## Controls
- Nothing is saved without a preview and a named approver.
- Raw documents are stored unedited in `knowledge/sources/documents/`.
- A document can add notes and patterns. It cannot change a verdict, a score or a rule.
- A pattern learned from a document is marked knowledge only until a detection rule is written.
- Every change is recorded in [[log]]. The health check reports broken links, orphan pages, patterns that are mostly cleared, and data columns with no definition.
- Limits of the system: [[system_limits]].
