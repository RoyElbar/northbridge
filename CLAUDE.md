# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Northbridge is a portfolio/architecture showcase of a private personal multi-agent AI system, "designed like a processor". The production system (27 agents, memory vault, coordination files) is private and lives elsewhere; this repo publishes only two real runnable scripts (`code/`), sanitized format artifacts (`artifacts/`), placeholder config templates (`templates/`), and the README with its SVG diagrams (`assets/`).

The LICENSE is viewing-only (all rights reserved, not open source). Do not copy code or text from this repo into other projects, and keep the repo's contents self-contained.

There is no build system, package manager config, test suite, linter, or CI. The two scripts are standalone entry points run directly with Python 3.11. "Testing" a change means running the script and checking its output/exit code.

## Commands

Dependencies are implicit (no requirements.txt): `sympy` (verifier), `pypdf` (document pipeline's one-page gate and `--append`), and a Chrome/Chromium binary for PDF rendering — auto-detected, or set `CHROME_PATH` (see `templates/env.example`).

```bash
# Render the included sample content -> code/document.html + code/document.pdf
python3.11 code/document_pipeline.py

# Deep-merge a variant over the core content and render a tailored PDF
python3.11 code/document_pipeline.py --variant variants/X.json --out out/document_X.pdf

# Dry run: render to a temp dir, report page count, touch no real output
python3.11 code/document_pipeline.py --check

# Verify a math claim: exit 0 = VERIFIED, 1 = REFUTED, 2 = UNCLEAR
python3.11 code/math_verifier.py "diff(sin(x**2), x)" "2*x*cos(x**2)"
```

## Architecture

The README's processor metaphor is the map: specialized agents = execution units, a live coordination board = bus + arbiter, layered markdown memory = caches, a verification unit = scoreboard/checker, a nightly maintenance loop = refresh. Each repo file is one exposed piece of that design:

- `code/math_verifier.py` — the mathematical core of the verification unit; `artifacts/agent-definition.md` is the agent contract that wraps it in production (least-privilege tools, hard rules, explicit output contract).
- `artifacts/coordination-board-sample.md` and `artifacts/insight-wire-sample.md` — the coordination formats: claim-before-write board entries (ephemeral) and an append-only insight wire (permanent). "The action goes to the board; what the action taught you goes to the wire."
- `templates/com.user.nightly-maintenance.template.plist` — launchd template for the nightly scan/classify job (only the provably-safe fix class is auto-applied).
- `code/document_pipeline.py` — the single-page document engine (renders the owner's CV): content JSON → `build_html()` → headless Chrome → PDF → pypdf page-count gate.

### document_pipeline.py invariants

These are deliberate design rules, not incidental code — preserve them when editing:

- **One page is a hard gate.** Overflow exits with code 2 ("cut content, not design"), never a warning. If pypdf is missing the gate can't run and the script says so loudly.
- **Content and design are separated.** The content file owns every word; the design is frozen in the single `CSS` constant. Content changes and design changes never travel in the same edit.
- **A stale PDF is never reported as fresh output** — the target PDF is deleted before rendering.
- **Only two markup forms are allowed in content strings:** `**text**` (emphasis, `.award` span) and `<m>text</m>` (muted, `.meta` span). Everything else is HTML-escaped by `esc()`.
- **Variant merge semantics** (`deep_merge`): dicts merge deep, lists and scalars replace whole, keys starting with `_` are skipped (usable as comments in variant files).

### math_verifier.py contract

The "generator never grades its own work" rule as code: re-derive the claim symbolically in a fresh process and answer with exactly one of three verdicts — `VERIFIED` / `REFUTED` / `UNCLEAR` (exit 0/1/2). Comparison is symbolic (`simplify(a - b) == 0`), solution lists compare as sets, and anything unparseable/uncomparable is `UNCLEAR`, never "probably fine". Callers treat any non-zero exit as "do not ship the claim". Don't add verdicts, and don't weaken UNCLEAR into a pass.

## Conventions

- **Nothing private enters the repo.** `templates/` holds placeholder-only values (`<ABSOLUTE_PATH_TO_VAULT>`, `__PLACEHOLDER__` style); `.env*` is gitignored with only `templates/env.example` allowed back in. Artifacts follow "format exact, content synthetic" — keep sample data clearly demo (`demo data`, synthetic session IDs).
- **Never commit render output.** `code/document.html` and `code/document.pdf` are gitignored.
- **README images come in light/dark pairs.** Every diagram in `assets/` has `-light.svg` and `-dark.svg` variants wired through `<picture>` elements in the README; a visual change must update both.
