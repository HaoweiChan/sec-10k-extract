# D32 — localhost presentation and source assets

## Material decision

Raw validator warnings remain API output and provenance. The UI collapses them
only when every risky target has a verified terminal result, then labels
`meta.coverage` as primary-span coverage rather than claiming complete content
extraction. Vision runs only for verified alternative evidence that overlaps a
same-accession SEC image; a terminal disposition alone spends nothing. The
original source bytes remain unchanged while the iframe routes permitted
same-accession images through an independently bounded 32-asset (16 MiB)
proxy that rejects traversal, foreign accessions, redirects, and non-images.
This source-viewer cap is not Vision's two-image cap; a lock reserves viewer
slots before fetch so parallel assets cannot exceed it.

## Assumption → Eval contradiction → Correction

- Assumed: a completed graph made raw primary-span warnings safe to show in the
  main banner. Eval said: `d32-presentation` showed that this reads as an
  unresolved failure and can be mistaken for a 100% coverage claim. Corrected:
  complete routes show an explicitly limited primary-span summary; details keep
  the raw caveat.
- Assumed: post-graph vision could merely annotate accepted alternatives. Cold
  review found a reject still left `graph.complete`. Corrected: rejected image
  evidence removes the alternative resolution, preserves cost, and leaves the
  item review-required.
