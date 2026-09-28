"""Apply checked locations and dates to `public/pycons.parquet`.

Reads the location-check files (`<event_slug>.json`, one per event) and, for events
whose check found a mismatch: marks online events online and draws their country's
outline, takes the page's dates where it gave them, and re-geocodes a host city the
page names that the dataset does not. Every checked event gains `official_url`.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Final

import geopandas as gpd
from geopy.geocoders import Nominatim
import orjson
from pandera.typing.polars import DataFrame
import polars as pl
from pycons_schema import Pycons
from shapely.geometry import Point
import typer


_PUBLIC: Final = Path(__file__).parent.parent / "public"
_GEOCODER_USER_AGENT: Final = "marimo-primer-pycon-globe"
_GEOCODE_TIMEOUT_SECONDS: Final = 10.0

app = typer.Typer(
    add_completion=False, context_settings={"help_option_names": ["-h", "--help"]}
)


def read_checks(checks_dir: Path) -> dict[str, dict[str, Any]]:
    """Read every location-check file.

    Returns:
        Each check keyed by its `event_slug`.
    """
    checks = (orjson.loads(p.read_bytes()) for p in sorted(checks_dir.glob("*.json")))
    return {c["event_slug"]: c for c in checks}


def country_outlines() -> tuple[dict[str, bytes], dict[str, str]]:
    """Read Natural Earth's countries.

    Returns:
        WKB outlines keyed by `ADM0_A3`, and `ADM0_A3` keyed by casefolded name.
    """
    countries = gpd.read_file(_PUBLIC / "countries.geojson")
    outlines = dict(zip(countries["ADM0_A3"], countries.geometry.to_wkb(), strict=True))
    codes = {
        name.casefold(): code
        for column in ("ADMIN", "NAME", "NAME_LONG", "ISO_A3", "ADM0_A3")
        for name, code in zip(countries[column], countries["ADM0_A3"], strict=True)
        if isinstance(name, str)
    }
    return outlines, codes


def _corrected(
    row: Mapping[str, Any],
    check: Mapping[str, Any],
    *,
    outlines: Mapping[str, bytes],
    codes: Mapping[str, str],
    geocoder: Nominatim,
) -> dict[str, Any]:
    fixed = dict(row)
    if check.get("start_date") and check.get("end_date"):
        fixed["start_date"] = pl.Series([check["start_date"]]).str.to_datetime()[0]
        fixed["end_date"] = pl.Series([check["end_date"]]).str.to_datetime()[0]
    places = check.get("places") or []
    if check.get("online") and not places:
        fixed |= {"online": True, "location": None, "location_source": "checked"}
        fixed["geometry"] = outlines.get(row["country"], row["geometry"])
    elif places:
        city, country = places[0]["city"], places[0].get("country", "")
        fixed["country"] = codes.get(country.casefold(), row["country"])
        if city.casefold() not in (row["location"] or "").casefold():
            place = geocoder.geocode(f"{city}, {country}")
            if place is not None:
                fixed |= {
                    "location": f"{city}, {country}",
                    "location_source": "checked",
                }
                fixed["geometry"] = Point(place.longitude, place.latitude).wkb
    return fixed


def apply_checks(
    *, pycons: DataFrame[Pycons], checks: Mapping[str, Mapping[str, Any]]
) -> DataFrame[Pycons]:
    """Apply each mismatched check to its event's first place.

    An event found to be online keeps a single row, its country's outline.

    Returns:
        The corrected table, with `official_url` from every check.
    """
    outlines, codes = country_outlines()
    geocoder = Nominatim(
        user_agent=_GEOCODER_USER_AGENT, timeout=_GEOCODE_TIMEOUT_SECONDS
    )
    rows = []
    seen_online: set[str] = set()
    for row in pycons.iter_rows(named=True):
        check = checks.get(row["event_slug"], {})
        fixed: dict[str, Any] = row
        if check.get("matches_dataset") is False:
            fixed = _corrected(
                row, check, outlines=outlines, codes=codes, geocoder=geocoder
            )
        if fixed["online"] and fixed["event_slug"] in seen_online:
            continue
        if fixed["online"] and fixed["country"] in outlines:
            fixed = fixed | {"geometry": outlines[fixed["country"]], "location": None}
        if fixed["online"]:
            seen_online.add(fixed["event_slug"])
        rows.append(fixed | {"official_url": check.get("official_url")})
    schema = pycons.schema | {"official_url": pl.String}
    return Pycons.validate(pl.DataFrame(rows, schema=schema))


@app.command()
def main(
    checks_dir: Path,
    *,
    write: Annotated[
        bool, typer.Option(help="Write the table; without it, only report.")
    ] = False,
) -> None:
    """Apply the location checks in CHECKS_DIR to public/pycons.parquet."""
    path = _PUBLIC / "pycons.parquet"
    pycons = Pycons.validate(
        pl.read_parquet(path).drop("__index_level_0__", strict=False)
    )
    checks = read_checks(checks_dir)
    fixed = apply_checks(pycons=pycons, checks=checks)
    changed = fixed.join(pycons, on=["event_slug", "geometry"], how="anti").height
    print(f"{fixed.height} rows ({pycons.height} before); {changed} with new geometry")
    if write:
        geo = pl.read_parquet_metadata(path)["geo"]
        fixed.write_parquet(path, metadata={"geo": geo})


if __name__ == "__main__":
    app()
