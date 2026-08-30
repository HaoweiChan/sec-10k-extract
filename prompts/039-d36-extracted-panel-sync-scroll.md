# D36 — compact Extracted panel and restore Sync scroll

## Owner request

The attached inspector screenshot showed the Extracted panel header crowded by
a long verified-evidence title, Markdown/boilerplate diagnostics, and a tall
wrapping full-text button. The owner asked to tidy that UI and explicitly keep
a checkable Sync scroll control in Original Filing.

## Decision and outcome

Use the existing layout and synchronization code rather than add a component or
dependency. The Extracted header now has two tracks: an ellipsized item label
and a compact action group. Its full-text control is `Full text` / `Preview` and
cannot wrap; detailed status, confidence, method, and region counts moved into
the existing collapsed provenance disclosure. Original Filing again contains
a checked Sync scroll checkbox. Side-by-side panes map proportionally within
the selected verified source region; stacked panes keep the checkbox visible
but disabled and explain why. Page/heading anchors remain the authority for
item selection.

The D27 static prohibition on proportional sync is superseded only for this
opt-in comparison control; no extraction offsets, evidence, or source anchors
changed. Red-first coverage is `ui-extracted-toolbar-compact.json`.

## Owner follow-up — comparison note

The owner questioned the 102-word boilerplate comparison panel. The note stays
because an unexplained difference between side-by-side panes looks like an
extraction defect, but its implementation details do not. It is reduced to 22
plain-language words: Extracted hides headers/page numbers and may use Markdown;
Original Filing stays unchanged, so alignment may differ. `ui-exclusion-note`
now caps the visible note at 30 words.
