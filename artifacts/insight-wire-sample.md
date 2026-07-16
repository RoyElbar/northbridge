# Artifact: the insight wire (append-only)

> Format exact. These are real, non-sensitive entries from the wire — the class of knowledge the system refuses to let die with the session that learned it.

**Mechanism:** one shell call appends a single line; every other agent receives
the delta in its next turn, and every *future* session inherits the full wire.
Append-only by design — history is evidence.

```text
[build]   PDF text extraction breaks phrases across rendered line-wraps —
          normalize whitespace before asserting content, or true claims fail the gate.
[infra]   grep/find over a cloud-synced directory silently miss files that are
          not hydrated locally — verification gates must run on guaranteed-local paths.
[render]  headless Chrome adds header/footer by default; --no-pdf-header-footer,
          and a one-page document must FAIL the build if it overflows (exit code, not a warning).
[agents]  a generator checking its own output inherits its own blind spots —
          adversarial verification only works from a fresh context.
[memory]  "update beats create": a new file for a fact that already has a home
          forks the truth. The write gate exists because this happened.
```

**Rule of thumb baked into every agent:** *the action goes to the board;
what the action taught you goes to the wire.* The board is ephemeral
coordination; the wire is permanent knowledge.
