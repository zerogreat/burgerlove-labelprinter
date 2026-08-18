"""Builds ZPL for a 1"x1" label on the physical printer's real resolution:
300 dpi (300x300 dots), confirmed from the printer's own config printout
(RESOLUTION "12/MM" and a self-calibrated LABEL LENGTH of ~315 dots, both
consistent with 300 dpi and inconsistent with the 203 dpi originally
assumed in PLAN.md).

Layout: bold left-aligned title, a bordered two-row Prep/Use-by table with
a divider between the (right-justified) label column and the value column,
and the staff name at the bottom. Font 0 has no bold weight, so "bold"
text is faked by printing the same field twice, offset by one dot.

Vertical centering note: ^A0N,h,w reserves descender space below the
baseline that all-caps/digit text (dates) never uses, so naively centering
by the declared font height renders too high. Row y-values below add a
small empirical downward correction (~14% of font height) on top of the
naive center so the visible ink — not the invisible descender padding —
sits in the middle of its row.
"""

from datetime import date

DOTS_PER_INCH = 300
LABEL_DOTS = DOTS_PER_INCH  # 1"x1" label

BORDER_THICKNESS = 3

CONTENT_LEFT = 24
CONTENT_RIGHT = LABEL_DOTS - 24
CONTENT_WIDTH = CONTENT_RIGHT - CONTENT_LEFT  # 252

TABLE_TOP = 112
ROW1_HEIGHT = 46
ROW2_HEIGHT = 62
TABLE_HEIGHT = ROW1_HEIGHT + ROW2_HEIGHT
DIVIDER_Y = TABLE_TOP + ROW1_HEIGHT  # horizontal divider between rows

LABEL_COL_WIDTH = 92  # "Prep" / "Use by" column
LABEL_RIGHT_PAD = 4  # gap between the right-justified label and the divider
VALUE_X = CONTENT_LEFT + LABEL_COL_WIDTH + 10

LABEL_FONT = 24  # shared by "Prep" and "Use by" captions
PREP_VALUE_FONT = 30
USE_BY_VALUE_FONT = 40

NAME_FONT = 36
NAME_LINE_HEIGHT = NAME_FONT  # matches the old FB line spacing of 0
NAME_MAX_LINES = 2
NAME_TOP = 26

# Per-character width estimates (as a fraction of font height) for the
# name-cropping math below. We have no real metrics for the printer's
# built-in font 0, and can't call out to Labelary at print time (the
# restaurant has no internet), so this approximates a typical proportional
# sans-serif instead of assuming every character is the same width.
_NARROW_CHARS = set("iIlj.,:;'!|\"")
_WIDE_CHARS = set("mMWw@")

# Compensates for print registration drift on the physical printer, and
# for the overall top/bottom balance of the label content — a software
# nudge on top of (not a substitute for) the printer's own gap sensor
# calibration. Positive moves the whole label DOWN; negative moves it UP.
LABEL_TOP_OFFSET = 5


def _escape(text: str) -> str:
    return text.replace("^", "").replace("~", "").strip()


def _format_date(iso_date: str) -> str:
    """ISO 'YYYY-MM-DD' -> 'MON DD', e.g. '2026-08-17' -> 'AUG 17'."""
    d = date.fromisoformat(iso_date)
    return f"{d.strftime('%b').upper()} {d.day:02d}"


def _centered_y(row_top: int, row_height: int, font: int) -> int:
    return row_top + (row_height - font) // 2 + round(font * 0.14)


def _char_width(ch: str, font: int) -> float:
    # Calibrated down from an earlier pass after real printouts showed
    # "Bacon (Cooked)" fitting on one line at this font/width — the
    # original multipliers were estimating it as too wide to fit.
    if ch == " ":
        return font * 0.26
    if ch in _NARROW_CHARS:
        return font * 0.30
    if ch in _WIDE_CHARS:
        return font * 0.72
    if ch.isupper():
        return font * 0.56
    if ch.isdigit():
        return font * 0.52
    return font * 0.46  # lowercase / default


def _text_width(text: str, font: int) -> float:
    return sum(_char_width(ch, font) for ch in text)


def _fit_chars(text: str, font: int, max_width: int) -> str:
    """Longest prefix of text whose estimated width fits max_width."""
    width = 0.0
    for i, ch in enumerate(text):
        width += _char_width(ch, font)
        if width > max_width:
            return text[:i]
    return text


