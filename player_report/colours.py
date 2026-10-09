"""Club colours (data/club_colours.csv) and helpers for readable text on top of them."""

from pathlib import Path

import pandas as pd
from matplotlib.colors import to_hex, to_rgb

DARK_TEXT, LIGHT_TEXT = "#1A1A1A", "white"


def load_club_colours(path: Path) -> pd.DataFrame:
    """Primary and secondary colour per club, indexed by StatsBomb team name."""
    return pd.read_csv(path, index_col="team")


def _luminance(colour) -> float:
    """WCAG relative luminance, 0 (black) to 1 (white)."""
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in to_rgb(colour)]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def text_colour(background) -> str:
    """Dark or white text, whichever contrasts more with the background."""
    lum = _luminance(background)
    dark_contrast = (lum + 0.05) / (_luminance(DARK_TEXT) + 0.05)
    light_contrast = 1.05 / (lum + 0.05)
    return DARK_TEXT if dark_contrast >= light_contrast else LIGHT_TEXT


def tint(colour, amount: float) -> str:
    """The colour mixed with white: amount=0.1 is a very light tint, 1 the colour itself."""
    return to_hex([1 - amount * (1 - c) for c in to_rgb(colour)])
