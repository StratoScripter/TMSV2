from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QHeaderView,
                             QTableWidgetItem, QLabel, QMessageBox, QComboBox, QDateEdit,
                             QRadioButton, QButtonGroup, QFrame, QScrollArea)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from .report import ReportModule
from modules.base_table_widget import BaseTableWidget
from ui.ui_styles import apply_styles
from modules.logger_config import get_logger
from datetime import date

logger = get_logger('report_ui')

class ReportWidget(BaseTableWidget):
    def __init__(self, main_window, server_module):
        super().__init__(main_window)
        self.server_module = server_module
        self.report_module = None
        apply_styles(self, 'historical')
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.setup_server_selection(scroll_layout)
        self.create_top_bar()
        scroll_layout.addWidget(self.top_bar)

        self.report_table = QTableWidget()
        self.create_report_table()
        self.add_table(self.report_table)
        scroll_layout.addWidget(self.report_table)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def setup_server_selection(self, layout):
        server_frame = QFrame()
        server_layout = QHBoxLayout(server_frame)
        server_label = QLabel("Select Server:")
        self.server_combo = QComboBox()
        self.server_combo.addItem("Select a server", None)
        self.server_combo.currentIndexChanged.connect(self.on_server_changed)
        server_layout.addWidget(server_label)
        server_layout.addWidget(self.server_combo)
        layout.addWidget(server_frame)

    def create_top_bar(self):
        self.top_bar = QFrame()
        bar_layout = QHBoxLayout(self.top_bar)
        bar_layout.setSpacing(10)
        
        self.product_radio = QRadioButton("Product")
        self.customer_radio = QRadioButton("Customer")
        self.report_type_group = QButtonGroup(self)
        self.report_type_group.addButton(self.product_radio)
        self.report_type_group.addButton(self.customer_radio)
        self.product_radio.setChecked(True)

        self.start_date_label = QLabel("Start Date:")
        self.start_date_input = QDateEdit()
        self.start_date_input.setDate(QDate.currentDate().addDays(-30))
        self.end_date_label = QLabel("End Date:")
        self.end_date_input = QDateEdit()
        self.end_date_input.setDate(QDate.currentDate())

        self.generate_button = QPushButton("Generate Report")

        bar_layout.addWidget(self.product_radio)
        bar_layout.addWidget(self.customer_radio)
        bar_layout.addWidget(self.start_date_label)
        bar_layout.addWidget(self.start_date_input)
        bar_layout.addWidget(self.end_date_label)
        bar_layout.addWidget(self.end_date_input)
        bar_layout.addWidget(self.generate_button)
        bar_layout.addStretch(1)

        self.generate_button.clicked.connect(self.generate_report)

    def create_report_table(self):
        headers = ["Report ID", "Title", "Generated On", "Status"]
        self.report_table.setColumnCount(len(headers))
        self.report_table.setHorizontalHeaderLabels(headers)
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.report_table.setSelectionMode(QTableWidget.SingleSelection)
    ...

    def populate_report_table(self, report_data):
        if not report_data:
            self.report_table.setRowCount(0)
            self.report_table.setColumnCount(1)
            self.report_table.setHorizontalHeaderLabels(["No Data"])
            return

        columns = list(report_data[0].keys())
        self.report_table.setColumnCount(len(columns))
        self.report_table.setHorizontalHeaderLabels(columns)

        self.report_table.setRowCount(len(report_data))
        for row, data in enumerate(report_data):
            for col, key in enumerate(columns):
                value = data.get(key, '')
                if isinstance(value, float):
                    value = f"{value:.2f}"
                self.report_table.setItem(row, col, QTableWidgetItem(str(value)))
        
        self.report_table.resizeRowsToContents()
        logger.info(f"Populated {self.report_table.rowCount()} rows in the table")

    def generate_report(self):
        if not self.report_module:
            QMessageBox.warning(self, "No Server Selected", "Please select a server first.")
            return

        report_type = "product" if self.product_radio.isChecked() else "customer"
        start_date = self.start_date_input.date().toPython()
        end_date = self.end_date_input.date().toPython()

        logger.info(f"Generating report: type={report_type}, start_date={start_date}, end_date={end_date}")

        try:
            report_data = self.report_module.get_report_data(report_type, start_date, end_date)

            if report_data:
                self.populate_report_table(report_data)
            else:
                logger.warning("No report data found for the selected criteria.")
                QMessageBox.information(self, "Report Results", "No data found for the selected criteria.")
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            QMessageBox.critical(self, "Report Error", f"An error occurred while generating the report: {str(e)}")

    def update_server_list(self, server_list):
        logger.info(f"Updating server list with {len(server_list)} servers")
        self.server_combo.clear()
        self.server_combo.addItem("Select a server", None)
        for server in server_list:
            self.server_combo.addItem(server.name, server)
        logger.info(f"Server combo box now has {self.server_combo.count()} items")

    def on_server_changed(self, index):
        server_info = self.server_combo.itemData(index)
        if server_info:
            logger.info(f"Attempting to connect to server: {server_info.name}")
            try:
                self.report_module = ReportModule(self.server_module)
                self.report_module.initialize(server_info)
                logger.info("Successfully connected to the database")
                self.generate_report()
            except ConnectionError as e:
                logger.error(f"Failed to connect to the server: {str(e)}")
                QMessageBox.warning(self, "Connection Error", f"Failed to connect to the server: {str(e)}")
        else:
            self.report_module = None
            self.report_table.setRowCount(0)