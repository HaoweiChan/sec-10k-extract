"""Layers 2-3: document selection + normalization.

Mechanism: docs/architecture/overview.md. Rulings: ADR-003 (stdlib only,
normalization canon), ADR-006 (hidden iXBRL metadata, newline-by-era).

Self-check: python3 -m src.sec10k.normalize
"""
import re
from datetime import date
from html import unescape
from html.parser import HTMLParser

# EDGAR dissemination wraps every document in <DOCUMENT>/<TYPE>/<TEXT> SGML —
# present in full-text .txt submissions AND in many .htm primary documents.
DOC_RE = re.compile(r"<DOCUMENT>(.*?)(?:</DOCUMENT>|\Z)", re.S | re.I)
TYPE_RE = re.compile(r"^<TYPE>(\S+)", re.M | re.I)
SEQ_RE = re.compile(r"^<SEQUENCE>(\S+)", re.M | re.I)
NAME_RE = re.compile(r"^<FILENAME>(\S+)", re.M | re.I)
TEXT_RE = re.compile(r"<TEXT>(.*?)(?:</TEXT>|\Z)", re.S | re.I)

# 10-K405 is a 10-K filed under Reg S-K Item 405 check-box rules — same document,
# same items (textron-2001, ibm-1997). 10-K/A amendments and 10-KSB are NOT
# accepted at B: refusing is honest, a best-effort parse of a form we never
# validated is not (contract v2 envelope rules). They land in the README's
# unsupported list.
ACCEPTED_FORMS = {"10-K", "10-K405"}

# the cover page names the form within its first screenful; beyond that a 10-K
# freely says "Form 10-Q" and a 10-Q always cites its own prior "Form 10-K"
COVER_CHARS = 3000
FORM_SNIFF_RE = re.compile(r"\bFORM\s{0,4}(10-[A-Z0-9]{1,4}(?:/A)?)\b", re.I)
# an amendment's cover may typeset the marker away from the form token —
# "FORM 10-K" / "(Amendment No. 1)" on the next line, or "Amendment No. 1 to"
# above it — so the /A alternative alone does not hold ADR-024's refusal
# (cold-review T3-2, gates-2026-08-22). Within this many normalized chars of
# the token, on either side; no committed cover says "Amendment No" at all.
AMENDMENT_RE = re.compile(r"\bamendment\s+no\b", re.I)
AMENDMENT_REACH = 80

# normalized text this short means the parse collapsed, whatever the input was
COLLAPSE_FLOOR = 2000

BLOCK_TAGS = {
    "address", "article", "blockquote", "body", "br", "caption", "center",
    "div", "dl", "dd", "dt", "fieldset", "figure", "footer", "form", "h1",
    "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "tbody", "tfoot", "thead", "tr", "ul",
}
CELL_TAGS = {"td", "th"}
# ix:header/ix:hidden hold XBRL context definitions whose character data is not
# document text at all — 15.4% of JPM 2024 before the first readable word (ADR-006).
# <title> is the source filename or a filing agent's label ("aapl-20250927",
# "e10vk", "Document") — machine metadata no reader sees, INV-S5; it opened
# normalized_text on 18 of 38 fixtures (cold-review T3-1, gates-2026-08-22)
SKIP_TAGS = {"script", "style", "title", "ix:header", "ix:hidden"}


