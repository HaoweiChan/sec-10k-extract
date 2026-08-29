# ADR-048 — Same-accession external Annual Report evidence

Date: 2026-08-29. Status: accepted.

**Ruling**: D24 extends the existing three-turn agent loop to verified Annual Report evidence in another document of the validated source accession, without moving primary offsets or coverage.
**Because**: MRK FY1995 and PGR FY2023 Items 7/8 are honest primary pointer spans whose substantive evidence is a same-accession EX-13 attachment.
**Enforced by**: the two burned adversarial cases, `envelope_shape`, the SEC accession allowlist, and the inspector's explicit document-scoped offset label.

---

## Context

Some valid 10-K item spans are deliberately short because the filing incorporates
an Annual Report attachment. MRK FY1995 and PGR FY2023 Items 7 and 8 are this
shape. Their primary spans are honest pointer text; the evidence lives in another
document in the same SEC accession. Replacing those spans with attachment offsets
would make the envelope's offset universe and coverage false.

## Decision

The existing three-turn agent loop gains a filing-package scope. Entry requires
both an existing item-level `item_span_near_empty` warning and a deterministic
pointer span naming an external Annual Report, plus an available candidate in the
same accession. An internal pointer, clean item, absent attachment, unmanifested
upload, or deterministically resolved cross-reference does not enter this route.

The deterministic acquisition boundary is the validated accession directory
under `https://www.sec.gov/Archives/`. It may enumerate that directory or SGML
`<DOCUMENT>` blocks already present in the supplied full submission. Each fetched
document is byte-capped, content-addressed, and cached. Redirects or identities
outside the accession are refused. No arbitrary origin, PDF/OCR path, or generated
content is available to the model.

The existing model, cache, `Budget`, persistent targets/outline, and three-turn
bound remain. The added actions are: list same-accession documents; bounded
document search/read; and propose external regions scoped to one listed document.
Each region must pass identity, hash, integer bounds, and title-or-pointer-page
proof. Rejection becomes the next turn's observation. Exhaustion retains the
primary result and review warning.

Accepted evidence is published under the target item's
`evidence.external_regions`. It preserves the primary pointer span and carries
document id/type/sequence/filename, SEC URL or SGML-block identity, raw and
normalized SHA-256, document-scoped offsets, and verifier decisions. Attachment
offsets never enter `/normalized_text`, item `start`/`end`, or `meta.coverage`.
The routing record names externally resolved items separately from primary-span
repairs and records acquisition plus model calls/tokens/USD/latency without a
credential.

## Consequences

Default extraction snapshots stay unchanged. Offline gates use cached transport
replays and local SGML/attachment fixtures, never network or an API key. The two
held-out outcomes that shaped this decision are burned as `input-variant` cases,
moved to adversarial with their fixtures, and replaced later under TD-167.

## PR83 round 1 amendment

Fresh review exposed three gaps in the first implementation. Title proof had
shown only that some title occurred near the proposed start, not that it named
the requested item or proved the region's end. It now reuses the canonical SEC
item title taxonomy and requires the next canonical section boundary or document
end; pointer-page proof remains a separate valid route. Embedded SGML extraction
now slices the original bytes before decoding, so `raw_sha256` identifies the
exact attachment body and `normalized_sha256` retains its normalized-text
meaning. Finally, the bounded Annual Report type allowlist includes SEC's numeric
`EX-13.<digits>` variants, while unrelated and nonnumeric suffixes remain out.

The three adversarial cases were observed together at 0/3 before these repairs
and 3/3 after. KO FY1997 supplies the real EX-13.1 route; the CP1252 case pins
byte identity; PGR FY2023 pins item-specific title and end proof. Default
extraction snapshots are identical across the amendment.
