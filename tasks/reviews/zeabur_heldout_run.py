"""Run every held-out case against the DEPLOYED inspector over /api/extract/url.

Same case files, same checks, same adapter — only the extractor is remote. So a
disagreement between this and the local run is a deployment fact, not a
labelling one.
"""
import hashlib, json, glob, os, re, sys, time, urllib.request
sys.path.insert(0, '/Users/willy/Documents/sec-10k-extract/.claude/worktrees/gpt-difficult-10k-samples-579d78')
from src.sec10k.eval_adapter import eval_check  # the SAME check vocabulary the suite uses

BASE = "https://whaleforce-sec10k.zeabur.app"
URLS = {
 "aig-2025-heldout":  "https://www.sec.gov/Archives/edgar/data/5272/000000527225000012/aig-20241231.htm",
 "cost-2022-heldout": "https://www.sec.gov/Archives/edgar/data/909832/000090983222000021/cost-20220828.htm",
 "csco-2016-heldout": "https://www.sec.gov/Archives/edgar/data/858877/000085887716000117/csco-2016730x10k.htm",
 "mrk-1995-heldout":  "https://www.sec.gov/Archives/edgar/data/64978/0000950130-96-000896.txt",
 "pgr-2023-heldout":  "https://www.sec.gov/Archives/edgar/data/80661/000008066124000007/pgr-20231231.htm",
 "smci-2025-heldout": "https://www.sec.gov/Archives/edgar/data/1375365/000137536525000004/smci-20240630.htm",
}

meta = json.load(urllib.request.urlopen(f"{BASE}/api/meta", timeout=30))
print(f"deployed git_sha {meta['git_sha']}  escalation_enabled={meta['escalation_enabled']} "
      f"token_required={meta.get('escalation_token_required')}\n")

total_usd = 0.0
for f in sorted(glob.glob('evals/heldout/*-heldout.json')):
    case = json.load(open(f)); cid = case["id"]
    url = URLS.get(cid)
    if not url:
        print(f"[SKIP] {cid}: no EDGAR URL"); continue
    body = json.dumps({"url": url}).encode()
    req = urllib.request.Request(f"{BASE}/api/extract/url", data=body,
                                 headers={"content-type": "application/json"})
    t0 = time.time()
    try:
        res = json.load(urllib.request.urlopen(req, timeout=600))
    except Exception as e:
        print(f"[ERROR] {cid}: {type(e).__name__}: {e}"); continue
    el = time.time() - t0
    if "detail" in res or res.get("error"):
        print(f"[ERROR] {cid}: {str(res)[:200]}"); continue
    # the envelope the API returns carries no `normalized_text` — it is served
    # separately so the offsets have exactly one source. Fetch it and VERIFY its
    # sha256 against the run, per the README's reproduction recipe, so the
    # checks below run against provably the same text the offsets index.
    tok = res["source"]["token"]
    norm = urllib.request.urlopen(f"{BASE}/api/normalized/{tok}", timeout=300).read()
    got = hashlib.sha256(norm).hexdigest()
    if got != res["norm_sha256"]:
        print(f"[ERROR] {cid}: norm_sha256 mismatch — {got[:12]} != {res['norm_sha256'][:12]}")
        continue
    res["normalized_text"] = norm.decode("utf-8")
    usd = (res.get("cost") or {}).get("usd", 0.0) or 0.0
    total_usd += usd
    # `item_text` slices `normalized_text[start:end]`, and the sha-verified text
    # above IS that string — so every content check here reads the DEPLOYMENT's
    # own offsets, and the API's 40,000-char display truncation is irrelevant.
    # What genuinely cannot run remotely is the handful of check types that
    # re-invoke `extract_items` on a local path (`deterministic`,
    # `escalation_invariant`, `offsets_invariant_under_*`); running those here
    # would be measuring the LOCAL extractor and calling it a deployment fact,
    # so they are skipped by name and counted.
    LOCAL_ONLY = {"deterministic", "escalation_invariant", "routing",
                  "verify_guards", "route_payload",
                  "offsets_invariant_under_exclusion", "offsets_invariant_under_tables",
                  "offsets_invariant_under_images", "offsets_invariant_under_blocks"}
    fails, skipped = [], []
    for chk in case["expect"]["checks"]:
        if chk["type"] in LOCAL_ONLY:
            skipped.append(chk["type"]); continue
        why = eval_check(res, chk)
        if why:
            fails.append((chk, why))
    tag = "PASS" if not fails else "FAIL"
    print(f"[{tag}] {cid:<22} {res['doc_status']:<22} cov={res.get('meta',{}).get('coverage')} "
          f"${usd:.6f} {el:5.1f}s")
    for chk, why in fails:
        print(f"        FAIL {why[:150]}")
    if skipped:
        print(f"        (skipped, cannot run remotely: {sorted(set(skipped))})")
print(f"\nTOTAL SPENT ON THE DEPLOYMENT: ${total_usd:.6f}")
