# ADR-056 — Keep the source toolbar compact

Date: 2026-08-30. Status: accepted.

**Ruling**: the original-filing toolbar uses three tracks: a fixed title, one shrinkable navigation status, and a fixed table action. Optional table-verification output occupies its own row only when present.
**Because**: five peer elements with verbose copy compressed into narrow word columns on a MacBook Air. The heading-anchor hint repeated what the status already communicates.
**Enforced by**: `ui-source-toolbar-compact.json` pins the compact copy and grid contract; browser evidence verifies the rendered geometry at the narrowest side-by-side viewport.

---

## 2026-08-30 owner amendment

The Original Filing action track also keeps a checked **Sync scroll** control.
It maps scroll position within the selected item's verified source region and
disables itself with an explicit inactive label when the panes stack below
1001 px. This is a comparison convenience; selecting an item still navigates
by the filing's page/heading anchor. The Extracted header uses a separate
two-track toolbar: one ellipsized item label plus compact view state and a
non-wrapping `Full text` / `Preview` action. Status, confidence, method, and
region counts stay in the existing evidence disclosure instead of competing
for the header row.

**Enforced by**: `ui-extracted-toolbar-compact.json` and
`ui-split-breakpoint.json`, plus the localhost 1280 px / 900 px browser walk.

No extraction, anchoring, table-verification, or authentication behavior changes.
