from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QWidget
from qfluentwidgets import isDarkTheme

DARK_BG = "#1E1E1E"
DARK_PANEL = "#252526"
DARK_SURFACE = "#252526"
DARK_FIELD = "#2D2D2D"
DARK_FIELD_HOVER = "#353535"
DARK_BORDER = "#3C3C3C"
DARK_BORDER_SOFT = "#2D2D2D"
DARK_TEXT = "#E8E8E8"
DARK_MUTED = "#A8A8A8"
DARK_SELECTION = "#1C605C"
DARK_ACCENT = "#39C5BB"

LIGHT_BG = "#F8F9FA"
LIGHT_PANEL = "#F8F9FA"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_BORDER = "#E5E5E5"
LIGHT_TEXT = "#333333"
LIGHT_MUTED = "#666666"
LIGHT_SELECTION = "#C6F1EE"

DARK_QSS = f"""
#MainWindow,
Win,
QWidget#MainBox,
QStackedWidget,
QStackedWidget > QWidget {{
    background-color: {DARK_BG};
    color: {DARK_TEXT};
}}
QWidget#BotBar {{
    background-color: {DARK_BG};
    border-top: 1px solid {DARK_BORDER_SOFT};
}}
QWidget#NavPanel {{
    background-color: {DARK_PANEL};
    border-right: none;
}}
NavigationInterface {{
    background-color: transparent;
    border: none;
}}
QLabel,
TitleLabel,
SubtitleLabel,
BodyLabel,
StrongBodyLabel {{
    background-color: transparent;
    color: {DARK_TEXT};
}}
CaptionLabel {{
    background-color: transparent;
    color: {DARK_MUTED};
}}
CardWidget {{
    background-color: {DARK_SURFACE};
    border: 1px solid {DARK_BORDER_SOFT};
    border-radius: 8px;
}}
QScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QAbstractScrollArea,
QAbstractScrollArea::viewport {{
    background-color: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 8px 2px 8px 2px;
}}
QScrollBar::handle:vertical {{
    background: #3A3A3A;
    min-height: 36px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4A4A4A;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    border: none;
    height: 0;
}}
QFrame,
QSplitter {{
    background-color: {DARK_BG};
}}
QLineEdit,
LineEdit,
QPlainTextEdit,
QTextEdit,
TextEdit,
QComboBox,
ComboBox,
QSpinBox,
SpinBox,
QDoubleSpinBox,
DoubleSpinBox,
QTableWidget,
QTableView {{
    background-color: {DARK_FIELD};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {DARK_SELECTION};
    selection-color: #FFFFFF;
}}
QLineEdit:hover,
LineEdit:hover,
QPlainTextEdit:hover,
QTextEdit:hover,
TextEdit:hover,
QComboBox:hover,
ComboBox:hover,
QSpinBox:hover,
SpinBox:hover,
QDoubleSpinBox:hover,
DoubleSpinBox:hover {{
    background-color: {DARK_FIELD_HOVER};
    border: 1px solid #3B424A;
}}
QComboBox QAbstractItemView,
ComboBox QAbstractItemView {{
    background-color: {DARK_FIELD};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    selection-background-color: {DARK_SELECTION};
}}
QCheckBox,
CheckBox,
QRadioButton,
RadioButton {{
    background-color: transparent;
    color: {DARK_TEXT};
    spacing: 8px;
}}
QHeaderView::section {{
    background-color: {DARK_SURFACE};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER_SOFT};
}}
QTableCornerButton::section {{
    background-color: {DARK_SURFACE};
    border: 1px solid {DARK_BORDER_SOFT};
}}
QToolTip {{
    background-color: {DARK_FIELD};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
}}
PushButton {{
    background-color: {DARK_FIELD};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
}}
PushButton:hover {{
    background-color: {DARK_FIELD_HOVER};
    border: 1px solid #414852;
}}
PushButton:pressed {{
    background-color: #24282E;
}}
PrimaryPushButton {{
    background-color: {DARK_ACCENT};
    color: #FFFFFF;
    border: 1px solid {DARK_ACCENT};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}}
PrimaryPushButton:hover {{
    background-color: #2FA59D;
    border: 1px solid #2FA59D;
}}
PushButton#btnGo {{
    background-color: {DARK_FIELD};
    color: {DARK_TEXT};
    border: 1px solid {DARK_BORDER};
    border-radius: 6px;
    font-size: 14px;
    font-weight: bold;
}}
PushButton#btnGo:hover {{
    background-color: {DARK_FIELD_HOVER};
    border: 1px solid #414852;
}}
PushButton#btnGo:pressed {{
    background-color: #24282E;
}}
"""

