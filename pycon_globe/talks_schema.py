from enum import StrEnum
from typing import Annotated

import pandera.polars as pa
import polars as pl


class TalkSource(StrEnum):
    PYVIDEO = "pyvideo"
    SCHEDULE = "schedule"
    YOUTUBE = "youtube"


class TalkKind(StrEnum):
    TALK = "talk"
    KEYNOTE = "keynote"
    WORKSHOP = "workshop"


class Talks(pa.DataFrameModel):
    """`public/talks.parquet`: one row per talk; `kind` is null for PyVideo talks."""

    event_slug: str
    talk_title: str
    speakers: Annotated[pl.List, pl.String]
    recorded: pl.Date = pa.Field(nullable=True)
    source: Annotated[pl.Enum, [s.value for s in TalkSource]]
    source_url: str = pa.Field(nullable=True)
    kind: Annotated[pl.Enum, [k.value for k in TalkKind]] = pa.Field(nullable=True)

    class Config:
        strict = True
