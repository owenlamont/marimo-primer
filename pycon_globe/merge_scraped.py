"""Merge scraped schedule JSON files into the talk and event tables.

Each input file is `<event_slug>.json` as written by the scraping agents. Re-running is
safe: every scraped event's earlier `schedule` rows are replaced, including by nothing
when its re-scrape found no talks.
"""

from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import Annotated, Any, Final

import orjson
from pandera.typing.polars import DataFrame
import polars as pl
import pyarrow.parquet as pq
from pycons_schema import Pycons
from talks_schema import TalkKind, Talks, TalkSource
import typer


_PUBLIC: Final = Path(__file__).parent.parent / "public"
_TALKS_SCHEMA: Final = pl.Schema(
    {
        "event_slug": pl.String,
        "talk_title": pl.String,
        "speakers": pl.List(pl.String),
        "recorded": pl.Date,
        "source": pl.Enum([s.value for s in TalkSource]),
        "source_url": pl.String,
        "kind": pl.Enum([k.value for k in TalkKind]),
    }
)

app = typer.Typer(
    add_completion=False, context_settings={"help_option_names": ["-h", "--help"]}
)


def read_events(scraped_dir: Path) -> list[dict[str, Any]]:
    """Read every scraped file.

    Returns:
        One mapping per file, including events whose talks were not found.
    """
    return [
        orjson.loads(path.read_bytes()) for path in sorted(scraped_dir.glob("*.json"))
    ]


def scraped_talks(
    events: Iterable[Mapping[str, Any]], *, source: TalkSource
) -> DataFrame[Talks]:
    """Flatten scraped events into one row per talk.

    Returns:
        The talks; no rows when none were found.
    """
    rows = [
        {
            "event_slug": event["event_slug"],
            "talk_title": talk["title"].strip(),
            "speakers": [s.strip() for s in talk["speakers"] if s.strip()],
            "recorded": None,
            "source": source.value,
            "source_url": event["schedule_url"],
            "kind": talk["kind"],
        }
        for event in events
        for talk in event["talks"]
    ]
    return Talks.validate(pl.DataFrame(rows, schema=_TALKS_SCHEMA))


def read_talks(path: Path) -> DataFrame[Talks]:
    """Read `talks.parquet`, dropping any index column pandas wrote.

    Returns:
        The talks, validated.
    """
    talks = pl.read_parquet(path).drop("__index_level_0__", strict=False)
    return Talks.validate(talks.cast(_TALKS_SCHEMA))


def merge_talks(
    *,
    talks: DataFrame[Talks],
    scraped: DataFrame[Talks],
    scraped_slugs: Collection[str],
    source: TalkSource,
) -> DataFrame[Talks]:
    """Replace every scraped event's earlier rows from `source` with the new ones.

    An event in `scraped_slugs` with no rows in `scraped` loses its old rows.

    Returns:
        The combined talks.
    """
    stale = (pl.col("source") == source.value) & pl.col("event_slug").is_in(
        list(scraped_slugs)
    )
    return Talks.validate(pl.concat([talks.filter(~stale), scraped]))


def schedule_urls(events: Iterable[Mapping[str, Any]]) -> pl.DataFrame:
    """Map each scraped event whose talks were found to where they came from.

    Returns:
        `event_slug` and `scraped_url` columns.
    """
    return pl.DataFrame(
        [
            {"event_slug": e["event_slug"], "scraped_url": e["schedule_url"]}
            for e in events
            if e["talks"]
        ],
        schema={"event_slug": pl.String, "scraped_url": pl.String},
    )


def recount(
    *, pycons: DataFrame[Pycons], talks: DataFrame[Talks], urls: pl.DataFrame
) -> DataFrame[Pycons]:
    """Set each event's counts from `talks`, and its `schedule_url` where scraped.

    Returns:
        `pycons` with the same rows and column order.
    """
    per_event = talks.group_by("event_slug").agg(
        talk_count=pl.len().cast(pl.UInt32),
        speaker_count=pl.col("speakers")
        .explode(empty_as_null=True)
        .drop_nulls()
        .n_unique()
        .cast(pl.UInt32),
    )
    recounted = (
        pycons.drop("talk_count", "speaker_count")
        .join(per_event, on="event_slug", how="left", maintain_order="left")
        .join(urls, on="event_slug", how="left", maintain_order="left")
        .with_columns(
            pl.col("talk_count", "speaker_count").fill_null(0),
            schedule_url=pl.coalesce("scraped_url", "schedule_url"),
        )
        .select(pycons.columns)
    )
    return Pycons.validate(recounted)


def write_pycons(pycons: DataFrame[Pycons], path: Path) -> None:
    """Write `pycons` over `path`, keeping the file's GeoParquet `geo` metadata."""
    geo = pq.read_metadata(path).metadata[b"geo"].decode()
    pycons.write_parquet(path, metadata={"geo": geo})


@app.command()
def main(
    scraped_dir: Path,
    *,
    write: Annotated[
        bool, typer.Option(help="Write the tables; without it, only report.")
    ] = False,
    source: Annotated[
        TalkSource, typer.Option(help="Where SCRAPED_DIR's talks came from.")
    ] = TalkSource.SCHEDULE,
) -> None:
    """Merge the scraped files in SCRAPED_DIR into public/."""
    events = read_events(scraped_dir)
    talks = merge_talks(
        talks=read_talks(_PUBLIC / "talks.parquet"),
        scraped=scraped_talks(events, source=source),
        scraped_slugs={e["event_slug"] for e in events},
        source=source,
    )
    pycons_path = _PUBLIC / "pycons.parquet"
    pycons = Pycons.validate(
        pl.read_parquet(pycons_path).drop("__index_level_0__", strict=False)
    )
    known = pl.col("event_slug").is_in(pycons["event_slug"].implode())
    orphans = talks.filter(~known)
    talks = Talks.validate(talks.filter(known))
    pycons = recount(pycons=pycons, talks=talks, urls=schedule_urls(events))
    events_with_talks = pycons.filter(pl.col("talk_count") > 0)["event_slug"]
    print(
        f"{len(events)} scraped events; {talks.height} talks in total "
        f"({orphans.height} dropped for events not in pycons.parquet); "
        f"{events_with_talks.n_unique()} of {pycons['event_slug'].n_unique()} "
        "events have talks"
    )
    if write:
        talks.write_parquet(_PUBLIC / "talks.parquet")
        write_pycons(pycons, pycons_path)


if __name__ == "__main__":
    app()
