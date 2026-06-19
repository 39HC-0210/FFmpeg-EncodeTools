from typing import Any, Callable, Tuple

from qfluentwidgets import ComboBox, SpinBox, DoubleSpinBox, CheckBox, LineEdit, BodyLabel

from core.tools.encoder import EncParam


class WidgetMaker:
    """根据 EncParam 定义动态创建对应 Qt 控件"""

    @staticmethod
    def make(param: EncParam, ro: bool = False) -> tuple[Any, Callable[[], Any]]:
        """根据参数定义创建控件和取值回调

        Args:
            param: 编码器参数定义
            ro: 是否设为只读

        Returns:
            (Qt 控件, 获取当前值的回调函数) 元组
        """
        t = param.w_type

        if t == "float_spin":
            w = DoubleSpinBox()
            if param.rng:
                w.setRange(float(param.rng[0]), float(param.rng[1]))
            w.setSingleStep(getattr(param, "step", 1.0))
            w.setValue(float(param.default))
            w.setReadOnly(ro)
            w.setToolTip(param.tip)
            return w, lambda: w.value()

        elif t == "int_spin":
            w = SpinBox()
            if param.rng:
                w.setRange(int(param.rng[0]), int(param.rng[1]))
            w.setValue(int(param.default))
            w.setReadOnly(ro)
            w.setToolTip(param.tip)
            return w, lambda: w.value()

        elif t == "combo":
            w = ComboBox()
            if param.opts:
                w.addItems(param.opts)
            w.setCurrentText(str(param.default))
            w.setEnabled(not ro)
            w.setToolTip(param.tip)
            return w, lambda: w.currentText()

        elif t == "check":
            w = CheckBox()
            w.setChecked(bool(param.default))
            w.setEnabled(not ro)
            w.setToolTip(param.tip)
            return w, lambda: w.isChecked()

        elif t == "text":
            w = LineEdit()
            w.setText(str(param.default))
            w.setReadOnly(ro)
            w.setToolTip(param.tip)
            return w, lambda: w.text()

        else:
            w = LineEdit()
            w.setText(str(param.default))
            return w, lambda: w.text()

    @staticmethod
    def make_row(param: EncParam, ro: bool = False) -> tuple[BodyLabel, Any, Callable[[], Any]]:
        """创建带标签的控件行

        Returns:
            (标签, 控件, 取值回调) 元组
        """
        lb = BodyLabel(param.label)
        w, get = WidgetMaker.make(param, ro)
        return lb, w, get