class _Plain(HTMLParser):
    """HTML -> plain text. Block tags break lines, inline tags vanish.

    With `tables=True` it ALSO records, in the same pass, where every
    <table>/<tr>/<td|th> starts and ends as offsets into the text it is
    emitting (ADR-029). The text itself is byte-identical either way: the
    recorder only reads `self.pos`, it never emits. Offsets are pre-_tidy
    here; `_tidy` moves them along with the text it rewrites.
    """

    def __init__(self, tables=False):
        super().__init__(convert_charrefs=True)  # entities decode here, stay Unicode
        self.parts = []
        self.pos = 0          # len("".join(parts)), kept incrementally
        self.skip_depth = 0
        self.tables = [] if tables else None   # closed records, document order
        self._open = []       # open <table> records, innermost last

    def _emit(self, s):
        self.parts.append(s)
        self.pos += len(s)

    # --- table recording (ADR-029 §b). One record per <table>: {start, end,
    # header, rows}; row = [cell...]; cell = [start, end] or [start, end,
    # colspan] when colspan > 1. html.parser synthesizes no end tags, so an
    # open cell/row is closed by the next <td>/<tr>/</table> as browsers do.
    def _cell_close(self):
        t = self._open[-1] if self._open else None
        if t and t["_cell"]:
            t["_cell"][1] = self.pos
            t["rows"][-1].append(t["_cell"])
            t["_cell"] = None

    def _row_close(self):
        t = self._open[-1] if self._open else None
        if t and t["rows"] and t["_row_open"]:
            self._cell_close()
            t["_row_open"] = False
            if not t["rows"][-1]:
                t["rows"].pop()          # <tr> with no cells: nothing to keep
            elif t["_row_th"] and t["header"] == len(t["rows"]) - 1:
                t["header"] += 1         # a leading run of all-<th> rows is the header

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        elif self.skip_depth:
            pass
        elif tag in BLOCK_TAGS:
            self._emit("\n")
            if self.tables is not None:
                if tag == "table":
                    self._open.append({"start": self.pos, "end": None, "header": 0,
                                       "rows": [], "_cell": None, "_row_open": False,
                                       "_row_th": True})
                elif tag == "tr" and self._open:
                    self._row_close()
                    t = self._open[-1]
                    t["rows"].append([])
                    t["_row_open"], t["_row_th"] = True, True
        elif tag in CELL_TAGS:
            if self.tables is not None and self._open:
                self._cell_close()
                t = self._open[-1]
                if not t["_row_open"]:   # <td> outside any <tr>: browsers imply one
                    t["rows"].append([])
                    t["_row_open"], t["_row_th"] = True, True
                t["_row_th"] &= tag == "th"
                span = dict(attrs).get("colspan") or "1"
                span = int(span) if span.strip().isdigit() else 1
                t["_cell"] = [self.pos + 1, None] + ([span] if span > 1 else [])
            self._emit(" ")  # cells are separate words, never one word

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif not self.skip_depth and tag in BLOCK_TAGS:
            if self.tables is not None and self._open:
                if tag == "table":
                    self._row_close()
                    t = self._open.pop()
                    t["end"] = self.pos
                    for k in ("_cell", "_row_open", "_row_th"):
                        del t[k]
                    if t["rows"]:
                        self.tables.append(t)
                elif tag == "tr":
                    self._row_close()
            self._emit("\n")
        elif not self.skip_depth and tag in CELL_TAGS and self.tables is not None:
            self._cell_close()

    def handle_data(self, data):
        if not self.skip_depth:
            # ADR-006 ruling 2: collapse WITHIN the chunk, while a source
            # line-wrap is still distinguishable from a block boundary
            self._emit(re.sub(r"\s+", " ", data))


def _sub_map(rx, repl, text, marks):
    """rx.sub(repl, text), plus the same edit applied to the sorted offsets in
    `marks`. An offset inside a replaced run lands on the run's replacement;
    the text comes from the very same rx.sub call the marks-free path makes,
    so it cannot differ from it (ADR-029 §d)."""
    if not marks:
        return rx.sub(repl, text), marks
    out, i, delta = [], 0, 0
    for m in rx.finditer(text):
        s, e = m.span()
        while i < len(marks) and marks[i] <= s:
            out.append(marks[i] + delta)
            i += 1
        while i < len(marks) and marks[i] < e:
            out.append(s + delta)
            i += 1
        delta += len(repl) - (e - s)
    out.extend(m + delta for m in marks[i:])
    return rx.sub(repl, text), out


TIDY_RULES = ((re.compile(r"[^\S\n]+"), " "),   # incl. U+00A0 from &nbsp; (ADR-003 canon)
              (re.compile(r" ?\n ?"), "\n"),
              (re.compile(r"\n{3,}"), "\n\n"))


def _tidy(text, marks=()):
    """Canonical whitespace. `marks` (sorted offsets into `text`) come back
    moved to where the same characters now sit; the text is unchanged by
    their presence."""
    marks = list(marks)
    for rx, repl in TIDY_RULES:
        text, marks = _sub_map(rx, repl, text, marks)
    lead = len(text) - len(text.lstrip())
    text = text.strip()
    return text, [min(max(m - lead, 0), len(text)) for m in marks]


