# ADR-049 — cover-first inspector navigation

Date: 2026-08-29. Status: accepted.

**Ruling**: derive bounded `front_matter` before the first item and select it after extraction; item selection either names its resolved source jump, reports a span-less status, or stays honestly `unanchored`.
**Because**: cover-derived form/date and opening text existed, but the UI hid them behind a manual item click and cleared the only success signal after a jump.
**Enforced by**: `ui-cover-navigation.json` runs the shipped view and JavaScript behavior; the existing `ui-anchor-contract` cases still decide whether a heading is safe to use.

---

No envelope span moves. `front_matter` is a web-view projection capped by the
existing display limit, not a new extracted item or output-contract field.
