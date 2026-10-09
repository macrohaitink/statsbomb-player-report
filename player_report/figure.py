"""One-page player report: identity panel, info cards, form chart and percentile pizza."""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path
from mplsoccer import VerticalPitch
from scipy.ndimage import gaussian_filter

from player_report.colours import text_colour, tint
from player_report.radar import GROUP_COLOURS, pizza

TEXT, MUTED, CARD = "#1A1A1A", "#6B6B6B", "white"
UP, DOWN = "#1B8A3A", "#C0392B"  # market value rise / fall (always shown with an arrow too)
FIGSIZE = (18, 7.6)
HEATMAP_ALPHA = 0.75  # opacity of the densest heatmap area, so pitch markings stay visible
HEATMAP_BINS = (72, 48)  # along the pitch length, across its width
HEATMAP_SMOOTHING = 3.5  # gaussian blur, in bins


def _euros(value: float) -> str:
    return f"€{value / 1e6:.0f}m"


def _cards(summary: dict, values: pd.Series, percentiles: pd.Series) -> list[tuple[str, str, str]]:
    """(label, value, note) for the nine info cards, in reading order."""
    dob = pd.Timestamp(summary["date_of_birth"]).strftime("%d.%m.%Y") if summary["date_of_birth"] else "–"
    start, end, change = summary["value_start"], summary["value_end"], summary["value_change"]
    value = f"{_euros(start['eur'])} → {_euros(end['eur'])}" if start and end else "–"
    trend = "" if change is None else f"{'▲' if change >= 0 else '▼'} {abs(change):.0%}"
    return [
        ("Date of birth", dob, f"age {summary['age']}"),
        ("Nationality", summary["nationality"], ""),
        ("Foot", (summary["foot"] or "–").capitalize(), ""),
        (summary["league"], summary["team"], ""),
        ("Market value", value, trend),
        ("Minutes", f"{summary['minutes']:,}", f"{summary['minutes'] / summary['appearances']:.0f} per app."),
        ("Appearances", str(summary["appearances"]), f"{summary['starts']} starts"),
        ("Goals + assists", f"{summary['goals']} + {summary['assists']}", f"{summary['penalty_goals']} penalties"),
        ("npxG per 90", f"{values['npxg']:.2f}", f"{percentiles['npxg']:.0f}th percentile"),
    ]


# Outline of a shirt in a -1..1 box: (x, y, path code); the collar curves down towards (0, 0.48)
SHIRT = [
    (-0.28, 0.88, Path.MOVETO), (-0.62, 0.78, Path.LINETO), (-1.0, 0.42, Path.LINETO),
    (-0.80, 0.16, Path.LINETO), (-0.58, 0.32, Path.LINETO), (-0.58, -0.92, Path.LINETO),
    (0.58, -0.92, Path.LINETO), (0.58, 0.32, Path.LINETO), (0.80, 0.16, Path.LINETO),
    (1.0, 0.42, Path.LINETO), (0.62, 0.78, Path.LINETO), (0.28, 0.88, Path.LINETO),
    (0.0, 0.48, Path.CURVE3), (-0.28, 0.88, Path.CURVE3), (0, 0, Path.CLOSEPOLY),
]
SHIRT_NAME_MAX_SIZE = 13  # font size of short names
SHIRT_NAME_WIDTH = 85  # font size x characters that still fits across the shirt


def _draw_shirt(fig, rect, summary, colour, trim):
    """Club-coloured shirt with surname and number, as on the back of a kit; long names get smaller."""
    ax = fig.add_axes(rect)
    ax.set_xlim(-1.05, 1.05); ax.set_ylim(-1.05, 1.05); ax.set_aspect("equal"); ax.axis("off")
    x, y, codes = zip(*SHIRT)
    ax.add_patch(PathPatch(Path(list(zip(x, y)), codes), facecolor=colour, edgecolor=trim,
                           linewidth=3, joinstyle="round"))
    ink = text_colour(colour)
    name_size = min(SHIRT_NAME_MAX_SIZE, SHIRT_NAME_WIDTH / len(summary["shirt_name"]))
    ax.text(0, 0.34, summary["shirt_name"], ha="center", va="center", fontsize=name_size,
            fontweight="bold", color=ink)
    ax.text(0, -0.28, str(summary["jersey_number"]), ha="center", va="center", fontsize=40,
            fontweight="bold", color=ink)


