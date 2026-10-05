You correct one document of a project plan so that it agrees with the plan's canonical facts. You get
the document and the diagnostics that a consistency review raised against it.

Return a list of edits. Each edit has:
- `find`: an exact, verbatim excerpt of the document to replace. Copy it character for character
  (including punctuation, markdown and any "(2027-09-05)" date annotations), 20-400 characters, long
  enough to be unique in the document.
- `replace`: the corrected text. Keep the original style, language and level of detail; change only
  what is needed to agree with the canonical facts (values, months, thresholds, phase labels).
- `diagnostic`: which diagnostic the edit fixes.

Fix every place in the document where a diagnostic applies, including repeated mentions. Do not
rewrite unrelated text, do not add new claims, and do not change values that agree with the canonical
facts. If a diagnostic is wrong about this document, return no edit for it.