def _place_tables(tables, marks, text):
    """Rewrite the pre-_tidy offsets in `tables` through the old->new `marks`
    map, then pull every span in to its first/last non-space character, so a
    cell slice never carries the separator `_Plain` emitted around it."""
    def tight(s, e):
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        return s, e
    for t in tables:
        ts, te = t["start"], t["end"] = tight(marks[t["start"]], marks[t["end"]])
        for row in t["rows"]:
            for c in row:
                s, e = tight(marks[c[0]], marks[c[1]])
                # an EMPTY cell in a leading/trailing spacer row sits in the
                # whitespace the table span was just pulled in from; keep it
                # inside [start, end] so every cell lies within its table
                c[0], c[1] = min(max(s, ts), te), min(max(e, ts), te)
    return tables


def split_documents(raw):
    """[{type, sequence, filename, body, start}] for each <DOCUMENT> block."""
    out = []
    for m in DOC_RE.finditer(raw):
        block = m.group(1)
        inner = TEXT_RE.search(block)
        body = inner.group(1) if inner else block
        field = lambda rx: (rx.search(block).group(1) if rx.search(block) else "")  # noqa: E731
        out.append({
            "type": field(TYPE_RE).upper(),
            "sequence": field(SEQ_RE),
            "filename": field(NAME_RE),
            "body": body,
            "start": m.start(),
        })
    return out


def format_era(body):
    if "<ix:" in body.lower():
        return "ixbrl"
    if re.search(r"<(?:html|body|div|font|span|p)[\s>/]", body, re.I):
        return "html"
    return "txt"  # 1993-2001 submissions carry <PAGE>/<TABLE>/<S>/<C> only


def normalize(body, era, tables=False):
    """Deterministic plain text. Offsets in the contract are into this.

    Returns `(text, tables)`: `tables` is None unless asked for, else the
    ADR-029 records — `{start, end, header, rows}` with offsets into `text`,
    document order. The txt era has no HTML tables (its SGML <TABLE>/<S>/<C>
    layout is ruled out, ADR-029 §e) so it answers `[]`. `text` is the same
    string whether or not tables are asked for — by construction, not by care:
    the recorder never emits, and `_tidy` edits the text with or without
    offsets to carry.
    """
    if era == "txt":
        # newlines ARE the document here: fixed-width layout, line-anchored
        # headings, page furniture that stays in the text (ADR-006 ruling 2)
        text = body.replace("\r\n", "\n").replace("\r", "\n").strip()
        return text, ([] if tables else None)
    p = _Plain(tables=tables)
    p.feed(body)
    p.close()
    if not tables:
        return _tidy("".join(p.parts))[0], None
    olds = sorted({m for t in p.tables for m in (t["start"], t["end"])}
                  | {m for t in p.tables for r in t["rows"] for c in r for m in c[:2]})
    text, news = _tidy("".join(p.parts), olds)
    found = _place_tables(p.tables, dict(zip(olds, news)), text)
    # drop a table with no visible text at all (spacer/rule tables): there is
    # no structure there for a reader to lose. Sort: a nested table closes
    # before its parent, so `p.tables` is in end order, not start order.
    found = [t for t in found if any(c[0] < c[1] for r in t["rows"] for c in r)]
    found.sort(key=lambda t: (t["start"], t["end"]))
    return text, found


# period of report, best signal first: EDGAR's own SGML header, the iXBRL
# dei fact, then the cover page. All three are needed — the header exists only
# on full submissions, dei only on 2019+ iXBRL, and JPM's two-column cover
# interleaves "For the fiscal year ended" with "Commission file" so the cover
# regex alone misses it.
PERIOD_HDR_RE = re.compile(r"CONFORMED PERIOD OF REPORT:\s*(\d{4})(\d{2})(\d{2})")
DEI_PERIOD_RE = re.compile(r'name="dei:DocumentPeriodEndDate"')
# the comma can float ("December 31 , 2024") once JPM's nested ix element is
# tag-stripped, so it is optional and may carry space on either side
# (?i) is load-bearing: an ALL-CAPS cover block ("DECEMBER 31, 2016") is a
# common filer typesetting choice, and COVER_DATE_RE below already matches one.
# Without it the two regexes disagree about case, the captured string fails to
# parse, period_end comes back None, and expected_items silently drops the
# whole modern taxonomy — caps-cover-taxonomy.
DATE_RE = re.compile(r"(?i)([A-Za-z]{3,9})\.?\s+(\d{1,2})\s*,?\s*(\d{4})")
# same comma freedom on BOTH sides here: "December 31,2016" (space-less) and
# "December 31 , 2016" (floating) are typesetting, and a miss demotes the
# filing to the 1993 item set (cold-review T3-3, comma-cover-period)
COVER_DATE_RE = re.compile(r"(?i)fiscal year ended[:\s]*"
                           r"([A-Z][a-z]{2,8}\.?\s+\d{1,2}\s*,?\s*\d{4})")
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def _parse_date(s):
    # every match, not just the first: (?i) widens DATE_RE enough that a
    # non-month word ("Ended 31, 2016") can match ahead of the real date, and
    # returning None then would reintroduce the bug this loop exists to kill
    for m in DATE_RE.finditer(s):
        month = m.group(1).lower()
        idx = next((i for i, name in enumerate(MONTHS, 1)
                    if name.startswith(month[:3])), None)
        if not idx:
            continue
        try:
            return date(int(m.group(3)), idx, int(m.group(2)))
        except ValueError:
            continue
    return None


