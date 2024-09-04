# ui_styles.py
from PySide6.QtWidgets import (QWidget, QStyle, QStyleOption, QPushButton, QMainWindow, QDialog, QLineEdit, 
                               QTextEdit, QSpinBox, QProgressBar, QStatusBar, QComboBox, QTableWidget, QFrame, 
                               QTabWidget, QLabel, QCheckBox, QRadioButton, QGroupBox, QScrollArea, QMenuBar, 
                               QMenu, QDateTimeEdit, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, 
                               QDateEdit, QMessageBox, QSizePolicy, QFormLayout, QDialogButtonBox, QDoubleSpinBox, 
                               QAbstractItemView, QFileDialog, QTimeEdit, QSplitter)
from PySide6.QtGui import QColor, QPalette, QFont, QPainter, QIcon
from PySide6.QtCore import Qt

class Colors:
    PRIMARY = "#005A8C"      # Deep Navy Blue
    SECONDARY = "#00334E"    # Darker Navy Blue
    BACKGROUND = "#F0F4F8"   # Light Gray-Blue
    CONTENT_BACKGROUND = "#FFFFFF"  # White
    TEXT = "#333333"         # Dark Gray (almost black)
    ACCENT = "#FF6B35"       # Muted Orange (for warnings/alerts)
    LIGHT_GRAY = "#E1E5E8"   # Light Gray
    MEDIUM_GRAY = "#B0B8C1"  # Medium Gray
    DARK_GRAY = "#5A6978"    # Slate Gray
    SUCCESS = "#28A745"      # Green
    TABLE_HEADER = "#005A8C" # Deep Navy Blue
    WARNING = "#FFC107"      # Amber (for warnings)
    DANGER = "#DC3545"       # Red (for errors/critical alerts)

class Fonts:
    MAIN = QFont("Roboto", 10)
    TITLE = QFont("Roboto", 16, QFont.Weight.Bold)
    SUBTITLE = QFont("Roboto", 14, QFont.Weight.DemiBold)
    LOGO = QFont("Roboto", 24, QFont.Weight.Bold)

BUTTON_ICONS = {
    "search": "SP_FileDialogContentsView",
    "add": "SP_FileDialogNewFolder",
    "edit": "SP_FileDialogDetailedView",
    "modify": "SP_FileDialogInfoView",
    "delete": "SP_TrashIcon",
    "connect": "SP_DriveNetIcon",
    "disconnect": "SP_BrowserStop",
    "info": "SP_MessageBoxInformation",
    "warning": "SP_MessageBoxWarning",
    "critical": "SP_MessageBoxCritical",
    "question": "SP_MessageBoxQuestion",
}

