"""Player profile data from Transfermarkt (Kaggle dataset "davidcariboo/player-scores"), cached per player and season."""

import json
import unicodedata
from pathlib import Path

import kagglehub
import pandas as pd

DATASET = "davidcariboo/player-scores"
SUMMER_UPDATE_DAYS = 90


def load_table(name: str, **read_csv_kwargs) -> pd.DataFrame:
    """One CSV of the dataset, e.g. "players" (kagglehub downloads the dataset once and caches it)."""
    path = Path(kagglehub.dataset_download(DATASET))
    return pd.read_csv(path / f"{name}.csv", **read_csv_kwargs)


def _normalise(text) -> str:
    """Lowercase without accents, so "Higuaín" matches "Higuain". Missing values become ""."""
    if pd.isna(text):
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()


def find_player(players: pd.DataFrame, full_name: str, nickname: str | None, country: str) -> int:
    """Transfermarkt id of a StatsBomb player, matched by name among players of the same citizenship.

    First tries the StatsBomb nickname against the Transfermarkt name ("Gonzalo Higuaín");
    then requires Transfermarkt's first and last name to appear in the StatsBomb full name.
    """
    citizens = players[players["country_of_citizenship"].map(_normalise) == _normalise(country)]

    found = citizens[citizens["name"].map(_normalise) == _normalise(nickname)]
    if len(found) != 1:
        sb_words = set(_normalise(full_name).split())
        tm_words = (citizens["first_name"].map(_normalise) + " " + citizens["last_name"].map(_normalise)).str.split()
        found = citizens[tm_words.map(lambda words: set(words) <= sb_words)]

    if len(found) != 1:
        candidates = found[["player_id", "name", "date_of_birth"]].to_dict("records")
        raise LookupError(f"No unique Transfermarkt match for {full_name!r}: {candidates}. Add it to `overrides`.")
    return int(found["player_id"].iloc[0])


def _valuation(row) -> dict | None:
    """A valuation row as {"date", "eur"}, or None."""
    if row is None:
        return None
    return {"date": row["date"].strftime("%Y-%m-%d"), "eur": int(row["market_value_in_eur"])}


def season_valuations(valuations: pd.DataFrame, tm_id: int, first_match, last_match) -> tuple[dict | None, dict | None]:
    """Market value at the start and end of a season.

    Start: the latest valuation on or before the first match.
    End: the summer update, i.e. the first valuation within SUMMER_UPDATE_DAYS after the
    last match; if there is none, the latest valuation on or before the last match.
    """
    first_match, last_match = pd.Timestamp(first_match), pd.Timestamp(last_match)
    player = valuations[valuations["player_id"] == tm_id].sort_values("date")

    before_start = player[player["date"] <= first_match]
    summer = player[(player["date"] > last_match)
                    & (player["date"] <= last_match + pd.Timedelta(days=SUMMER_UPDATE_DAYS))]
    before_end = player[player["date"] <= last_match]

    start = before_start.iloc[-1] if len(before_start) else None
    end = summer.iloc[0] if len(summer) else (before_end.iloc[-1] if len(before_end) else None)
    return _valuation(start), _valuation(end)


def player_profile(sb_player: pd.Series, first_match, last_match, cache_dir: Path,
                   overrides: dict[int, int] | None = None) -> dict:
    """Transfermarkt profile of a StatsBomb player for one season, read from cache if already built.

    `sb_player` is a row of a StatsBomb lineup (player_id, player_name, player_nickname, country).
    `overrides` maps StatsBomb player ids to Transfermarkt ids, for players the name matching can't resolve.
    """
    first_match, last_match = pd.Timestamp(first_match), pd.Timestamp(last_match)
    sb_id = int(sb_player["player_id"])
    path = Path(cache_dir) / f"{sb_id}_{first_match.year}_{last_match.year}.json"
    if path.exists():
        return json.loads(path.read_text())

    players = load_table("players")
    tm_id = (overrides or {}).get(sb_id) or find_player(
        players, sb_player["player_name"], sb_player["player_nickname"], sb_player["country"])
    tm = players.set_index("player_id").loc[tm_id]
    value_start, value_end = season_valuations(
        load_table("player_valuations", parse_dates=["date"]), tm_id, first_match, last_match)

    profile = {
        "statsbomb_id": sb_id,
        "transfermarkt_id": tm_id,
        "name": tm["name"],
        "last_name": None if pd.isna(tm["last_name"]) else tm["last_name"],
        "date_of_birth": None if pd.isna(tm["date_of_birth"]) else str(tm["date_of_birth"])[:10],
        "foot": None if pd.isna(tm["foot"]) else tm["foot"],
        "value_start": value_start,
        "value_end": value_end,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    return profile
