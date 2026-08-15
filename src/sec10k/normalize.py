"""Layers 2-3: document selection + normalization.

Mechanism: docs/architecture/overview.md. Rulings: ADR-003 (stdlib only,
normalization canon), ADR-006 (hidden iXBRL metadata, newline-by-era).

Self-check: python3 -m src.sec10k.normalize
"""
import re
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
# document text at all — 15.4% of JPM 2024 before the first readable word (ADR-006)
SKIP_TAGS = {"script", "style", "ix:header", "ix:hidden"}


class _Plain(HTMLParser):
    """HTML -> plain text. Block tags break lines, inline tags vanish."""

    def __init__(self):
        super().__init__(convert_charrefs=True)  # entities decode here, stay Unicode
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        elif self.skip_depth:
            pass
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")
        elif tag in CELL_TAGS:
            self.parts.append(" ")  # cells are separate words, never one word

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif not self.skip_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            # ADR-006 ruling 2: collapse WITHIN the chunk, while a source
            # line-wrap is still distinguishable from a block boundary
            self.parts.append(re.sub(r"\s+", " ", data))


def _tidy(text):
    text = re.sub(r"[^\S\n]+", " ", text)  # incl. U+00A0 from &nbsp; (ADR-003 canon)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def normalize(body, era):
    """Deterministic plain text. Offsets in the contract are into this."""
    if era == "txt":
        # newlines ARE the document here: fixed-width layout, line-anchored
        # headings, page furniture that stays in the text (ADR-006 ruling 2)
        return body.replace("\r\n", "\n").replace("\r", "\n").strip()
    p = _Plain()
    p.feed(body)
    p.close()
    return _tidy("".join(p.parts))


def sniff_form(text):
    """Form type per the cover page, or None. Second opinion on <TYPE>."""
    m = FORM_SNIFF_RE.search(text[:COVER_CHARS])
    return m.group(1).upper().replace(" ", "") if m else None


def select_and_normalize(raw):
    """Layers 2+3. Returns (normalized_text, meta, warnings).

    meta.form_type is None when nothing identified the form — the caller
    turns that into `unsupported`; this function never decides doc_status.
    """
    warnings = []
    blocks = split_documents(raw)
    chosen = next((b for b in blocks if b["type"] in ACCEPTED_FORMS), None)
    if blocks and chosen is None:
        # exhibits-only or a non-10-K submission: EDGAR's own metadata says so
        types = sorted({b["type"] for b in blocks})
        return "", {"form_type": None, "format_era": None, "n_blocks": len(blocks),
                    "document_selected": None, "block_types": types}, warnings

    body = chosen["body"] if chosen else raw
    era = format_era(body)
    text = normalize(body, era)

    declared = chosen["type"] if chosen else None
    sniffed = sniff_form(text)
    form_type = declared or sniffed
    # filer-supplied <TYPE> vs the document's own cover page. Warn, trust
    # <TYPE> (EDGAR validates it); never refuse on disagreement alone. Same
    # form family is agreement: a 10-K405's cover page always reads "FORM
    # 10-K" (405 is a check-box distinction, not a form title), so comparing
    # the strings would fire on every 10-K405 ever filed.
    if declared and sniffed and declared != sniffed \
            and not {declared, sniffed} <= ACCEPTED_FORMS:
        warnings.append({"code": "form_type_disagreement", "item": None,
                         "message": f"<TYPE> says {declared}, cover page says {sniffed}"})

    meta = {
        "form_type": form_type,
        "form_type_declared": declared,
        "form_type_sniffed": sniffed,
        "format_era": era,
        "n_blocks": len(blocks),
        "document_selected": (
            f"{chosen['type']} seq={chosen['sequence']} {chosen['filename']}".strip()
            if chosen else "whole file (no <DOCUMENT> blocks)"),
        "raw_chars": len(raw),
        "norm_chars": len(text),
    }
    return text, meta, warnings


def _demo():
    """Smallest checks that fail if the ADR-003/006 rulings break."""
    html_doc = ("<html><body><div style=display:none><ix:header><ix:hidden>"
                "<xbrldi:explicitMember>us-gaap:OperatingSegmentsMember"
                "</xbrldi:explicitMember></ix:hidden></ix:header></div>"
                "<p>FORM 10-K</p><p>Microsoft was\nfounded in 1975. "
                "AT&amp;T&#160;paid.</p><table><tr><td>12</td><td>34</td></tr>"
                "</table><script>var x=1;</script></body></html>")
    text, meta, warns = select_and_normalize(html_doc)
    assert "us-gaap:" not in text, text                      # INV-S5
    assert "OperatingSegmentsMember" not in text, text
    assert "var x" not in text, text
    assert "Microsoft was founded in 1975." in text, text    # ADR-006 ruling 2
    assert "AT&T paid." in text, text                        # entity + nbsp canon
    assert "12 34" in text, text                             # cells stay separate words
    assert meta["form_type"] == "10-K" and meta["format_era"] == "ixbrl", meta

    txt_doc = ("<DOCUMENT>\n<TYPE>10-K405\n<SEQUENCE>1\n<TEXT>\nFORM 10-K\n"
               "Item 1.  Business\n   fixed   width\n   lines\n</TEXT>\n</DOCUMENT>\n"
               "<DOCUMENT>\n<TYPE>EX-13\n<TEXT>\nItem 1.  Not this one\n</TEXT>\n</DOCUMENT>")
    text, meta, warns = select_and_normalize(txt_doc)
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

    # exhibits-only submission: EDGAR's own metadata refuses it for us
    ex = "<DOCUMENT>\n<TYPE>EX-21\n<TEXT>\nsubsidiaries\n</TEXT>\n</DOCUMENT>"
    assert select_and_normalize(ex)[1]["form_type"] is None

    print("[normalize self-check] ok")


if __name__ == "__main__":
    _demo()
