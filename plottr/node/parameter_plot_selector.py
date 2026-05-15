from typing import Optional, Dict

import numpy as np

from plottr import QtWidgets
from ..gui.widgets import FormLayoutWrapper, DimensionCombo
from ..data.datadict import DataDict, DataDictBase
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

        all_fields = dataIn.axes() + dataIn.dependents()

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

        x_vals = np.array(dataIn.data_vals(self._xParam)).flatten()
        y_vals = np.array(dataIn.data_vals(self._yParam)).flatten()

        if x_vals.size != y_vals.size:
            self.node_logger.warning(
                f"xParam '{self._xParam}' (size {x_vals.size}) and "
                f"yParam '{self._yParam}' (size {y_vals.size}) have different sizes. "
                f"Passing through."
            )
            return dict(dataOut=dataIn.copy())

        dd_out = DataDict()
        dd_out[self._xParam] = {
            'values': x_vals,
            'label': dataIn[self._xParam].get('label', ''),
            'unit': dataIn[self._xParam].get('unit', ''),
        }
        dd_out[self._yParam] = {
            'values': y_vals,
            'axes': [self._xParam],
            'label': dataIn[self._yParam].get('label', ''),
            'unit': dataIn[self._yParam].get('unit', ''),
        }
        dd_out.validate()
        return dict(dataOut=dd_out)
