from typing import Annotated

from pandera.api.polars.model_config import BaseConfig
import pandera.polars as pa
import polars as pl


class Pycons(pa.DataFrameModel):
    """`public/pycons.parquet` read as plain Parquet: one row per event and place.

    `geometry` is WKB; the file's `geo` metadata carries its CRS.
    """

    event_slug: str
    event_name: str
    year: int
    start_date: Annotated[pl.Datetime, "ms", None]
    end_date: Annotated[pl.Datetime, "ms", None]
    online: bool
    talk_count: pl.UInt32
    speaker_count: pl.UInt32
    schedule_url: str = pa.Field(nullable=True)
    geometry: pl.Binary

    # Pandera needs nested Config; ty treats its mutable attribute as invariant.
    class Config(BaseConfig):  # ty: ignore[invalid-mutable-override]
        strict = False