def period_end(raw, text):
    """Fiscal-period end date, or None. Decides the era's expected item set."""
    m = PERIOD_HDR_RE.search(raw)
    if m:
        try:
            return date(*(int(g) for g in m.groups()))
        except ValueError:
            pass
    m = DEI_PERIOD_RE.search(raw)
    if m:  # the fact's own text, tags stripped — it may wrap a nested ix element
        window = re.sub(r"<[^>]*>", " ", raw[m.end():m.end() + 400])
        got = _parse_date(unescape(window))
        if got:
            return got
    m = COVER_DATE_RE.search(text[:COVER_CHARS * 2])
    return _parse_date(m.group(1)) if m else None


def sniff_form(text):
    """Form type per the cover page, or None. Second opinion on <TYPE>."""
    m = FORM_SNIFF_RE.search(text[:COVER_CHARS])
    if not m:
        return None
    form = m.group(1).upper().replace(" ", "")
    if not form.endswith("/A") and AMENDMENT_RE.search(
            text[max(0, m.start() - AMENDMENT_REACH):m.end() + AMENDMENT_REACH]):
        form += "/A"
    return form


def select_and_normalize(raw, tables=False):
    """Layers 2+3. Returns (normalized_text, meta, warnings, tables).

    meta.form_type is None when nothing identified the form — the caller
    turns that into `unsupported`; this function never decides doc_status.
    `tables` is None unless asked for (ADR-029, opt-in): asking changes
    nothing else in the return value.
    """
    warnings = []
    blocks = split_documents(raw)
    chosen = next((b for b in blocks if b["type"] in ACCEPTED_FORMS), None)

    # Exhibits-only or a non-10-K submission: EDGAR's own metadata says so, and
    # selection has nothing to select. This branch used to return "" — which
    # tripped the caller's collapse test, since the caller checks collapse
    # BEFORE form identity (contract order, ADR-010 ruling 4). So a perfectly
    # readable 10-KSB came back `failed`, "117768 raw chars normalized to 0",
    # which sends a user to re-download a file that downloaded fine. The
    # ordering is not the bug: an unselectable submission is not an unreadable
    # one, so normalize the whole file and let the caller refuse on the form it
    # can now name. A file that is BOTH unselectable and truncated still
    # collapses first, which is the ordering doing its job.
    body = chosen["body"] if chosen else raw
    era = format_era(body)
    text, found = normalize(body, era, tables)

    declared = chosen["type"] if chosen else (blocks[0]["type"] or None if blocks else None)
    if blocks and chosen is None:
        # ...and SAY SO. `document_selected` records it in meta, but meta is not
        # where a consumer looks for problems. The span universe on this path is
        # every <DOCUMENT> block concatenated, exhibits included, so an EX-13
        # carrying its own "Item 1." headings is inside the text being segmented.
        # Worse, `blocks[0]["type"]` is empty when the SGML header omits <TYPE>:
        # form_type then falls through to the cover page, the submission is
        # accepted as a 10-K, and the last item's span swallows the exhibit —
        # `success`, no warnings. Non-escalating (not in AMBIGUOUS_CODES): the
        # parse is real and usually right, it is the SCOPE that needs declaring.
        warnings.append({
            "code": "whole_submission_fallback", "item": None,
            "message": f"no <DOCUMENT> block declares an accepted 10-K form "
                       f"({sorted({b['type'] or '<none>' for b in blocks})}); the whole "
                       f"submission was normalized, so exhibits are inside the span universe"})
    sniffed = sniff_form(text)
    form_type = declared or sniffed
    # filer-supplied <TYPE> vs the document's own cover page. Warn, trust
    # <TYPE> (EDGAR validates it); never refuse on disagreement alone. Same
    # form family is agreement: a 10-K405's cover page always reads "FORM
    # 10-K" (405 is a check-box distinction, not a form title), so comparing
    # the strings would fire on every 10-K405 ever filed.
    # ...and EDGAR's <TYPE> drops the hyphen the cover page keeps ("10KSB" vs
    # "FORM 10-KSB"), which is spelling, not disagreement.
    if declared and sniffed and declared.replace("-", "") != sniffed.replace("-", "") \
            and not {declared, sniffed} <= ACCEPTED_FORMS:
        warnings.append({"code": "form_type_disagreement", "item": None,
                         "message": f"<TYPE> says {declared}, cover page says {sniffed}"})

    meta = {
        "form_type": form_type,
        "period_end": period_end(raw, text),
        "form_type_declared": declared,
        "form_type_sniffed": sniffed,
        "format_era": era,
        "n_blocks": len(blocks),
        "block_types": sorted({b["type"] for b in blocks}) if blocks else [],
        "document_selected": (
            f"{chosen['type']} seq={chosen['sequence']} {chosen['filename']}".strip()
            if chosen else "whole file (no 10-K block to select)" if blocks
            else "whole file (no <DOCUMENT> blocks)"),
        "raw_chars": len(raw),
        "norm_chars": len(text),
    }
    return text, meta, warnings, found


