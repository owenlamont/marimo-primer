# /// script
# requires-python = ">=3.14"
# dependencies = [
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
    import datetime as dt

    import geopandas as gpd
    import marimo as mo
    import pandas as pd
    from pyglobegl import (
        GlobeConfig,
        GlobeLayerConfig,
        GlobeWidget,
        PointsLayerConfig,
        PolygonsLayerConfig,
    )
    from pyglobegl.geopandas import points_from_gdf, polygons_from_gdf

    return (
        GlobeConfig,
        GlobeLayerConfig,
        GlobeWidget,
        PointsLayerConfig,
        PolygonsLayerConfig,
        dt,
        gpd,
        mo,
        pd,
        points_from_gdf,
        polygons_from_gdf,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # marimo

    ## A reactive Python notebook, stored as a plain `.py` file

    PythonWA
    """)
    return


@app.cell
def _(mo):
    price = mo.ui.slider(0, 300, value=90, label="Price ($/MWh)")
    return (price,)


@app.cell
def _(mo, price):
    revenue = price.value * 1_000
    mo.vstack(
        [
            price,
            mo.md(f"Selling 1,000 MWh earns **${revenue:,}**."),
            mo.md("Move the slider: this cell reruns."),
        ]
    )
    return


@app.cell
def _(dt, mo):
    dates = mo.ui.date_range(
        start=dt.date(2020, 1, 1),
        stop=dt.date(2026, 12, 31),
        value=(dt.date(2024, 1, 1), dt.date(2024, 12, 31)),
        label="PyCons held between",
    )
    return (dates,)


@app.cell
def _(dates, gpd, mo, pd):
    # pandas, unlike geopandas, can read a URL, which is where the file is under WASM
    table = pd.read_parquet(str(mo.notebook_location() / "public" / "pycons.parquet"))
    pycons = gpd.GeoDataFrame(
        table, geometry=gpd.GeoSeries.from_wkb(table.geometry), crs="EPSG:4326"
    )
    shown = pycons[pycons.start_date.dt.date.between(*dates.value)].assign(
        altitude=lambda d: d.talk_count / 200,
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
    GlobeWidget,
    PointsLayerConfig,
    PolygonsLayerConfig,
    dates,
    is_point,
    mo,
    points_from_gdf,
    polygons_from_gdf,
    shown,
):
    globe = GlobeWidget(
        config=GlobeConfig(
            globe=GlobeLayerConfig(
                globe_image_url="https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg"
            ),
            points=PointsLayerConfig(
                points_data=points_from_gdf(
                    shown[is_point], include_columns=["altitude", "radius", "label"]
                )
            ),
            polygons=PolygonsLayerConfig(
                polygons_data=polygons_from_gdf(
                    shown[~is_point], include_columns=["altitude", "label"]
                )
            ),
        )
    )
    mo.vstack([dates, globe])
    return


if __name__ == "__main__":
    app.run()
