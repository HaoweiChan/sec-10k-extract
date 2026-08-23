"""Wide sweep (PR #39 R1): every decimal in the D2-live sections of the three docs that
--check-docs cannot see (no backticked fixture name within 60 chars before it on the line),
re-derived against every committed bench artifact (+ cross-run ranges, /60 minute conversions)."""
import json, re, glob, sys
sys.path.insert(0, '.')
from evals.bench import MIB, DOC_WINDOW
ARTS = sorted(glob.glob('evals/report/2026082*-bench.json'))
CLEAN7 = [a for a in ARTS if any(s in a for s in ('031501', '031540', '031620', '115810', '185543', '185626', '185707'))]
TRIO = [a for a in ARTS if '20260823' in a]
OLDTRIO = [a for a in ARTS if any(s in a for s in ('031501', '031540', '031620'))]


def walk(o, path, out):
    if isinstance(o, dict):
        for k, v in o.items():
            walk(v, path + '.' + k, out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + f'[{i}]', out)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        out.append((float(o), path))


def named(d, p):
    return re.sub(r'records\[(\d+)\]', lambda m: 'records[' + d['records'][int(m.group(1))]['fixture'] + ']', p)


univ = []   # (value, label)
for a in ARTS:
    d = json.load(open(a)); tag = a.split('/')[-1][:15]
    vals = []
    walk(d, '', vals)
    for v, p in vals:
        univ.append((v, f'{tag}:{named(d, p)}'))
    for r in d['records']:
        univ.append((r['raw_bytes'] / MIB, f'{tag}:records[{r["fixture"]}].raw_bytes/MiB'))
    for k, v in (d['perf'].get('heldout_sizes_bytes') or {}).items():
        univ.append((v / MIB, f'{tag}:heldout[{k}]/MiB'))
    for k, p in d['perf'].get('populations', {}).items():
        univ.append((p['edgar_year_7000_seconds'] / 60, f'{tag}:populations.{k}.edgar_year_7000_seconds/60'))
        univ.append((p['n_1000_seconds'] / 60, f'{tag}:populations.{k}.n_1000_seconds/60'))


def ranges(arts, label):
    flat = {}
    for a in arts:
        d = json.load(open(a)); vals = []; walk(d, '', vals)
        for v, p in vals:
            flat.setdefault(named(d, p), []).append(v)
    for p, vs in flat.items():
        univ.append((min(vs), f'{label}:min{p}')); univ.append((max(vs), f'{label}:max{p}'))


ranges(TRIO, 'trio23'); ranges(OLDTRIO, 'trio20'); ranges(CLEAN7, 'clean7')
ror = json.load(open('evals/report/20260823-185707-bench.json'))
rec = {r['fixture']: r for r in ror['records']}
univ.append((rec['bac-2006']['median_s'] / rec['xom-2021']['median_s'], 'ror:bac/xom median ratio'))
syn = [r for r in ror['records'] if r['synthetic']]; real = [r for r in ror['records'] if not r['synthetic']]
univ.append((sum(r['raw_bytes'] for r in syn) / len(syn) / MIB, 'ror:synthetic mean MiB'))
univ.append((sum(r['raw_bytes'] for r in real) / len(real) / MIB, 'ror:real-dev mean MiB'))
fix_names = sorted(rec, key=len, reverse=True)
name_re = re.compile('`(' + '|'.join(re.escape(n) for n in fix_names) + ')`')
num_re = re.compile(r'(?<![\w.,])(\d+\.\d+)(?![\d])')


def sections(path):
    text = open(path).read().split('\n')
    if path.endswith('analysis-report.md'):
        s3 = next(i for i, l in enumerate(text) if l.startswith('## 3. Runtime'))
        s6 = next(i for i, l in enumerate(text) if l.startswith('## 6. Where'))
        v4 = next(i for i, l in enumerate(text) if l.startswith('v4 (2026-08-20)'))
        return [(i, l) for i, l in enumerate(text) if i < v4 or s3 <= i < s6]
    if path.endswith('README.md'):
        a = next(i for i, l in enumerate(text) if l.startswith('## Performance'))
        b = next(i for i, l in enumerate(text) if l.startswith('## Where AI'))
        return [(i, l) for i, l in enumerate(text) if a <= i < b or 'Large filings' in l]
    return list(enumerate(text))


rows = []; n_vis = 0
for path in ['docs/analysis-report.md', 'README.md', 'specs/decisions/ADR-021-benchmark-instrument.md']:
    for i, line in sections(path):
        hits = list(name_re.finditer(line))
        for nm in num_re.finditer(line):
            before = line[max(0, nm.start() - 1):nm.start()]; after = line[nm.end():nm.end() + 2]
            if before == '$' or after[:1] in ('%', '×') or after[:2] in ('x ',):
                continue
            visible = False
            for h in hits:
                if h.end() <= nm.start() < h.end() + DOC_WINDOW and not any(h.end() < h2.start() <= nm.start() for h2 in hits):
                    visible = True
            if visible:
                n_vis += 1; continue
            lit = nm.group(1); places = len(lit.split('.')[1]); target = float(lit)
            def prio(lab):
                return (0 if lab.startswith('20260823-185707:.perf') else 1 if lab.startswith('20260823-185707') else
                        2 if lab.startswith('trio23') else 3 if lab.startswith('ror') else 4 if lab.startswith('clean7') else
                        5 if lab.startswith('20260820-031540') else 6 if lab.startswith('trio20') else 7)
            m = sorted((lab for v, lab in univ if round(v, places) == target), key=prio)
            rows.append((path.split('/')[-1], i + 1, lit, line.strip()[max(0, nm.start() - 30):nm.end() + 15], m))
mode = sys.argv[1] if len(sys.argv) > 1 else "bad"
if mode != "json": print("instrument-visible decimals skipped:", n_vis)
if mode != "json": print("instrument-INVISIBLE decimals:", len(rows))
bad = [r for r in rows if not r[4]]
if mode != "json": print("no artifact derivation found:", len(bad))
mode = sys.argv[1] if len(sys.argv) > 1 else 'bad'
if mode == 'json':
    print(json.dumps([f'{r[0]}:{r[1]} {r[2]} -> {r[4][0] if r[4] else "NONE"}' for r in rows], indent=0, ensure_ascii=False))
else:
    for r in rows:
        if mode == 'all' or not r[4]:
            print(('OK ' if r[4] else 'NO ') + f'{r[0]}:{r[1]} {r[2]} | {r[3]!r} | {r[4][0] if r[4] else "-"}')