def _demo():
    """Smallest checks that fail if the ADR-003/006 rulings break."""
    html_doc = ("<html><body><div style=display:none><ix:header><ix:hidden>"
                "<xbrldi:explicitMember>us-gaap:OperatingSegmentsMember"
                "</xbrldi:explicitMember></ix:hidden></ix:header></div>"
                "<p>FORM 10-K</p><p>Microsoft was\nfounded in 1975. "
                "AT&amp;T&#160;paid.</p><table><tr><td>12</td><td>34</td></tr>"
                "</table><script>var x=1;</script></body></html>")
    text, meta, warns, _ = select_and_normalize(html_doc)
    assert "us-gaap:" not in text, text                      # INV-S5
    assert "OperatingSegmentsMember" not in text, text
    assert "var x" not in text, text
    assert "Microsoft was founded in 1975." in text, text    # ADR-006 ruling 2
    assert "AT&T paid." in text, text                        # entity + nbsp canon
    assert "12 34" in text, text                             # cells stay separate words
    assert meta["form_type"] == "10-K" and meta["format_era"] == "ixbrl", meta
    # ADR-029: asking for tables changes nothing but the fourth value, and the
    # one table's cells are slices of the SAME text
    t_on, m_on, w_on, tabs = select_and_normalize(html_doc, tables=True)
    assert (t_on, m_on, w_on) == (text, meta, warns)
    assert len(tabs) == 1 and [text[c[0]:c[1]] for c in tabs[0]["rows"][0]] == ["12", "34"], tabs

    txt_doc = ("<DOCUMENT>\n<TYPE>10-K405\n<SEQUENCE>1\n<TEXT>\nFORM 10-K\n"
               "Item 1.  Business\n   fixed   width\n   lines\n</TEXT>\n</DOCUMENT>\n"
               "<DOCUMENT>\n<TYPE>EX-13\n<TEXT>\nItem 1.  Not this one\n</TEXT>\n</DOCUMENT>")
    text, meta, warns, _ = select_and_normalize(txt_doc)
    assert "Not this one" not in text, text                  # trap 5: exhibits dropped
    assert "\n   fixed   width\n" in text, repr(text)        # txt layout survives
    assert meta["format_era"] == "txt" and meta["form_type"] == "10-K405", meta

    # a 10-Q cover must not be read as a 10-K just because it cites one later
    q = "<html><body><p>FORM 10-Q</p><p>see our Annual Report on Form 10-K</p></body></html>"
    assert sniff_form(select_and_normalize(q)[0]) == "10-Q"

    # <TYPE> 10-K405 + "FORM 10-K" cover is the norm, not a disagreement...
    quiet = ("<DOCUMENT>\n<TYPE>10-K405\n<TEXT>\n" + "FORM 10-K\nbody\n" + "</TEXT>\n</DOCUMENT>")
    assert select_and_normalize(quiet)[2] == [], select_and_normalize(quiet)[2]
    # ...but a genuine form mismatch still warns
    loud = ("<DOCUMENT>\n<TYPE>10-K\n<TEXT>\n" + "FORM 10-Q\nbody\n" + "</TEXT>\n</DOCUMENT>")
    assert [w["code"] for w in select_and_normalize(loud)[2]] == ["form_type_disagreement"]

    # exhibits-only submission: EDGAR's own metadata refuses it for us — by
    # NAMING the form, not by returning nothing. Returning "" here made the
    # caller's collapse test fire and report `failed` on a readable file
    # (ksb-unsupported).
    ex = "<DOCUMENT>\n<TYPE>EX-21\n<TEXT>\nsubsidiaries\n</TEXT>\n</DOCUMENT>"
    t, m, w, _ = select_and_normalize(ex)
    assert m["form_type"] == "EX-21" and m["form_type"] not in ACCEPTED_FORMS, m
    assert "subsidiaries" in t, t   # readable, therefore not a collapse
    assert [x["code"] for x in w] == ["whole_submission_fallback"], w
    # the shape that made the fallback dangerous: no <TYPE> at all, so form_type
    # falls through to the cover page and a 10-K is ACCEPTED with its exhibits
    # inside the span universe. It may proceed — but not in silence.
    untyped = ("<DOCUMENT>\n<TEXT>\nFORM 10-K\nItem 1. Business\nprose\n</TEXT>\n</DOCUMENT>\n"
               "<DOCUMENT>\n<TYPE>EX-13\n<TEXT>\nItem 1. Business\nexhibit\n</TEXT>\n</DOCUMENT>")
    t2, m2, w2, _ = select_and_normalize(untyped)
    assert m2["form_type"] == "10-K" and m2["form_type_declared"] is None, m2
    assert "exhibit" in t2, t2
    assert "whole_submission_fallback" in [x["code"] for x in w2], w2
    # EDGAR's <TYPE> drops the hyphen the cover page keeps; same form, no news
    ksb = "<DOCUMENT>\n<TYPE>10KSB\n<TEXT>\nFORM 10-KSB\nbody\n</TEXT>\n</DOCUMENT>"
    codes = [x["code"] for x in select_and_normalize(ksb)[2]]
    assert "form_type_disagreement" not in codes, codes   # spelling, not news
    assert codes == ["whole_submission_fallback"], codes   # ...but the scope IS news

    # ADR-024 rules 10-K/A OUT, so the refusal is the behaviour that has to
    # hold — on BOTH routes, because an amendment reaches us either way and the
    # /A is one character wide. These two byte-adjacent shapes are pinned here,
    # at the layer (ADR-024 §2); the non-adjacent marker (T3-2) has a gate case
    # of its own, amended-cover-refused, on the synthetic amended-cover-2021.
    amd_sgml = "<DOCUMENT>\n<TYPE>10-K/A\n<TEXT>\nFORM 10-K/A\nbody\n</TEXT>\n</DOCUMENT>"
    assert select_and_normalize(amd_sgml)[1]["form_type"] == "10-K/A"
    # ...and the one that matters more: a primary .htm carries no SGML header at
    # all, so only the cover-page sniff stands between an amendment and a parse.
    amd_htm = "<html><body><p>FORM 10-K/A</p><p>Amendment No. 1</p></body></html>"
    m3 = select_and_normalize(amd_htm)[1]
    assert m3["form_type_declared"] is None and m3["form_type"] == "10-K/A", m3
    assert "10-K/A" not in ACCEPTED_FORMS   # extract.py returns `unsupported`

    # cold-review T3-1 (gates-2026-08-22): the <title> is a filename or a filing
    # agent's label — machine metadata, INV-S5 — not the first line of the filing
    titled = "<html><head><title>aapl-20250927</title></head><body><p>FORM 10-K</p></body></html>"
    assert "aapl-20250927" not in select_and_normalize(titled)[0]
    # T3-2: the ADR-024 refusal must hold when the amendment marker is typeset
    # away from the form token, on either side of it
    for cover in ("<p>FORM 10-K</p><p>(Amendment No. 1)</p>",
                  "<p>Amendment No. 1 to</p><p>FORM 10-K</p>"):
        got = sniff_form(select_and_normalize(f"<html><body>{cover}</body></html>")[0])
        assert got == "10-K/A", (cover, got)
    # T3-3: a space-less or floating comma in the cover date is typesetting,
    # not a missing date (comma-cover-period carries the space-less shape)
    for s in ("fiscal year ended December 31,2016", "fiscal year ended December 31 , 2016"):
        assert period_end("", s) == date(2016, 12, 31), (s, period_end("", s))

    print("[normalize self-check] ok")


if __name__ == "__main__":
    _demo()
