# Artifact: live coordination board

> Format exact, content synthetic (`demo data`). Every concurrent session writes its entry **before** touching shared state, and reads everyone else's first. Read-before-write is the law of the board.

**Directory:** `$VAULT/live/` — one file per active session.

```markdown
# session 2026-01-15-0930-demo0001 — course-prep
🎯 WHAT: building tomorrow's practice sheet for the demo course (signals-101),
   worked-solutions + verification pass.
AREA CLAIMED: courses/signals-101/ — do not write here concurrently.
STATUS: extraction done · solving Q3 of 8 · all answers going through math-verifier.
```

```markdown
# session 2026-01-15-1105-demo0002 — app-build
🎯 WHAT: fixing the mobile reader's scroll-lock bug, then redeploy.
AREA CLAIMED: app/reader/ + deploy pipeline.
STATUS: root cause found (body scroll-lock lifecycle) · fix in test.
NOTE: saw courses/signals-101/ is claimed by 0930-session → staying clear.
```

**The collision rule:** an area claimed by another live session means *coordinate,
not clobber* — the second writer either waits, hands off, or negotiates via a
board note. Same discipline as a bus arbiter: whoever holds the grant owns the
bus; everyone else queues.

**Lifecycle:** entries update at every meaningful state change and close with the
session. A stale entry (session died) is detected by the nightly maintenance
loop and demoted — never silently deleted.
