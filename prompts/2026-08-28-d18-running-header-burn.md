# D18 — running-header burn decision

## Material request

Burn the frozen AIG FY2024 failure into the adversarial set, reproduce the
candidate-filter defect before changing it, make a structural shared fix, and
record the freeze exception, replacement debt, and corpus blast radius.

## Outcome

The diagnosis found a dense front-matter TOC ending immediately before the
real Item 1 heading. Later Item 1 running headers made that body heading recur,
so `_toc_runs` dropped it with the TOC. The selected fix retains only the last
candidate of an identified index run when its code was already declared in the
leading dense index chain. It adds no threshold, dependency, filer literal, or output
contract. The moved AIG case passes and all 50 pre-existing origin/main fixture
outputs are byte-for-byte identical after serializing `doc_status`, `warnings`,
and `items`.
