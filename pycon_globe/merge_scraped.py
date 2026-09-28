"""Merge scraped schedule JSON files into the talk and event tables.

Each input file is `<event_slug>.json` as written by the scraping agents. Re-running is
safe: an event's earlier `schedule` rows are replaced, not duplicated.
"""

from pathlib import Path
from typing import Annotated, Final

import geopandas as gpd
import orjson
import pandas as pd
import typer


_PUBLIC: Final = Path(__file__).parent.parent / "public"
_SOURCE: Final = "schedule"

app = typer.Typer(
    add_completion=False, context_settings={"help_option_names": ["-h", "--help"]}
)


def read_scraped(scraped_dir: Path) -> pd.DataFrame:
    """Read every scraped file into one row per talk.

    Returns:
        The talks, in `talks.parquet`'s columns plus `kind`.
    """
    rows = [
        {
            "event_slug": event["event_slug"],
            "talk_title": talk["title"].strip(),
            "speakers": [s.strip() for s in talk["speakers"] if s.strip()],
            "recorded": pd.NaT,
            "source": _SOURCE,
            "source_url": event["schedule_url"],
            "kind": talk["kind"],
        }
        for path in sorted(scraped_dir.glob("*.json"))
        for event in [orjson.loads(path.read_bytes())]
        for talk in event["talks"]
    ]
    return pd.DataFrame(rows)


def merge_talks(*, talks: pd.DataFrame, scraped: pd.DataFrame) -> pd.DataFrame:
    """Replace each scraped event's earlier `schedule` rows with the new ones.

    Returns:
        The combined talks table.
    """
    stale = (talks["source"] == _SOURCE) & talks["event_slug"].isin(
        scraped["event_slug"]
    )
    return pd.concat([talks[~stale], scraped], ignore_index=True)


def read_schedule_urls(scraped_dir: Path) -> pd.Series:
    """Read where each scraped event's talks came from.

    Returns:
        `schedule_url` indexed by `event_slug`, for events whose talks were found.
    """
    events = [orjson.loads(path.read_bytes()) for path in scraped_dir.glob("*.json")]
    return pd.Series(
        {e["event_slug"]: e["schedule_url"] for e in events if e["talks"]},
        name="schedule_url",
        dtype="string",
    )


def recount(*, pycons: gpd.GeoDataFrame, talks: pd.DataFrame) -> gpd.GeoDataFrame:
    """Set each event's talk and distinct-speaker counts from the talks table.

    Returns:
        A copy of `pycons` with `talk_count` and `speaker_count` recomputed.
    """
    per_event = pd.DataFrame(
        {
            "talk_count": talks.groupby("event_slug").size(),
            "speaker_count": talks.explode("speakers")
            .groupby("event_slug")["speakers"]
            .nunique(),
        }
    )
    counts = pycons[["event_slug"]].join(per_event, on="event_slug")
    recounted = pycons.assign(
        talk_count=counts["talk_count"].fillna(0).astype("uint32"),
        speaker_count=counts["speaker_count"].fillna(0).astype("uint32"),
    )
    return gpd.GeoDataFrame(recounted, geometry="geometry", crs=pycons.crs)


@app.command()
def main(
    scraped_dir: Path,
    *,
    write: Annotated[
        bool, typer.Option(help="Write the tables; without it, only report.")
    ] = False,
) -> None:
    """Merge the scraped files in SCRAPED_DIR into public/."""
    scraped = read_scraped(scraped_dir)
    talks = merge_talks(
        talks=pd.read_parquet(_PUBLIC / "talks.parquet"), scraped=scraped
    )
    pycons = recount(pycons=gpd.read_parquet(_PUBLIC / "pycons.parquet"), talks=talks)
    urls = read_schedule_urls(scraped_dir)
    known = pycons.get("schedule_url", pd.Series(pd.NA, index=pycons.index))
    pycons = pycons.assign(
        schedule_url=pycons["event_slug"].map(urls).fillna(known).astype("string")
    )
    events = pycons.drop_duplicates("event_slug")
    print(
        f"{scraped['event_slug'].nunique()} scraped events, {len(scraped)} talks; "
        f"{len(talks)} talks in total; "
        f"{(events['talk_count'] > 0).sum()} of {len(events)} events now have talks"
    )
    if write:
        talks.to_parquet(_PUBLIC / "talks.parquet")
        pycons.to_parquet(_PUBLIC / "pycons.parquet")


if __name__ == "__main__":
    app()
