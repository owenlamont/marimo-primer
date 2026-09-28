# Coding Agent Instructions

## What this repo is

The deck and demos for a marimo talk at the PythonWA Meetup. The deck is itself a marimo
notebook in the slides layout, and it should also run in the browser via WASM export.

## Layout

- `deck.py` – the slides notebook; `layouts/deck.slides.json` selects the slides layout.
- `public/` – data the deck reads. The WASM export ships only this folder, so the deck
  loads it through `mo.notebook_location()`.
- `public/pycons.parquet` – GeoParquet, one row per PyCon (2020 onwards) and place,
  hand-edited. `public/talks.parquet` holds talks per event.
- `pycon_globe/build_dataset.py` – the one-off seed for that data. The data has since
  been hand-edited, so don't re-run it.

## Working here

- Keep notebook code short and readable: put per-event rules in the data, not branches
  in the notebook.
- Use the uv CLI for dependency changes. A 7-day `exclude-newer` cooldown applies.
- Run `prek run --all-files` and `uv run marimo check deck.py` before committing.
- Check the deck with `uv run marimo run deck.py`, and WASM with
  `uv run marimo export html-wasm deck.py -o <dir> --mode run`, served over HTTP.
- `main` takes changes by PR only, with `lint` required.
