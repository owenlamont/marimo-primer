# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "altair",
#     "marimo",
#     "pyglobegl[geopandas]",
#     "pandas",
#     "pyarrow",
# ]
# ///

import marimo


__generated_with = "0.25.0"
app = marimo.App(width="medium", layout_file="layouts/deck.slides.json")


@app.cell
def _():
    import math

    import altair as alt
    import geopandas as gpd
    import marimo as mo
    import pandas as pd
    from pyglobegl import (
        GlobeConfig,
        GlobeLayerConfig,
        GlobeLayoutConfig,
        GlobeWidget,
        PointsLayerConfig,
        PolygonDatum,
        PolygonsLayerConfig,
    )
    from pyglobegl.geopandas import points_from_gdf

    return (
        GlobeConfig,
        GlobeLayerConfig,
        GlobeLayoutConfig,
        GlobeWidget,
        PointsLayerConfig,
        PolygonDatum,
        PolygonsLayerConfig,
        alt,
        gpd,
        math,
        mo,
        pd,
        points_from_gdf,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # a marimo primer

    ## Reactive Python notebooks

    An introduction for Jupyter users · PythonWA
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Why marimo exists

    [Akshay Agrawal](https://x.com/akshaykagrawal) (Stanford, Google Brain) and
    [Myles Scolnick](https://x.com/themylesfiles) (Palantir), launched January 2024.
    Jupyter frustrated Akshay's research:

    - **Hidden state**: over a third of notebooks on GitHub fail to reproduce.
    - **JSON** is hard to use in Python codebases.
    - Documents **lack interactivity**. Pluto.jl and Observable showed the fix.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## A reactive Python notebook

    - Stored as a plain `.py` file: it's just Python.
    - Cells form a dependency graph: change one, its dependents re-run.
    - UI elements built in; runs as a notebook, an app, or a script.

    ```bash
    marimo edit nb.py   # interactive notebook
    marimo run  nb.py   # deploy as an app
    python      nb.py   # run as a script
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Install it with `uv`

    ```bash
    uv tool install marimo    # install once, globally
    marimo edit notebook.py   # start editing

    uvx marimo edit nb.py     # ...or run without installing
    uv add marimo             # ...or add it to a project
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Coming from Jupyter? Two things feel different

    - **Execution.** Jupyter runs cells in the order you click, so state can drift;
      marimo re-runs by dependency.
    - **Format.** `.ipynb` is JSON; marimo is `.py`, so version control and review
      just work.

    ```bash
    uvx marimo convert old.ipynb -o new.py   # bring your notebooks
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Where Jupyter still leads

    - Jupyter's **ipywidgets** ecosystem is far larger than marimo's.
    - Jupyter runs many kernels and languages (R, Julia and more); marimo is
      Python-only.
    - Jupyter has a huge community, with years of tooling, tutorials and answers.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.vstack(
        [
            mo.md(r"""## Change a value, everything downstream updates"""),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md(r"""**Jupyter**"""),
                            mo.ui.code_editor(
                                value="rsvps = 40", language="python", disabled=True
                            ),
                            mo.ui.code_editor(
                                value="# change rsvps: pizzas is now stale\n"
                                "pizzas = rsvps * 3 // 8",
                                language="python",
                                disabled=True,
                            ),
                        ],
                        gap=0,
                    ),
                    mo.vstack(
                        [
                            mo.md(r"""**marimo**"""),
                            mo.ui.code_editor(
                                value="rsvps = 40", language="python", disabled=True
                            ),
                            mo.ui.code_editor(
                                value="# change rsvps: pizzas re-runs itself\n"
                                "pizzas = rsvps * 3 // 8",
                                language="python",
                                disabled=True,
                            ),
                        ],
                        gap=0,
                    ),
                ],
                gap=4,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    rsvps = mo.ui.slider(0, 150, value=40, label="Meetup RSVPs")
    return (rsvps,)


@app.cell
def _(math, mo, rsvps):
    pizzas = math.ceil(rsvps.value * 3 / 8)
    mo.vstack(
        [
            rsvps,
            mo.md(f"At 3 slices each, order **{pizzas} pizzas**."),
            mo.md("Move the slider: this cell reruns."),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## No hidden state: delete a cell, its variables vanish

    - Each variable is defined in exactly one cell, so nothing is shadowed.
    - No lingering kernel state: the notebook **is** the code you see.
    - In Jupyter, `%whos` lists what's hiding in the kernel; in marimo there's nothing
      hidden to list.

    ```bash
    marimo check nb.py   # flags redefinitions and cycles
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.vstack(
        [
            mo.md(r"""## A reactive UI in three lines"""),
            mo.hstack(
                [
                    mo.vstack(
                        [
                            mo.md(r"""**Jupyter**"""),
                            mo.ui.code_editor(
                                value="from ipywidgets import interact",
                                language="python",
                                disabled=True,
                            ),
                            mo.ui.code_editor(
                                value="@interact(x=(0, 150))\n"
                                "def show(x):\n    redraw(x)",
                                language="python",
                                disabled=True,
                            ),
                        ],
                        gap=0,
                    ),
                    mo.vstack(
                        [
                            mo.md(r"""**marimo**"""),
                            mo.ui.code_editor(
                                value="x = mo.ui.slider(0, 150)\nx",
                                language="python",
                                disabled=True,
                            ),
                            mo.ui.code_editor(
                                value="plot(x.value)", language="python", disabled=True
                            ),
                        ],
                        gap=0,
                    ),
                ],
                gap=4,
            ),
            mo.md(r"""Custom widgets via `anywidget`, which also works in Jupyter."""),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Version control: the same one-line edit, in git

    - A one-line change to a marimo notebook is a one-line diff you can review.
    - The same change to an `.ipynb` also rewrites JSON metadata and base64 outputs.
    - marimo recomputes outputs on each run. To keep them, it can snapshot HTML,
      `.ipynb` or Markdown into a `__marimo__/` folder beside the notebook.

    ```bash
    git diff notebook.py   # a one-line change
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## You can tame `.ipynb` diffs

    - `nbstripout`, `nbdime`, `jupytext` and ReviewNB all help.
    - Each is extra tooling or an integration someone has to set up.
    - marimo is clean by default, with nothing to set up.

    ```bash
    uvx nbstripout --install   # e.g. a per-repo git filter
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Runs with no server: WASM

    ```bash
    marimo export html-wasm nb.py -o dist/
    ```

    Pyodide runs the notebook in the browser, with no server. JupyterLite does the same
    for Jupyter. This deck's last slide runs that way too.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Agents: the format helps here too

    Because a marimo notebook is plain `.py`, coding agents read, edit and review it
    like any Python file.

    ```bash
    gh skill install marimo-team/skills --all --agent claude-code --scope user
    ```

    Skills for authoring notebooks and converting from Jupyter.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## marimo pair: drive a live notebook from your agent

    Your agent runs Python in the **same kernel you see**: it can inspect variables,
    add and run cells, and move widgets.

    ```bash
    gh skill install marimo-team/marimo-pair --agent claude-code --scope user

    # then, in Claude Code:
    /marimo-pair pair with me on notebook.py
    ```

    Led by [Trevor Manz](https://bsky.app/profile/manzt.sh), a founding engineer at
    marimo.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Reach for marimo when you want...

    - **Reactive** execution and no stale state.
    - **Plain `.py`**: clean diffs, agent-friendly.
    - To ship a notebook as an **app**, or run it in the browser.

    ```bash
    uv tool install marimo && marimo edit
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## anywidget: write a widget once, run it everywhere

    [Trevor Manz](https://bsky.app/profile/manzt.sh) built it during his Harvard PhD;
    marimo made it its plugin API and hired him.

    - **Before**: PyPI **and** npm packages, a JS build, an adapter per platform.
    - **Now**: one Python class plus an ES module, for Jupyter, Colab, VS Code, marimo.
    - [Vincent Warmerdam](https://x.com/fishnets88) (scikit-lego, now at marimo) keeps
      [wigglystuff](https://github.com/koaning/wigglystuff); next up,
      [pyglobegl](https://github.com/owenlamont/pyglobegl).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Demo: every PyCon since 2020

    Drag across the timeline to pick a range. Each bar is a PyCon, as tall as its talk
    count; online events shade their country.
    """)
    return


@app.cell
def _(gpd, mo, pd):
    # pandas, unlike geopandas, can read a URL, which is where the file is under WASM
    table = pd.read_parquet(str(mo.notebook_location() / "public" / "pycons.parquet"))
    pycons = gpd.GeoDataFrame(
        table, geometry=gpd.GeoSeries.from_wkb(table.geometry), crs="EPSG:4326"
    )
    return (pycons,)


@app.cell
def _(alt, mo, pycons):
    width_px = 640
    timeline = mo.ui.altair_chart(
        alt.Chart(pycons[["event_slug", "event_name", "start_date", "talk_count"]])
        .mark_circle(size=40)
        .encode(
            x=alt.X("start_date:T", title=None),
            y=alt.Y("talk_count:Q", title="talks"),
            tooltip=["event_name", "start_date:T", "talk_count"],
        )
        .add_params(alt.selection_interval(name="dates", encodings=["x"]))
        .properties(width=width_px, height=80)
        .configure(autosize=alt.AutoSizeParams(type="fit", contains="padding")),
        legend_selection=False,
    )
    return timeline, width_px


@app.cell
def _(pd, pycons, timeline):
    in_range = (
        pycons[pycons.event_slug.isin(timeline.value.event_slug)]
        if any(timeline.selections.values())
        else pycons
    )
    shown = in_range.assign(
        altitude=lambda d: d.talk_count / 200,
        color=lambda d: pd.cut(
            d.talk_count,
            [-1, 0, 25, 50, 100, 1_000],
            labels=["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
        ).astype(str),
        radius=0.8,
        label=lambda d: (
            d.event_name
            + " "
            + d.year.astype(str)
            + ": "
            + d.talk_count.astype(str)
            + " talks"
        ),
    )
    is_point = shown.geom_type == "Point"
    return is_point, shown


@app.cell
def _(
    GlobeConfig,
    GlobeLayerConfig,
    GlobeLayoutConfig,
    GlobeWidget,
    PointsLayerConfig,
    PolygonDatum,
    PolygonsLayerConfig,
    is_point,
    mo,
    points_from_gdf,
    shown,
    timeline,
    width_px,
):
    globe = GlobeWidget(
        config=GlobeConfig(
            layout=GlobeLayoutConfig(width=width_px, height=480),
            globe=GlobeLayerConfig(
                globe_image_url="https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-day.jpg"
            ),
            points=PointsLayerConfig(
                points_data=points_from_gdf(
                    shown[is_point],
                    include_columns=["altitude", "color", "radius", "label"],
                )
            ),
            polygons=PolygonsLayerConfig(
                # polygons_from_gdf rewinds rings, so globe.gl fills them inside out
                polygons_data=[
                    PolygonDatum(
                        geometry=row.geometry.__geo_interface__,
                        altitude=row.altitude / 10,
                        cap_color=row.color,
                        label=row.label,
                    )
                    for row in shown[~is_point].itertuples()
                ]
            ),
        )
    )
    mo.vstack(
        [mo.md("## Every PyCon since 2020"), mo.center(timeline), mo.center(globe)]
    )
    return


if __name__ == "__main__":
    app.run()
