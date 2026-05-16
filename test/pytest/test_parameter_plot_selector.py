import numpy as np
import pytest

from plottr.data.datadict import DataDict, MeshgridDataDict
from plottr.node.parameter_plot_selector import ParameterPlotSelector


@pytest.fixture
def simple_dd():
    dd = DataDict(
        time={'values': np.linspace(0, 1, 50)},
        voltage={'values': np.sin(np.linspace(0, 2 * np.pi, 50)), 'axes': ['time'],
                 'unit': 'V', 'label': 'Voltage'},
        current={'values': np.cos(np.linspace(0, 2 * np.pi, 50)), 'axes': ['time'],
                 'unit': 'A', 'label': 'Current'},
    )
    dd.validate()
    return dd


@pytest.fixture
def two_axis_dd():
    x = np.linspace(0, 1, 10)
    y = np.linspace(0, 2, 8)
    xx, yy = np.meshgrid(x, y, indexing='ij')
    dd = MeshgridDataDict(
        x={'values': xx},
        y={'values': yy},
        z={'values': xx + yy, 'axes': ['x', 'y']},
    )
    dd.validate()
    return dd


def _node_process(xparam, yparam, data):
    # Disable UI to avoid requiring a QApplication in pure-logic tests.
    ParameterPlotSelector.useUi = False
    try:
        node = ParameterPlotSelector('test')
    finally:
        ParameterPlotSelector.useUi = True
    node._xParam = xparam
    node._yParam = yparam
    return node.process(dataIn=data)


def test_passthrough_when_params_none(simple_dd):
    result = _node_process(None, None, simple_dd)
    assert result is not None
    out = result['dataOut']
    assert set(out.axes()) == set(simple_dd.axes())
    assert set(out.dependents()) == set(simple_dd.dependents())


def test_passthrough_when_x_none(simple_dd):
    result = _node_process(None, 'current', simple_dd)
    assert set(result['dataOut'].dependents()) == set(simple_dd.dependents())


def test_passthrough_when_y_none(simple_dd):
    result = _node_process('time', None, simple_dd)
    assert set(result['dataOut'].dependents()) == set(simple_dd.dependents())


def test_cross_plot_two_dependents(simple_dd):
    result = _node_process('voltage', 'current', simple_dd)
    assert result is not None
    out = result['dataOut']
    assert out.axes() == ['voltage']
    assert out.dependents() == ['current']
    assert len(out.data_vals('voltage')) == 50
    assert len(out.data_vals('current')) == 50


def test_cross_plot_axis_vs_dependent(simple_dd):
    result = _node_process('time', 'voltage', simple_dd)
    out = result['dataOut']
    assert out.axes() == ['time']
    assert out.dependents() == ['voltage']


def test_metadata_preserved(simple_dd):
    # Units and labels carried through
    result = _node_process('voltage', 'current', simple_dd)
    out = result['dataOut']
    assert out['voltage']['unit'] == 'V'
    assert out['current']['unit'] == 'A'
    assert out['voltage']['label'] == 'Voltage'
    assert out['current']['label'] == 'Current'


def test_global_meta_preserved(simple_dd):
    simple_dd['__info__'] = {'source': 'test'}
    result = _node_process('voltage', 'current', simple_dd)
    assert result['dataOut'].get('__info__') == {'source': 'test'}


def test_passthrough_on_same_param(simple_dd):
    result = _node_process('voltage', 'voltage', simple_dd)
    assert set(result['dataOut'].dependents()) == set(simple_dd.dependents())


def test_passthrough_on_missing_param(simple_dd):
    result = _node_process('nonexistent', 'current', simple_dd)
    assert set(result['dataOut'].dependents()) == set(simple_dd.dependents())


def test_meshgrid_flattened_to_scatter(two_axis_dd):
    result = _node_process('x', 'z', two_axis_dd)
    out = result['dataOut']
    assert out.axes() == ['x']
    assert out.dependents() == ['z']
    # 10 * 8 = 80 points after flatten
    assert len(out.data_vals('x')) == 80
    assert len(out.data_vals('z')) == 80


def test_passthrough_on_size_mismatch():
    """Fields with different flattened sizes fall back to pass-through with a warning."""
    dd = DataDict(
        time={'values': np.linspace(0, 1, 10)},
        voltage={'values': np.ones(10), 'axes': ['time']},
        current={'values': np.ones(10), 'axes': ['time']},
    )
    dd.validate()
    # Artificially create a size mismatch after validation.
    dd['current']['values'] = np.ones(7)
    result = _node_process('voltage', 'current', dd)
    assert result is not None
    out = result['dataOut']
    # Pass-through: original structure preserved.
    assert set(out.dependents()) == {'voltage', 'current'}
