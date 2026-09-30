# marimo-primer

The deck and demos for a talk introducing [marimo](https://marimo.io) to Jupyter users,
given at the PythonWA Meetup. The deck is itself a marimo notebook in the slides layout,
so its demos run live on the slides. It ends on a globe of every PyCon since 2020.

## Running the slides

You need [uv](https://docs.astral.sh/uv/). Then:

```sh
git clone https://github.com/owenlamont/marimo-primer.git
cd marimo-primer
uv run marimo run deck.py    # present: opens the slides in your browser
uv run marimo edit deck.py   # edit the deck and its cells
```

`uv run` installs the dependencies from `uv.lock` on first use. In the slides, the arrow
keys move between slides and `Home` returns to the title.

## The PyCon data

`public/pycons.parquet` (GeoParquet, one row per PyCon and place) and
`public/talks.parquet` (one row per talk) drive the globe. Events, dates and websites
start from [python-organizers/conferences](https://github.com/python-organizers/conferences)
and talks from [PyVideo](https://github.com/pyvideo/data), both CC0. The rest of the talks
were collected from each event's own schedule, YouTube playlists and speakers' posts, and
the data has since been hand-edited. To correct or remove an entry, open an issue.
