"""Renders a ZPL label to a PNG via the Labelary API, for on-screen preview
during development. Never used by the real /print flow — this is purely a
"what would this look like" tool for dialing in app/zpl.py before testing
against the physical printer.
"""

import urllib.error
import urllib.request

# 12dpmm = 300 dpi, matching the physical printer's actual resolution
# (confirmed from its config printout — see app/zpl.py).
LABELARY_URL = "https://api.labelary.com/v1/printers/12dpmm/labels/1x1/0/"


class PreviewError(Exception):
    pass


def render_preview_png(zpl: str) -> bytes:
    req = urllib.request.Request(
        LABELARY_URL,
        data=zpl.encode("utf-8"),
        headers={"Accept": "image/png"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise PreviewError(f"Labelary rejected the ZPL ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise PreviewError(f"Could not reach the label preview service: {exc.reason}") from exc
