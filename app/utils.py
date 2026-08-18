import re


def format_staff_name(raw: str) -> str:
    """Free-form staff name -> 'FIRST L.' for the label/print log, e.g.
    "David Draper" -> "DAVID D.". Single-word input (bare initials like
    "DD") is just upper-cased, since there's no last name to abbreviate."""
    words = raw.strip().split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0].upper()
    return f"{words[0].upper()} {words[-1][0].upper()}."


def item_initials(name: str) -> str:
    """Two-letter picker stand-in: first letter of the first two words
    ("BBQ Sauce" -> "BS"), or the first two letters of a single word.
    Non-letter characters (parens, hyphens, commas, digits, ...) are
    stripped first so the result is always letters only."""
    words = [w for w in (re.sub(r"[^A-Za-z]", "", w) for w in name.split()) if w]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    if words:
        return words[0][:2].upper()
    return "?"
