# ADR-056 — Keep the source toolbar compact

Date: 2026-08-30. Status: accepted.

**Ruling**: the original-filing toolbar uses three tracks: a fixed title, one shrinkable navigation status, and a fixed table action. Optional table-verification output occupies its own row only when present.
**Because**: five peer elements with verbose copy compressed into narrow word columns on a MacBook Air. The heading-anchor hint repeated what the status already communicates.
**Enforced by**: `ui-source-toolbar-compact.json` pins the compact copy and grid contract; browser evidence verifies the rendered geometry at the narrowest side-by-side viewport.

---

No extraction, anchoring, table-verification, or authentication behavior changes.