def _wrap_and_crop(text: str, font: int, max_width: int, max_lines: int) -> list[str]:
    """Greedy word-wrap using per-character width estimates (see
    _char_width). Full lines wrap at word boundaries; the final allowed
    line hard-crops whatever text remains character-by-character (mid-word
    if needed) so it's filled as much as possible instead of dropping a
    word that doesn't quite fit whole. No ellipsis — anything past the
    last line is simply left off. ZPL's own ^FB auto-wrap overlaps text
    instead of clipping when content overflows its line count, so this is
    computed here instead of left to the printer."""
    words = text.split()
    lines: list[str] = []

    while words and len(lines) < max_lines - 1:
        current = ""
        while words:
            candidate = f"{current} {words[0]}".strip()
            if _text_width(candidate, font) > max_width:
                break
            current = candidate
            words.pop(0)

        if not current:
            # a single word alone is wider than the line — take what fits
            # and carry the rest forward as the start of the next word
            fitted = _fit_chars(words[0], font, max_width) or words[0][:1]
            current = fitted
            words[0] = words[0][len(fitted):]

        lines.append(current)

    if words and len(lines) < max_lines:
        lines.append(_fit_chars(" ".join(words), font, max_width))

    return lines


def build_zpl(food_name: str, initials: str, prepped_date: str, expiration_date: str | None) -> str:
    name = _escape(food_name)
    init = _escape(initials)
    prepped = _format_date(prepped_date)
    use_by = _format_date(expiration_date) if expiration_date else "—"  # em dash

    prep_label_y = _centered_y(TABLE_TOP, ROW1_HEIGHT, LABEL_FONT)
    prep_value_y = _centered_y(TABLE_TOP, ROW1_HEIGHT, PREP_VALUE_FONT)
    use_by_label_y = _centered_y(DIVIDER_Y, ROW2_HEIGHT, LABEL_FONT)
    use_by_value_y = _centered_y(DIVIDER_Y, ROW2_HEIGHT, USE_BY_VALUE_FONT)
    name_lines = _wrap_and_crop(name, NAME_FONT, CONTENT_WIDTH, NAME_MAX_LINES)

    lines = [
        "^XA",
        "^CI28",  # UTF-8, needed for the em dash fallback
        f"^PW{LABEL_DOTS}",
        f"^LL{LABEL_DOTS}",
        f"^LT{LABEL_TOP_OFFSET}",
    ]

    # title: bold (double-struck), left-aligned, hard-cropped to 2 lines
    for i, line_text in enumerate(name_lines):
        y = NAME_TOP + i * NAME_LINE_HEIGHT
        lines.append(f"^FO{CONTENT_LEFT},{y}^A0N,{NAME_FONT},{NAME_FONT}^FD{line_text}^FS")
        lines.append(f"^FO{CONTENT_LEFT + 1},{y + 1}^A0N,{NAME_FONT},{NAME_FONT}^FD{line_text}^FS")

    lines += [
        # table: outer box, row divider, column divider
        f"^FO{CONTENT_LEFT},{TABLE_TOP}^GB{CONTENT_WIDTH},{TABLE_HEIGHT},{BORDER_THICKNESS},B^FS",
        f"^FO{CONTENT_LEFT},{DIVIDER_Y}^GB{CONTENT_WIDTH},{BORDER_THICKNESS},{BORDER_THICKNESS},B^FS",
        f"^FO{CONTENT_LEFT + LABEL_COL_WIDTH},{TABLE_TOP}^GB{BORDER_THICKNESS},{TABLE_HEIGHT},{BORDER_THICKNESS},B^FS",
        # row 1: Prep (right-justified label, no colon, not bold)
        f"^FO{CONTENT_LEFT},{prep_label_y}^A0N,{LABEL_FONT},{LABEL_FONT}^FB{LABEL_COL_WIDTH - LABEL_RIGHT_PAD},1,0,R^FDPrep^FS",
        f"^FO{VALUE_X},{prep_value_y}^A0N,{PREP_VALUE_FONT},{PREP_VALUE_FONT}^FD{prepped}^FS",
        # row 2: Use by (bold right-justified label, no colon; much bigger bold value)
        f"^FO{CONTENT_LEFT},{use_by_label_y}^A0N,{LABEL_FONT},{LABEL_FONT}^FB{LABEL_COL_WIDTH - LABEL_RIGHT_PAD},1,0,R^FDUse by^FS",
        f"^FO{CONTENT_LEFT + 1},{use_by_label_y + 1}^A0N,{LABEL_FONT},{LABEL_FONT}^FB{LABEL_COL_WIDTH - LABEL_RIGHT_PAD},1,0,R^FDUse by^FS",
        f"^FO{VALUE_X},{use_by_value_y}^A0N,{USE_BY_VALUE_FONT},{USE_BY_VALUE_FONT}^FD{use_by}^FS",
        f"^FO{VALUE_X + 1},{use_by_value_y + 1}^A0N,{USE_BY_VALUE_FONT},{USE_BY_VALUE_FONT}^FD{use_by}^FS",
        # staff name, bottom
        f"^FO{CONTENT_LEFT},236^A0N,28,28^FB{CONTENT_WIDTH},1,0,L^FD{init}^FS",
        "^XZ",
    ]
    return "\n".join(lines)
