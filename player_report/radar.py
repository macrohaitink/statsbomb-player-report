"""Percentile pizza chart of a player's metrics, coloured by metric group (mplsoccer PyPizza)."""

import pandas as pd
from mplsoccer import PyPizza

GROUP_COLOURS = {"Shooting": "#D7263D", "Creating": "#F28E2B", "Possession": "#2F6DB5"}
VALUE_TEXT_COLOURS = {"Shooting": "white", "Creating": "#1A1A1A", "Possession": "white"}
TEXT, GRID, BACKGROUND = "#1A1A1A", "#C8C8C8", "white"

STRIKER_METRICS = [  # (metric column, label, group), drawn clockwise from the top
    ("np_goals", "Non-penalty\ngoals", "Shooting"),
    ("npxg", "npxG", "Shooting"),
    ("np_shots", "Shots", "Shooting"),
    ("xg_per_shot", "xG per\nshot", "Shooting"),
    ("shots_on_target_pct", "Shots on\ntarget %", "Shooting"),
    ("assists", "Assists", "Creating"),
    ("xa", "xA", "Creating"),
    ("key_passes", "Key\npasses", "Creating"),
    ("box_receptions", "Box\nreceptions", "Creating"),
    ("successful_dribbles", "Successful\ndribbles", "Possession"),
    ("pass_completion_pct", "Pass\ncompletion %", "Possession"),
    ("progressive_passes", "Progressive\npasses", "Possession"),
    ("progressive_carries", "Progressive\ncarries", "Possession"),
]


def _format(value: float, column: str) -> str:
    """Percentages as whole numbers ("52%"), everything else with two decimals."""
    return f"{value:.0f}%" if column.endswith("_pct") else f"{value:.2f}"


def pizza(values: pd.Series, percentiles: pd.Series, metrics=STRIKER_METRICS, ax=None, background=BACKGROUND):
    """Slices sized by percentile, labelled with the actual value. Returns (fig, ax).

    `values` and `percentiles` are one player's rows of player_metrics and percentiles.
    `ax`, if given, must be a polar axes (e.g. fig.add_subplot(projection="polar")).
    """
    columns, labels, groups = zip(*metrics)
    colours = [GROUP_COLOURS[group] for group in groups]

    baker = PyPizza(
        params=list(labels), background_color=background,
        straight_line_color="white", straight_line_lw=1,
        last_circle_color=GRID, last_circle_lw=1,
        other_circle_color=GRID, other_circle_lw=0.8, other_circle_ls=":",
        inner_circle_size=18,
    )
    return baker.make_pizza(
        [round(percentiles[c]) for c in columns],
        alt_text_values=[_format(values[c], c) for c in columns],
        ax=ax, figsize=(8, 8), param_location=117,
        slice_colors=colours, color_blank_space="same", blank_alpha=0.2,
        value_colors=[VALUE_TEXT_COLOURS[g] for g in groups], value_bck_colors=colours,
        kwargs_slices=dict(edgecolor="white", linewidth=2, zorder=2),
        kwargs_params=dict(color=TEXT, fontsize=10, va="center"),
        kwargs_values=dict(fontsize=9, zorder=3,
                           bbox=dict(edgecolor="white", boxstyle="round,pad=0.3", lw=1)),
    )
