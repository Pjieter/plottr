# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable)
uv sync --extra pyqt5   # or pyqt6 / pyside2

# Run all tests
uv run pytest test/pytest

# Run a single test file
uv run pytest test/pytest/test_data_dict.py

# Type checking
uv run mypy plottr

# Launch apps
uv run plottr-autoplot-ddh5   # live plot a DDH5 file
uv run plottr-inspectr        # browse QCoDeS datasets
uv run plottr-monitr          # monitor a data directory
```

## Architecture

### Data layer (`plottr/data/`)

Central abstraction is `DataDictBase` (a dict subclass). Two concrete types:
- `DataDict` — flat record-style data; axes declared per field; supports `append`, `expand` (nested → flat).
- `MeshgridDataDict` — all arrays share the same grid shape; supports `slice`, `mean`.

Conversion helpers: `datadict_to_meshgrid`, `meshgrid_to_datadict`, `combine_datadicts`.

Storage: `datadict_to_hdf5` / `datadict_from_hdf5` write/read `.ddh5` files (HDF5). `DDH5Writer` is a context-manager writer. `FileOpener` handles file-lock coordination for concurrent access.

QCoDeS integration (`qcodes_dataset.py`) converts `DataSetProtocol` → `DataDict` and provides `QCodesDSLoader` node.

### Node/Flowchart system (`plottr/node/`)

Nodes are pyqtgraph `Flowchart` nodes with a plottr wrapper:
- `Node` (base): holds options, optional `NodeWidget` (Qt control panel), emits signals on option change, calls `process()` to transform `DataDictBase → DataDictBase`.
- Decorators: `@updateOption` on property setters triggers re-processing; `@updateGuiFromNode` / `@emitGuiUpdate` keep node↔widget in sync without feedback loops.
- `linearFlowchart(*nodes)` in `node/tools.py` wires nodes left-to-right and is used by all built-in apps.

Key processing nodes: `DataSelector`, `GridOption` (gridder), `DimReducer`, `Histogram`, `ScaleUnits`, `CorrectOffset`, `Fitter`.

### Plot layer (`plottr/plot/`)

`PlotWidget` / `PlotWidgetContainer` / `PlotNode` are the base classes.  
Two backends share the same base API:
- `plot/mpl/` — Matplotlib
- `plot/pyqtgraph/` — pyqtgraph (default for live use)

`AutoFigureMaker` (base class) drives semi-automatic subplot layout from `PlotItem` / `SubPlot` dataclasses; each backend subclasses it.

### Apps (`plottr/apps/`)

All apps create a `linearFlowchart`, wire a loader node at the front, terminate with a `PlotNode`, and display via `AutoPlotMainWindow` (a `PlotWindow` subclass with an `UpdateToolBar` for timed refresh).

- `autoplot.py` — generic autoplot; `autoplotDDH5` and `autoplotQcodesDataset` are the public entry points.
- `inspectr.py` — QCoDeS DB browser.
- `monitr.py` — watches a directory for new DDH5 files using `watchdog`.

### Qt abstraction

All Qt imports go through `qtpy` (set `QT_API` env var to choose `pyqt5`, `pyqt6`, or `pyside2`). GUI helpers live in `plottr/gui/`.