def _draw_cards(fig, rect, cards, colour):
    """3 x 3 grid of white cards with a club-coloured accent bar."""
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 3); ax.set_ylim(0, 3); ax.axis("off")
    for i, (label, value, note) in enumerate(cards):
        x, y = i % 3 + 0.04, 2 - i // 3 + 0.06
        ax.add_patch(FancyBboxPatch((x, y), 0.92, 0.86, boxstyle="round,pad=0,rounding_size=0.08",
                                    facecolor=CARD, edgecolor="none"))
        ax.add_patch(FancyBboxPatch((x, y + 0.16), 0.03, 0.54, boxstyle="round,pad=0,rounding_size=0.015",
                                    facecolor=colour, edgecolor="none"))
        ax.text(x + 0.1, y + 0.66, label, fontsize=10, color=MUTED, va="center")
        ax.text(x + 0.1, y + 0.42, value, fontsize=15, fontweight="bold", color=TEXT, va="center")
        note_colour = UP if note.startswith("▲") else DOWN if note.startswith("▼") else MUTED
        ax.text(x + 0.1, y + 0.18, note, fontsize=9.5, color=note_colour, va="center")


def _draw_form(fig, rect, log, colour, accent):
    """npxG bars and goal markers for every match, on one shared axis."""
    ax = fig.add_axes(rect)
    ax.bar(range(len(log)), log["npxg"], width=0.7, color=colour, label="npxG", zorder=2)
    scored = log[log["goals"] > 0]
    ax.scatter(scored.index, scored["goals"], s=42, color=accent, edgecolor="white", linewidth=1.5,
               zorder=3, label="Goals")
    ax.set_xlim(-0.8, len(log) - 0.2)
    ax.set_ylim(0, max(log["goals"].max(), log["npxg"].max()) + 0.6)
    ax.set_xticks([0, len(log) - 1], [d.strftime("%d %b %Y") for d in log["match_date"].iloc[[0, -1]]])
    ax.yaxis.grid(True, color="#E2E2E2", linewidth=0.8, zorder=0)
    ax.tick_params(colors=MUTED, length=0, labelsize=9)
    ax.set_facecolor("none")
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#BBBBBB")
    ax.set_title("Match by match: npxG and goals", loc="left", fontsize=12, fontweight="bold", color=TEXT, pad=8)
    ax.legend(loc="upper right", frameon=False, fontsize=9, ncol=2, bbox_to_anchor=(1, 1.16))


def _draw_touches(fig, rect, touches, colour):
    """See-through heatmap of on-ball events on a vertical pitch, attacking upwards."""
    pitch = VerticalPitch(pitch_type="statsbomb", pitch_color=CARD, line_color="#B5B5B5",
                          linewidth=1, line_zorder=2)
    ax = fig.add_axes(rect)
    pitch.draw(ax=ax)
    rgb = to_rgb(colour)
    cmap = LinearSegmentedColormap.from_list("club", [(*rgb, 0), (*rgb, HEATMAP_ALPHA)])
    stats = pitch.bin_statistic(touches["x"], touches["y"], statistic="count", bins=HEATMAP_BINS)
    stats["statistic"] = gaussian_filter(stats["statistic"], HEATMAP_SMOOTHING)
    pitch.heatmap(stats, ax=ax, cmap=cmap, edgecolors="none", zorder=1)
    ax.set_title("Touches heat map", fontsize=11, color=TEXT, pad=6)


def player_report(summary: dict, values: pd.Series, percentiles: pd.Series, n_peers: int, peer_label: str,
                  log: pd.DataFrame, touches: pd.DataFrame, colours: pd.Series):
    """The full one-page report. `colours` is the club's row of the club colours table."""
    primary, secondary = colours["primary"], colours["secondary"]
    background = tint(primary, 0.08)
    fig = plt.figure(figsize=FIGSIZE, facecolor=background)

    # Left: identity and heatmap
    _draw_shirt(fig, [0.015, 0.70, 0.095, 0.23], summary, primary, secondary)
    fig.text(0.115, 0.845, summary["name"], fontsize=22, fontweight="bold", color=TEXT, va="center")
    fig.text(0.115, 0.775, f"{summary['position']} · {summary['team']}", fontsize=13, color=MUTED, va="center")
    _draw_touches(fig, [0.035, 0.07, 0.17, 0.58], touches, primary)

    # Middle: info cards and form
    _draw_cards(fig, [0.29, 0.42, 0.36, 0.53], _cards(summary, values, percentiles), primary)
    _draw_form(fig, [0.305, 0.09, 0.335, 0.25], log, primary, secondary)

    # Right: percentile pizza with caption and group legend
    pizza_ax = fig.add_axes([0.695, 0.17, 0.26, 0.68], projection="polar")
    pizza(values, percentiles, ax=pizza_ax, background=background)
    fig.text(0.825, 0.06, f"Percentile vs. {n_peers} {peer_label} (per 90 unless %)",
             ha="center", fontsize=10, color=MUTED)
    for i, (group, colour) in enumerate(GROUP_COLOURS.items()):
        fig.text(0.75 + i * 0.06, 0.025, f"■ {group}", color=colour, fontsize=10)

    fig.text(0.015, 0.015, "Data: StatsBomb open data · Transfermarkt (Kaggle: davidcariboo/player-scores)",
             fontsize=8.5, color=MUTED)
    return fig
