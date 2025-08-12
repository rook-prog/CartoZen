# utils/font_utils.py
# Per-element font style helpers for CartoZen

STYLE_MAP = {
    "Normal": {"fontweight": "normal", "fontstyle": "normal"},
    "Bold": {"fontweight": "bold", "fontstyle": "normal"},
    "Italic": {"fontweight": "normal", "fontstyle": "italic"},
    "Bold-Italic": {"fontweight": "bold", "fontstyle": "italic"},
}

def get_style(style_name: str) -> dict:
    """Return a dict with matplotlib text kwargs for the given style name."""
    return STYLE_MAP.get(style_name, STYLE_MAP["Normal"])
