import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    rsvps = 40
    return (rsvps,)


@app.cell
def _(rsvps):
    pizzas = rsvps * 3 // 8
    pizzas
    return


if __name__ == "__main__":
    app.run()
