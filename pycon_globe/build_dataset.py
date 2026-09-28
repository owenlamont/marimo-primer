"""Seed the PyCon event and talk tables the globe demo reads, from 2020 onwards.

A one-off starting point, kept as the record of where the seed came from: its
`events.parquet` was since hand-edited and reshaped into `pycons.parquet`, one
GeoParquet row per event and place, so it refuses to overwrite either. Events,
dates, locations and websites come from python-organizers. Talks come from PyVideo,
which has recorded talks for only some of those events; the rest are filled by hand
from each event's website. PyVideo events with no python-organizers row are kept with
a null location, for `locations_manual.toml` or a hand edit to fill. Both upstream
datasets are CC0.
"""

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import tomllib
from typing import Final

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.location import Location
import orjson
import polars as pl


_HERE: Final = Path(__file__).parent
_DATA_DIR: Final = _HERE.parent / "public"
_SOURCES_DIR: Final = _HERE / ".sources"
_MANUAL_LOCATIONS: Final = _HERE / "locations_manual.toml"
_GEOCODE_CACHE: Final = _DATA_DIR / "geocode_cache.parquet"

_PYVIDEO_URL: Final = "https://github.com/pyvideo/data.git"
_ORGANIZERS_URL: Final = "https://github.com/python-organizers/conferences.git"
_GEOCODER_USER_AGENT: Final = "marimo-primer-pycon-globe"
_GEOCODE_DELAY_SECONDS: Final = 1.1
_GEOCODE_TIMEOUT_SECONDS: Final = 10.0
_FIRST_YEAR: Final = 2020

# PyVideo and python-organizers spell some series differently; both sides are
# normalised by `_series_key` before this lookup.
_SERIES_ALIASES: Final[Mapping[str, str]] = {
    "pyconar": "pyconargentina",
    "pyconca": "pyconcanada",
    "pyconjapan": "pyconjp",
    "pyconapac": "pyconasiapacific",
    "pyconlt": "pyconlithuania",
    "pyconse": "pyconsweden",
    "pycontaiwan": "pycontw",
    "pyconbalkanbelgrade": "pyconbalkan",
    "pyconke": "pyconkenya",
    "pyconie": "pyconireland",
    "pycondepydata": "pyconde",
    "pycondepydataberlin": "pyconde",
    "pyconza": "pyconsouthafrica",
}


def _series_key(name: str) -> str:
    without_year = re.sub(r"\b(19|20)\d{2}\b", "", name.lower())
    key = re.sub(r"[^a-z0-9]+", "", without_year)
    return _SERIES_ALIASES.get(key, key)


