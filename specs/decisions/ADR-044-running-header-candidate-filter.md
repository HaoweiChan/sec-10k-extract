# ADR-044 — preserve a real heading attached to a TOC from its running headers

Date: 2026-08-28. Status: accepted. **Sanctioned post-freeze exception.** The
frozen AIG FY2024 run was executed before this decision and silently lost the
opening page of Item 1 while reporting `success`, 0.95 confidence and no
item-level warning. Its outcome now influences the implementation, so the case
and fixture are burned and moved to the adversarial corpus; exactly one new
held-out replacement is owed.

**Ruling**: `_toc_runs` keeps the final candidate of an index run when its code already appeared in the leading chain of dense index clusters and no standalone candidate precedes it. This is the structural shape of a contents block that runs directly into the first real item heading. Later page furniture may repeat that code, so recurrence alone cannot safely discard the trailing candidate. No threshold, AIG literal, offset, or per-filer exception is added.
**Because**: AIG's titled candidates 0–22, at normalized offsets 4,411–6,357, are its front-matter Item 1–16 TOC. Candidate 23, at 6,459, is the real `ITEM 1 | Business` heading. It was dropped because page headers later repeat Item 1; greedy assignment then selected the page-2 header at 8,828 and lost the opening anchor. The existing rule correctly removes the 23 TOC entries; it was over-broad only for the one trailing body candidate.
**Enforced by**: the burned AIG adversarial case and the direct `segment._demo()` reproduction. The leading dense-chain reproduction drops the TOC and retains its trailing Item 1 heading; the independent-run counterexample confirms that a standalone body heading ends the exception. AIG's frozen Item 1 anchor passes after the correction.

---

## Alternatives rejected

1. **Leave the recurrence rule unchanged.** This retains a confident silent
partial loss on a real filing.
2. **Keep every last member of every dense run.** ADR-015 already shows that
dense one-line body items can be legitimate; a generic last-member exemption
would let a titled TOC candidate survive where no preceding TOC code identifies
it as the body transition.
3. **Preserve every repeated code in the TOC.** That weakens the filter over
ordinary repeated/duplicated index material and admits many more false
candidates than the one required body boundary.

The selected discriminator is the smallest shared correction: one candidate
in a run the existing manifest test has already identified as an index, only
when its code has an earlier declaration in the leading dense index chain.

## Measurements and limit

At the frozen implementation, AIG Item 1 started at 8,828 and failed its
opening anchor. After the correction it starts at 6,459, has 48,136 characters,
and passes the complete burned case. A two-process comparison of the serialized
`doc_status`, `warnings`, and `items` fields for every fixture present at
`origin/main` found **50/50 unchanged**. The newly moved AIG fixture is not in
that denominator.

This is not a general page-furniture classifier. It only corrects a real
heading physically attached to the index it follows. A falsifier is a filing
where the preserved trailing duplicate is itself TOC material, or a legitimate
first body heading lacks this preceding-code relation. Either result requires a
new adversarial case and a revised rule; neither may be patched by adding a
filer name, text literal, or offset condition.
