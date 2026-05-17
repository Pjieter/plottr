from typing import Optional, Dict

import numpy as np

from plottr import QtWidgets
from ..gui.widgets import FormLayoutWrapper, DimensionCombo
from ..data.datadict import DataDict, DataDictBase, is_meta_key
from .node import Node, NodeWidget, updateOption


class _ParamPlotOptionsWidget(FormLayoutWrapper):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(
            parent=parent,
            elements=[
                ('X param', DimensionCombo(dimensionType='all')),
                ('Y param', DimensionCombo(dimensionType='all')),
            ],
        )
        self.xCombo = self.elements['X param']
        self.yCombo = self.elements['Y param']


class ParameterPlotSelectorWidget(NodeWidget):

    def __init__(self, node: "ParameterPlotSelector"):
        super().__init__(embedWidgetClass=_ParamPlotOptionsWidget, node=node)

        self.widget: _ParamPlotOptionsWidget
        assert self.widget is not None

        self.widget.xCombo.connectNode(self.node)
        self.widget.yCombo.connectNode(self.node)

        self.optSetters = {
            'xParam': self.setXParam,
            'yParam': self.setYParam,
        }
        self.optGetters = {
            'xParam': self.getXParam,
            'yParam': self.getYParam,
        }

        self.widget.xCombo.dimensionSelected.connect(
            lambda x: self.signalOption('xParam')
        )
        self.widget.yCombo.dimensionSelected.connect(
            lambda x: self.signalOption('yParam')
        )

    def getXParam(self) -> Optional[str]:
        t = self.widget.xCombo.currentText()
        return None if t == 'None' else t

    def getYParam(self) -> Optional[str]:
        t = self.widget.yCombo.currentText()
        return None if t == 'None' else t

    def setXParam(self, val: Optional[str]) -> None:
        self.widget.xCombo.setCurrentText(val if val is not None else 'None')

    def setYParam(self, val: Optional[str]) -> None:
        self.widget.yCombo.setCurrentText(val if val is not None else 'None')


class ParameterPlotSelector(Node):
    """Node for plotting any parameter against any other.

    When both :attr:`xParam` and :attr:`yParam` are set to valid field names,
    creates a new DataDict with xParam as the axis and yParam as the dependent,
    flattening multi-dimensional arrays to produce a scatter dataset.

    When either param is ``None`` (the default), data passes through unchanged.
    """

    nodeName = 'ParameterPlotSelector'
    useUi = True
    uiClass = ParameterPlotSelectorWidget

    def __init__(self, name: str):
        self._xParam: Optional[str] = None
        self._yParam: Optional[str] = None
        super().__init__(name)

    @property
    def xParam(self) -> Optional[str]:
        return self._xParam

    @xParam.setter
    @updateOption('xParam')
    def xParam(self, value: Optional[str]) -> None:
        self._xParam = value

    @property
    def yParam(self) -> Optional[str]:
        return self._yParam

    @yParam.setter
    @updateOption('yParam')
    def yParam(self, value: Optional[str]) -> None:
        self._yParam = value

    def process(
            self, dataIn: Optional[DataDictBase] = None
    ) -> Optional[Dict[str, Optional[DataDictBase]]]:
        if super().process(dataIn=dataIn) is None:
            return None
        assert dataIn is not None

        if self._xParam is None or self._yParam is None:
            return dict(dataOut=dataIn.copy())

        # Deduplicate: axes() can list the same name multiple times when
        # several dependents share an axis.
        all_fields = list(dict.fromkeys(dataIn.axes() + dataIn.dependents()))

        if self._xParam not in all_fields:
            self.node_logger.warning(
                f"xParam '{self._xParam}' not found in data. Passing through."
            )
            return dict(dataOut=dataIn.copy())

        if self._yParam not in all_fields:
            self.node_logger.warning(
                f"yParam '{self._yParam}' not found in data. Passing through."
            )
            return dict(dataOut=dataIn.copy())

        if self._xParam == self._yParam:
            self.node_logger.warning("xParam and yParam are the same field. Passing through.")
            return dict(dataOut=dataIn.copy())

        x_raw = dataIn.data_vals(self._xParam)
        y_raw = dataIn.data_vals(self._yParam)

        if x_raw is None or y_raw is None:
            self.node_logger.warning("One or both selected params have no values. Passing through.")
            return dict(dataOut=dataIn.copy())

        # For MeshgridDataDict inputs the arrays are N-D (full grid shape);
        # flatten to 1-D to produce a scatter dataset.
        # Use np.ma.array so MaskedArray masks are preserved rather than stripped.
        x_vals = np.ma.array(x_raw).flatten()
        y_vals = np.ma.array(y_raw).flatten()

        if x_vals.size == 0 or y_vals.size == 0:
            self.node_logger.warning("One or both selected params are empty. Passing through.")
            return dict(dataOut=dataIn.copy())

        if x_vals.size != y_vals.size:
            self.node_logger.warning(
                f"xParam '{self._xParam}' (size {x_vals.size}) and "
                f"yParam '{self._yParam}' (size {y_vals.size}) have different sizes. "
                f"Passing through."
            )
            return dict(dataOut=dataIn.copy())

        def _copy_field(src: dict, extra: dict) -> dict:
            # Exclude '__shape__': after flattening the shape changes and any
            # cached value from MeshgridDataDict.validate() would be stale.
            out = {k: v for k, v in src.items()
                   if k not in ('values', 'axes', '__shape__')}
            out.update(extra)
            return out

        dd_out = DataDict()
        dd_out[self._xParam] = _copy_field(dataIn[self._xParam], {'values': x_vals})
        dd_out[self._yParam] = _copy_field(
            dataIn[self._yParam], {'values': y_vals, 'axes': [self._xParam]}
        )

        # Preserve global metadata (e.g. __info__ written by DDH5Writer).
        for key, val in dataIn.items():
            if is_meta_key(key):
                dd_out[key] = val

        dd_out.validate()
        return dict(dataOut=dd_out)