def _refresh_clone(url: str, dest: Path) -> None:
    git = shutil.which("git") or "git"
    if dest.exists():
        subprocess.run([git, "-C", str(dest), "pull", "-q", "--ff-only"], check=True)
    else:
        subprocess.run([git, "clone", "-q", "--depth", "1", url, str(dest)], check=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class Tables:
    events: pl.DataFrame
    talks: pl.DataFrame


def _event_year(event_dir: Path) -> int:
    year = re.search(r"(\d{4})$", event_dir.name)
    return int(year.group(1)) if year else 0


def _pyvideo_event_dirs(pyvideo_dir: Path) -> Iterator[Path]:
    for event_dir in sorted(pyvideo_dir.iterdir()):
        if (
            "pycon" in event_dir.name
            and _event_year(event_dir) >= _FIRST_YEAR
            and (event_dir / "category.json").exists()
        ):
            yield event_dir


def read_pyvideo(pyvideo_dir: Path) -> Tables:
    """Read PyVideo's PyCon events and their recorded talks.

    Returns:
        The events, and their talks with `recorded` parsed to a date.
    """
    events = []
    talks = []
    for event_dir in _pyvideo_event_dirs(pyvideo_dir):
        year = _event_year(event_dir)
        title = orjson.loads((event_dir / "category.json").read_bytes())["title"]
        events.append({"event_slug": event_dir.name, "event_name": title, "year": year})
        for video_file in sorted((event_dir / "videos").glob("*.json")):
            video = orjson.loads(video_file.read_bytes())
            urls = [v["url"] for v in video.get("videos", []) if v.get("url")]
            talks.append(
                {
                    "event_slug": event_dir.name,
                    "talk_title": video["title"].strip(),
                    "speakers": [s.strip() for s in video["speakers"] if s.strip()],
                    "recorded": video.get("recorded") or None,
                    "source": "pyvideo",
                    "source_url": urls[0] if urls else None,
                }
            )
    talks_frame = pl.DataFrame(
        talks,
        schema={
            "event_slug": pl.String,
            "talk_title": pl.String,
            "speakers": pl.List(pl.String),
            "recorded": pl.String,
            "source": pl.String,
            "source_url": pl.String,
        },
    ).with_columns(pl.col("recorded").str.to_date(strict=False))
    return Tables(events=pl.DataFrame(events), talks=talks_frame)


def read_organizers(organizers_dir: Path) -> pl.DataFrame:
    """Read the python-organizers CSVs.

    Returns:
        One row per non-cancelled PyCon from `_FIRST_YEAR` onwards.
    """
    frames = [
        pl.read_csv(csv_file, infer_schema=False).with_columns(
            year=pl.lit(int(csv_file.stem))
        )
        for csv_file in sorted(organizers_dir.glob("[0-9][0-9][0-9][0-9].csv"))
        if int(csv_file.stem) >= _FIRST_YEAR
    ]
    return (
        pl.concat(frames, how="diagonal")
        .filter(
            pl.col("Subject").str.contains("(?i)pycon")
            & ~pl.col("Subject").str.contains("(?i)cancelled")
        )
        .select(
            "year",
            event_slug=pl.format(
                "{}-{}",
                pl.col("Subject")
                .str.to_lowercase()
                .str.replace_all(r"[^a-z0-9]+", "-"),
                pl.col("year"),
            ),
            event_name=pl.col("Subject"),
            series_key=pl.col("Subject").map_elements(_series_key, pl.String),
            location=pl.col("Location"),
            country=pl.col("Country"),
            start_date=pl.col("Start Date").str.to_date(strict=False),
            end_date=pl.col("End Date").str.to_date(strict=False),
            website=pl.col("Website URL"),
        )
        .unique(["year", "series_key"], keep="first")
    )


def read_manual_locations(path: Path) -> pl.DataFrame:
    """Read hand-entered `[event-slug] location = "City, Country"` entries.

    Returns:
        One row per entry, or none when the file does not exist.
    """
    entries = tomllib.loads(path.read_text()) if path.exists() else {}
    return pl.DataFrame(
        [
            {"event_slug": slug, "manual_location": e["location"]}
            for slug, e in entries.items()
        ],
        schema={"event_slug": pl.String, "manual_location": pl.String},
    )


def link_pyvideo(
    *, organizers: pl.DataFrame, pyvideo_events: pl.DataFrame, talks: pl.DataFrame
) -> Tables:
    """Union the python-organizers events with any PyVideo-only ones.

    A PyVideo event matching a python-organizers row on year and series takes that
    row's `event_slug`, and its talks are relabelled to match.

    Returns:
        The combined events and the relabelled talks.
    """
    slug_map = (
        pyvideo_events.with_columns(
            series_key=pl.col("event_name").map_elements(_series_key, pl.String)
        )
        .join(
            organizers.select("year", "series_key", organizer_slug="event_slug"),
            on=["year", "series_key"],
            how="left",
        )
        .with_columns(
            pyvideo_slug="event_slug",
            event_slug=pl.coalesce("organizer_slug", "event_slug"),
        )
    )
    pyvideo_only = slug_map.filter(pl.col("organizer_slug").is_null()).select(
        "event_slug", "event_name", "year"
    )
    relabelled_talks = (
        talks.join(
            slug_map.select(
                pl.col("pyvideo_slug").alias("event_slug"), new_slug="event_slug"
            ),
            on="event_slug",
        )
        .with_columns(event_slug="new_slug")
        .drop("new_slug")
    )
    events = pl.concat(
        [organizers.drop("series_key"), pyvideo_only], how="diagonal_relaxed"
    )
    return Tables(events=events, talks=relabelled_talks)


def locate_events(
    *, events: pl.DataFrame, talks: pl.DataFrame, manual: pl.DataFrame
) -> pl.DataFrame:
    """Attach the manual location override, dates and talk counts to each event.

    Events with no python-organizers dates take the first and last recorded date of
    their talks, both bounds inclusive.

    Returns:
        One row per event, with `location_source` null where no location is known.
    """
    talk_stats = talks.group_by("event_slug").agg(
        talk_count=pl.len(),
        speaker_count=pl.col("speakers").explode().drop_nulls().n_unique(),
        first_recorded=pl.col("recorded").min(),
        last_recorded=pl.col("recorded").max(),
    )
    return (
        events.join(manual, on="event_slug", how="left")
        .join(talk_stats, on="event_slug", how="left")
        .with_columns(
            location_source=pl.when(pl.col("manual_location").is_not_null())
            .then(pl.lit("manual"))
            .when(pl.col("location").is_not_null())
            .then(pl.lit("organizers")),
            location=pl.coalesce("manual_location", "location"),
            start_date=pl.coalesce("start_date", "first_recorded"),
            end_date=pl.coalesce("end_date", "last_recorded"),
            talk_count=pl.col("talk_count").fill_null(0),
            speaker_count=pl.col("speaker_count").fill_null(0),
        )
        .select(
            "event_slug",
            "event_name",
            "year",
            "start_date",
            "end_date",
            "location",
            "country",
            "location_source",
            "website",
            "talk_count",
            "speaker_count",
        )
    )


def _lookup_coordinates(
    lookup: Callable[[str], Location | None], location: str
) -> dict[str, str | float | None]:
    parts = [part.strip() for part in location.split(",")]
    place = lookup(location)
    if place is None and len(parts) > 2:
        place = lookup(f"{parts[0]}, {parts[-1]}")
    print(f"geocoded {location!r}: {'ok' if place else 'NOT FOUND'}")
    return {
        "location": location,
        "lat": place.latitude if place else None,
        "lng": place.longitude if place else None,
    }


def geocode(locations: pl.Series, cache_path: Path) -> pl.DataFrame:
    """Look up each location's coordinates, calling Nominatim only for uncached ones.

    Side effect: rewrites `cache_path` with any newly looked-up locations, including
    misses (null coordinates), so a miss is not retried on every build.

    Returns:
        The updated cache: one row per location ever looked up.
    """
    schema = {"location": pl.String, "lat": pl.Float64, "lng": pl.Float64}
    cache = (
        pl.read_parquet(cache_path)
        if cache_path.exists()
        else pl.DataFrame(schema=schema)
    )
    wanted = set(locations.drop_nulls().unique()) - {"Online"}
    missing = sorted(wanted - set(cache["location"]))
    if missing:
        geocoder = Nominatim(
            user_agent=_GEOCODER_USER_AGENT, timeout=_GEOCODE_TIMEOUT_SECONDS
        )
        lookup = RateLimiter(geocoder.geocode, min_delay_seconds=_GEOCODE_DELAY_SECONDS)
        found = [_lookup_coordinates(lookup, location) for location in missing]
        cache = pl.concat([cache, pl.DataFrame(found, schema=schema)])
        cache.write_parquet(cache_path)
    return cache


def main() -> None:
    """Clone both upstream datasets and write the seed tables.

    Raises:
        SystemExit: If either output table already exists.
    """
    outputs = (_DATA_DIR / "pycons.parquet", _DATA_DIR / "talks.parquet")
    if existing := [p.name for p in outputs if p.exists()]:
        raise SystemExit(
            f"{', '.join(existing)} already exist and may hold hand edits; "
            "delete them to reseed from upstream."
        )
    _SOURCES_DIR.mkdir(exist_ok=True)
    _DATA_DIR.mkdir(exist_ok=True)
    pyvideo_dir = _SOURCES_DIR / "pyvideo"
    organizers_dir = _SOURCES_DIR / "organizers"
    _refresh_clone(_PYVIDEO_URL, pyvideo_dir)
    _refresh_clone(_ORGANIZERS_URL, organizers_dir)

    pyvideo = read_pyvideo(pyvideo_dir)
    linked = link_pyvideo(
        organizers=read_organizers(organizers_dir),
        pyvideo_events=pyvideo.events,
        talks=pyvideo.talks,
    )
    talks = linked.talks
    located = locate_events(
        events=linked.events,
        talks=talks,
        manual=read_manual_locations(_MANUAL_LOCATIONS),
    )
    coordinates = geocode(located["location"], _GEOCODE_CACHE)
    located = located.join(coordinates, on="location", how="left")

    located.write_parquet(_DATA_DIR / "events.parquet")
    talks.write_parquet(_DATA_DIR / "talks.parquet")

    print(f"{located.height} events, {talks.height} talks")
    print(located.group_by("location_source").len().sort("len", descending=True))
    unlocated = located.filter(pl.col("lat").is_null())
    print(f"{unlocated.height} events without coordinates:")
    print(unlocated.select("event_slug", "event_name", "location", "talk_count"))


if __name__ == "__main__":
    main()