LIGHT_QSS = f"""
#MainWindow,
Win,
QWidget#MainBox,
QStackedWidget,
QStackedWidget > QWidget {{
    background-color: {LIGHT_BG};
    color: {LIGHT_TEXT};
}}
QWidget#BotBar {{
    background-color: {LIGHT_BG};
    border-top: 1px solid {LIGHT_BORDER};
}}
QWidget#NavPanel {{
    background-color: {LIGHT_PANEL};
    border-right: none;
}}
NavigationInterface {{
    background-color: transparent;
    border: none;
}}
QScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QAbstractScrollArea,
QAbstractScrollArea::viewport {{
    background-color: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 8px 2px 8px 2px;
}}
QScrollBar::handle:vertical {{
    background: #C8CDD4;
    min-height: 36px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #AEB5BF;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
    border: none;
    height: 0;
}}
QFrame,
QSplitter {{
    background-color: {LIGHT_BG};
}}
QLabel,
TitleLabel,
SubtitleLabel,
BodyLabel,
StrongBodyLabel {{
    background-color: transparent;
    color: {LIGHT_TEXT};
}}
CardWidget {{
    background-color: {LIGHT_SURFACE};
    border: 1px solid {LIGHT_BORDER};
    border-radius: 8px;
}}
QLineEdit,
LineEdit,
QPlainTextEdit,
QTextEdit,
TextEdit,
QComboBox,
ComboBox,
QSpinBox,
SpinBox,
QDoubleSpinBox,
DoubleSpinBox,
QTableWidget,
QTableView {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT};
    border: 1px solid #D8DCE2;
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {LIGHT_SELECTION};
    selection-color: #000000;
}}
QCheckBox,
CheckBox,
QRadioButton,
RadioButton {{
    background-color: transparent;
    color: {LIGHT_TEXT};
    spacing: 8px;
}}
QToolTip {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT};
    border: 1px solid {LIGHT_BORDER};
}}
PushButton {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT};
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    padding: 6px 12px;
}}
PushButton:hover {{
    background-color: #F4F4F4;
    border: 1px solid #B0B0B0;
}}
PrimaryPushButton {{
    background-color: {DARK_ACCENT};
    color: #FFFFFF;
    border: 1px solid {DARK_ACCENT};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}}
PrimaryPushButton:hover {{
    background-color: #2FA59D;
    border: 1px solid #2FA59D;
}}
PushButton#btnGo {{
    background-color: {LIGHT_SURFACE};
    color: {LIGHT_TEXT};
    border: 1px solid #D0D0D0;
    border-radius: 6px;
    font-size: 14px;
    font-weight: bold;
}}
PushButton#btnGo:hover {{
    background-color: #F4F4F4;
    border: 1px solid #B0B0B0;
}}
PushButton#btnGo:pressed {{
    background-color: #E8E8E8;
}}
"""


def apply_theme_styles(widget: QWidget) -> None:
    """将当前主题的 QSS 样式和调色板应用到窗口及其子控件"""
    widget.setStyleSheet(DARK_QSS if isDarkTheme() else LIGHT_QSS)
    app = QApplication.instance()
    if isinstance(app, QApplication):
        app.setPalette(_palette())
    polish_theme_widgets(widget)


def polish_theme_widgets(widget: QWidget) -> None:
    """确保所有 QLabel 子控件背景透明"""
    labels: list[QLabel] = []
    if isinstance(widget, QLabel):
        labels.append(widget)
    labels.extend(widget.findChildren(QLabel))

    for label in labels:
        label.setAutoFillBackground(False)
        label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        style = label.styleSheet().strip()
        fix = "background: transparent; background-color: transparent; border: none;"
        if fix not in style:
            label.setStyleSheet(f"{style}; {fix}" if style else fix)


def dialog_card_style() -> str:
    """返回弹窗内卡片组件的 QSS 样式"""
    bg = DARK_SURFACE if isDarkTheme() else LIGHT_SURFACE
    border = DARK_BORDER_SOFT if isDarkTheme() else LIGHT_BORDER
    return (
        "CardWidget { "
        f"background-color: {bg}; "
        f"border: 1px solid {border}; "
        "border-radius: 8px; "
        "}"
    )


def dialog_style() -> str:
    """返回弹窗的整体 QSS 样式"""
    qss = DARK_QSS if isDarkTheme() else LIGHT_QSS
    return "QDialog { background: transparent; }\n" + qss


def valid_text_color() -> str:
    """选取当前主题下"有效"文本的颜色"""
    return DARK_TEXT if isDarkTheme() else "#000000"


def _palette() -> QPalette:
    """构建当前主题的 QPalette 调色板"""
    pal = QPalette()
    if isDarkTheme():
        pal.setColor(QPalette.ColorRole.Window, QColor(DARK_BG))
        pal.setColor(QPalette.ColorRole.Base, QColor(DARK_FIELD))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(DARK_SURFACE))
        pal.setColor(QPalette.ColorRole.Text, QColor(DARK_TEXT))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(DARK_TEXT))
        pal.setColor(QPalette.ColorRole.Button, QColor(DARK_FIELD))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(DARK_TEXT))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(DARK_MUTED))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(DARK_SELECTION))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    else:
        pal.setColor(QPalette.ColorRole.Window, QColor(LIGHT_BG))
        pal.setColor(QPalette.ColorRole.Base, QColor(LIGHT_SURFACE))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#F3F3F3"))
        pal.setColor(QPalette.ColorRole.Text, QColor(LIGHT_TEXT))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(LIGHT_TEXT))
        pal.setColor(QPalette.ColorRole.Button, QColor(LIGHT_SURFACE))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(LIGHT_TEXT))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(LIGHT_MUTED))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(LIGHT_SELECTION))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    return pal
