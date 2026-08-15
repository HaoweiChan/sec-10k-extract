"""10-K item-level extraction. Contract: specs/001-sec10k-contract.md."""


def extract_items(path):
    """Extract items from a 10-K filing.

    Returns {"normalized_text": str, "items": [ {item, part, title, start,
    end, status, confidence}, ... ]} per specs/001-sec10k-contract.md.
    """
    raise NotImplementedError("extraction pipeline not implemented yet")