class Styles:
    @staticmethod
    def apply_base_styles(app):
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BACKGROUND))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT))
        palette.setColor(QPalette.ColorRole.Base, QColor(Colors.CONTENT_BACKGROUND))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.LIGHT_GRAY))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.DARK_GRAY))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Colors.TEXT))
        palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT))
        palette.setColor(QPalette.ColorRole.Button, QColor(Colors.PRIMARY))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.CONTENT_BACKGROUND))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(Colors.CONTENT_BACKGROUND))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.PRIMARY))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.CONTENT_BACKGROUND))
        app.setPalette(palette)
        app.setFont(Fonts.MAIN)

    @staticmethod
    def main_window():
        return f"""
        QMainWindow {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
        }}
        """
    @staticmethod
    def connection_status_label(is_connected):
        color = Colors.SUCCESS if is_connected else Colors.ACCENT
        return f"""
        QLabel {{
            color: {color};
            font-weight: bold;
            padding-right: 10px;
            {Styles.label()}
        }}
        """
    @staticmethod
    def dialog():
        return f"""
        QDialog {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
        }}
        """

    @staticmethod
    def widget():
        return f"""
        QWidget {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
        }}
        """

    @staticmethod
    def push_button(button_type=None):
        base_style = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: {Colors.CONTENT_BACKGROUND};
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.SECONDARY};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK_GRAY};
            padding-top: 9px;
            padding-bottom: 7px;
        }}
        QPushButton:disabled {{
            background-color: {Colors.MEDIUM_GRAY};
            color: {Colors.LIGHT_GRAY};
        }}
        """
        
        if button_type and button_type in BUTTON_ICONS:
            base_style += f"""
            QPushButton {{
                padding-left: 32px;
                text-align: left;
            }}
            """
        
        return base_style

    @staticmethod
    def set_button_icon(button, button_type):
        if button_type in BUTTON_ICONS:
            icon = QIcon(button.style().standardIcon(getattr(QStyle.StandardPixmap, BUTTON_ICONS[button_type])))
            button.setIcon(icon)

    @staticmethod
    def line_edit():
        return f"""
        QLineEdit {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            padding: 6px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QLineEdit:focus {{
            border: 2px solid {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def text_edit():
        return f"""
        QTextEdit {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            padding: 6px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QTextEdit:focus {{
            border: 2px solid {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def spin_box():
        return f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            padding: 6px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 16px;
            background-color: {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def progress_bar():
        return f"""
        QProgressBar {{
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            background-color: {Colors.CONTENT_BACKGROUND};
            text-align: center;
            color: {Colors.TEXT};
        }}
        QProgressBar::chunk {{
            background-color: {Colors.PRIMARY};
            border-radius: 3px;
        }}
        """

    @staticmethod
    def status_bar():
        return f"""
        QStatusBar {{
            background-color: {Colors.DARK_GRAY};
            color: {Colors.TEXT};
        }}
        """

    @staticmethod
    def combo_box():
        return f"""
        QComboBox {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            padding: 6px;
            min-width: 6em;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QComboBox:focus {{
            border: 2px solid {Colors.PRIMARY};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 16px;
            border-left-width: 1px;
            border-left-color: {Colors.LIGHT_GRAY};
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {Colors.LIGHT_GRAY};
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            selection-background-color: {Colors.PRIMARY};
            selection-color: {Colors.TEXT};
        }}
        """

    @staticmethod
    def table_widget():
        return f"""
        QTableWidget {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            gridline-color: {Colors.LIGHT_GRAY};
            border: none;
            border-radius: 4px;
        }}
        QTableWidget QHeaderView::section {{
            background-color: {Colors.TABLE_HEADER};
            color: {Colors.CONTENT_BACKGROUND};
            padding: 8px;
            border: none;
            font-weight: bold;
        }}
        QTableWidget::item {{
            padding: 6px;
        }}
        QTableWidget::item:selected {{
            background-color: {Colors.PRIMARY};
            color: {Colors.CONTENT_BACKGROUND};
        }}
        QTableWidget::item:hover {{
            background-color: {Colors.LIGHT_GRAY};
        }}
        QTableWidget QHeaderView::section:horizontal {{
            stretch: 1;
        }}
        QTableWidget QHeaderView::section:vertical {{
            resize: none;
        }}
        QTableWidget QHeaderView {{
            background-color: {Colors.TABLE_HEADER};
        }}
        """

    @staticmethod
    def frame():
        return f"""
        QFrame {{
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
        }}
        """

    @staticmethod
    def tab_widget():
        return f"""
        QTabWidget::pane {{
            border: 1px solid {Colors.LIGHT_GRAY};
            background-color: {Colors.CONTENT_BACKGROUND};
            border-radius: 4px;
        }}
        QTabBar::tab {{
            background-color: {Colors.LIGHT_GRAY};
            color: {Colors.TEXT};
            border: none;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background-color: {Colors.PRIMARY};
            color: {Colors.CONTENT_BACKGROUND};
        }}
        """

    @staticmethod
    def label():
        return f"""
        QLabel {{
            color: {Colors.TEXT};
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        """

    @staticmethod
    def check_box():
        return f"""
        QCheckBox {{
            spacing: 6px;
            color: {Colors.TEXT};
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 1px solid {Colors.LIGHT_GRAY};
        }}
        QCheckBox::indicator:unchecked {{
            background-color: {Colors.CONTENT_BACKGROUND};
        }}
        QCheckBox::indicator:checked {{
            background-color: {Colors.PRIMARY};
            border: 1px solid {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def radio_button():
        return f"""
        QRadioButton {{
            spacing: 6px;
            color: {Colors.TEXT};
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid {Colors.LIGHT_GRAY};
        }}
        QRadioButton::indicator:unchecked {{
            background-color: {Colors.CONTENT_BACKGROUND};
        }}
        QRadioButton::indicator:checked {{
            background-color: {Colors.PRIMARY};
            border: 1px solid {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def group_box():
        return f"""
        QGroupBox {{
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            margin-top: 8px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
            color: {Colors.TEXT};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px;
            color: {Colors.TEXT};
        }}
        """

    @staticmethod
    def scroll_area():
        return f"""
        QScrollArea {{
            background-color: {Colors.BACKGROUND};
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background-color: {Colors.BACKGROUND};
        }}
        QScrollBar:vertical {{
            background-color: {Colors.LIGHT_GRAY};
            width: 14px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {Colors.MEDIUM_GRAY};
            min-height: 20px;
            border-radius: 7px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        """

    @staticmethod
    def menu_bar():
        return f"""
        QMenuBar {{
            background-color: {Colors.DARK_GRAY};
            color: {Colors.TEXT};
        }}
        QMenuBar::item:selected {{
            background-color: {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def menu():
        return f"""
        QMenu {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
        }}
        QMenu::item:selected {{
            background-color: {Colors.PRIMARY};
        }}
        """

    @staticmethod
    def date_time_edit():
        return f"""
        QDateTimeEdit, QDateEdit, QTimeEdit {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
            border-radius: 4px;
            padding: 6px;
            font-family: 'Roboto', sans-serif;
            font-size: 12px;
        }}
        QDateTimeEdit::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 16px;
            border-left-width: 1px;
            border-left-color: {Colors.LIGHT_GRAY};
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }}
        """

    @staticmethod
    def splitter():
        return f"""
        QSplitter::handle {{
            background-color: {Colors.LIGHT_GRAY};
        }}
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        QSplitter::handle:vertical {{
            height: 1px;
        }}
        """

    @staticmethod
    def file_dialog():
        return f"""
        QFileDialog {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
        }}
        QFileDialog QListView, QFileDialog QTreeView, QFileDialog QTableView {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.LIGHT_GRAY};
        }}
        QFileDialog QPushButton {{
            background-color: {Colors.PRIMARY};
            color: {Colors.TEXT};
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }}
        """

    @staticmethod
    def message_box():
        return f"""
        QMessageBox {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
        }}
        QMessageBox QPushButton {{
            background-color: {Colors.PRIMARY};
            color: {Colors.TEXT};
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }}
        """

    @staticmethod
    def dialog_button_box():
        return f"""
        QDialogButtonBox {{
            button-layout: 0;
        }}
        QDialogButtonBox QPushButton {{
            background-color: {Colors.PRIMARY};
            color: {Colors.TEXT};
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
            min-width: 80px;
        }}
        QDialogButtonBox QPushButton:hover {{
            background-color: {Colors.ACCENT};
        }}
        """

    @staticmethod
    def header_view():
        return f"""
        QHeaderView::section {{
            background-color: {Colors.TABLE_HEADER};
            color: {Colors.CONTENT_BACKGROUND};
            padding: 5px;
            border: none;
            font-weight: bold;
        }}
        QHeaderView::section:horizontal {{
            border-right: 1px solid {Colors.LIGHT_GRAY};
        }}
        QHeaderView::section:vertical {{
            border-bottom: 1px solid {Colors.LIGHT_GRAY};
        }}
        """

    @staticmethod
    def abstract_item_view():
        return f"""
        QAbstractItemView {{
            background-color: {Colors.CONTENT_BACKGROUND};
            color: {Colors.TEXT};
            selection-background-color: {Colors.PRIMARY};
            selection-color: {Colors.CONTENT_BACKGROUND};
            alternate-background-color: {Colors.LIGHT_GRAY};
        }}
        """
    
class TMSWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

class StyledPushButton(QPushButton):
    def __init__(self, text, button_type=None, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(Styles.push_button(button_type))
        if button_type:
            Styles.set_button_icon(self, button_type)

def apply_styles(widget, recursive=True):
    style_mapping = {
        QWidget: Styles.widget,
        QMainWindow: Styles.main_window,
        QDialog: Styles.dialog,
        QPushButton: Styles.push_button,
        QLineEdit: Styles.line_edit,
        QTextEdit: Styles.text_edit,
        QSpinBox: Styles.spin_box,
        QDoubleSpinBox: Styles.spin_box,
        QProgressBar: Styles.progress_bar,
        QStatusBar: Styles.status_bar,
        QComboBox: Styles.combo_box,
        QTableWidget: Styles.table_widget,
        QFrame: Styles.frame,
        QTabWidget: Styles.tab_widget,
        QLabel: Styles.label,
        QCheckBox: Styles.check_box,
        QRadioButton: Styles.radio_button,
        QGroupBox: Styles.group_box,
        QScrollArea: Styles.scroll_area,
        QMenuBar: Styles.menu_bar,
        QMenu: Styles.menu,
        QDateTimeEdit: Styles.date_time_edit,
        QDateEdit: Styles.date_time_edit,
        QTimeEdit: Styles.date_time_edit,
        QSplitter: Styles.splitter,
        QFileDialog: Styles.file_dialog,
        QMessageBox: Styles.message_box,
        QDialogButtonBox: Styles.dialog_button_box,
        QHeaderView: Styles.header_view,
        QAbstractItemView: Styles.abstract_item_view,
    }

    for widget_type, style_method in style_mapping.items():
        if isinstance(widget, widget_type):
            try:
                widget.setStyleSheet(style_method())
            except Exception as e:
                print(f"Error applying {style_method.__name__} to {type(widget).__name__}: {str(e)}")
            break

    # Apply content_area style to widgets with 'content' object name
    if hasattr(widget, 'objectName') and widget.objectName() == 'content':
        try:
            widget.setStyleSheet(Styles.widget())
        except Exception as e:
            print(f"Error applying content_area style: {str(e)}")

    # Recursively apply styles to child widgets
    if recursive and hasattr(widget, 'findChildren'):
        for child in widget.findChildren(QWidget):
            apply_styles(child, recursive=False)

def apply_table_styles(table_widget):
    if isinstance(table_widget, QTableWidget):
        table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table_widget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table_widget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Apply header styles
        table_widget.horizontalHeader().setStyleSheet(Styles.header_view())
        table_widget.verticalHeader().setStyleSheet(Styles.header_view())
def set_layout_properties(widget):
    if hasattr(widget, 'layout'):
        layout = widget.layout()
        if isinstance(layout, QVBoxLayout) or isinstance(layout, QHBoxLayout) or isinstance(layout, QFormLayout):
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)