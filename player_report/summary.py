"""The facts behind the report's info cards: one player's season, from StatsBomb and Transfermarkt."""

import pandas as pd

from player_report.transfermarkt import player_profile


def _age(date_of_birth: str | None, on_date) -> int | None:
    """Age in whole years on a given date."""
    if date_of_birth is None:
        return None
    born, on = pd.Timestamp(date_of_birth), pd.Timestamp(on_date)
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def _value_change(start: dict | None, end: dict | None) -> float | None:
    """Relative change in market value, e.g. 0.51 for +51%."""
    if start is None or end is None:
        return None
    return (end["eur"] - start["eur"]) / start["eur"]


def season_summary(totals_row: pd.Series, sb_player: pd.Series, team: str, league: str,
                   cache_dir, overrides: dict[int, int] | None = None) -> dict:
    """Everything the info cards show for one player's season.

    `totals_row` is the player's row of `statsbomb_tools.players.season_totals`; `sb_player` is
    their row of a StatsBomb lineup (nickname, country, jersey number). Market values are taken
    around the player's own first and last match of the season.
    """
    profile = player_profile(sb_player, totals_row["first_match"], totals_row["last_match"], cache_dir, overrides)
    name = sb_player["player_nickname"] if pd.notna(sb_player["player_nickname"]) else sb_player["player_name"]

    return {
        "name": name,
        "shirt_name": (profile["last_name"] or name.split()[-1]).upper(),
        "jersey_number": int(sb_player["jersey_number"]),
        "team": team,
        "league": league,
        "position": totals_row["position"],
        "nationality": sb_player["country"],
        "date_of_birth": profile["date_of_birth"],
        "age": _age(profile["date_of_birth"], totals_row["last_match"]),
        "foot": profile["foot"],
        "value_start": profile["value_start"],
        "value_end": profile["value_end"],
        "value_change": _value_change(profile["value_start"], profile["value_end"]),
        "appearances": int(totals_row["appearances"]),
        "starts": int(totals_row["starts"]),
        "minutes": int(totals_row["minutes"]),
        "goals": int(totals_row["goals"]),
        "penalty_goals": int(totals_row["penalty_goals"]),
        "assists": int(totals_row["assists"]),
    }
