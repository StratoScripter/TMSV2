# loadingarm_ui.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QComboBox, QDateEdit,
                               QMessageBox, QHeaderView, QAbstractItemView, QTabWidget, QLabel, QSplitter,
                               QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QDate, Slot, QDateTime
from PySide6.QtGui import QDoubleValidator, QPainter
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from .loadingarm import loading_arm_module
from .modbus import modbus_module
from .server import server_module
from ui.ui_styles import apply_styles, Styles, TMSWidget
import logging
import datetime

logger = logging.getLogger(__name__)

class LoadingArmWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.is_modbus_connected = False
        apply_styles(self)
        self.init_ui()

        loading_arm_module.realtime_data_updated.connect(self.update_realtime_data)
        loading_arm_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)
        modbus_module.modbus_connected.connect(self.set_modbus_connection_status)

        # Check initial Modbus connection status
        self.set_modbus_connection_status(modbus_module.is_modbus_connected)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tab_widget)
        # Real-time tab
        self.realtime_widget = QWidget()
        self.realtime_layout = QVBoxLayout(self.realtime_widget)
        self.tab_widget.addTab(self.realtime_widget, "Real-time Data")

        # Historical tab
        self.historical_widget = QWidget()
        self.historical_layout = QVBoxLayout(self.historical_widget)
        self.tab_widget.addTab(self.historical_widget, "Historical Data")

        # Real-time table
        self.realtime_table = QTableWidget()
        self.realtime_layout.addWidget(self.realtime_table)

        # Real-time chart
        self.realtime_chart_widget = RealTimeChartWidget()
        self.realtime_layout.addWidget(self.realtime_chart_widget)

        # Add, Edit, Delete buttons for real-time tab
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Loading Arm")
        self.edit_button = QPushButton("Edit Loading Arm")
        self.delete_button = QPushButton("Delete Loading Arm")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        self.realtime_layout.addLayout(button_layout)

        # Historical layout
        historical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.historical_layout.addWidget(historical_splitter)

        # Historical table
        self.historical_table = QTableWidget()
        historical_splitter.addWidget(self.historical_table)

        # Chart view
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        historical_splitter.addWidget(self.chart_view)

        # Date range for historical data
        date_range_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.fetch_historical_button = QPushButton("Fetch Historical Data")
        date_range_layout.addWidget(QLabel("Start Date:"))
        date_range_layout.addWidget(self.start_date)
        date_range_layout.addWidget(QLabel("End Date:"))
        date_range_layout.addWidget(self.end_date)
        date_range_layout.addWidget(self.fetch_historical_button)
        self.historical_layout.addLayout(date_range_layout)

        # Set up the tables
        self.setup_realtime_table()
        self.setup_historical_table()

        # Connect signals
        self.add_button.clicked.connect(self.add_loading_arm)
        self.edit_button.clicked.connect(self.edit_loading_arm)
        self.delete_button.clicked.connect(self.delete_loading_arm)
        self.fetch_historical_button.clicked.connect(self.fetch_historical_data)

        self.update_ui_elements()

    def setup_realtime_table(self):
        self.realtime_table.setColumnCount(7)
        self.realtime_table.setHorizontalHeaderLabels([
            "Loading Arm Name", "Code", "Flow Rate", "Active", "Loading Weight", "Unit", "Last Reading"
        ])
        self.realtime_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.realtime_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.realtime_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.realtime_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def setup_historical_table(self):
        self.historical_table.setColumnCount(9)
        self.historical_table.setHorizontalHeaderLabels([
            "Loading Arm Code", "Loading Arm Name", "Seller Name", "Buyer Name",
            "Product Name", "Loading Weight", "Unit", "Order Date", "Order Time"
        ])
        self.historical_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.historical_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.historical_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.historical_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    @Slot(list)
    def update_realtime_data(self, data):
        self.realtime_table.setRowCount(len(data))
        for row, arm in enumerate(data):
            self.realtime_table.setItem(row, 0, QTableWidgetItem(arm['name']))
            self.realtime_table.setItem(row, 1, QTableWidgetItem(arm['code']))
            self.realtime_table.setItem(row, 2, QTableWidgetItem(f"{arm['flow_rate']:.2f}"))
            self.realtime_table.setItem(row, 3, QTableWidgetItem("Yes" if arm['is_active'] else "No"))
            self.realtime_table.setItem(row, 4, QTableWidgetItem(f"{arm['loading_weight']:.2f}"))
            self.realtime_table.setItem(row, 5, QTableWidgetItem(arm['unit_name']))
            self.realtime_table.setItem(row, 6, QTableWidgetItem(str(arm['last_reading_datetime'])))

        self.realtime_chart_widget.update_chart(data)

    def fetch_historical_data(self):
        start_date = self.start_date.date().toPython()
        end_date = self.end_date.date().toPython()
        historical_data = loading_arm_module.get_historical_loading_arm_data(start_date, end_date)

        if isinstance(historical_data, list):
            self.historical_table.setRowCount(len(historical_data))
            for row, data in enumerate(historical_data):
                self.historical_table.setItem(row, 0, QTableWidgetItem(str(data['LoadingArmCode'])))
                self.historical_table.setItem(row, 1, QTableWidgetItem(str(data['LoadingArmName'])))
                self.historical_table.setItem(row, 2, QTableWidgetItem(str(data['SellerName'])))
                self.historical_table.setItem(row, 3, QTableWidgetItem(str(data['BuyerName'])))
                self.historical_table.setItem(row, 4, QTableWidgetItem(str(data['ProductName'])))
                self.historical_table.setItem(row, 5, QTableWidgetItem(str(data['LoadingWeight'])))
                self.historical_table.setItem(row, 6, QTableWidgetItem(str(data['UnitName'])))
                self.historical_table.setItem(row, 7, QTableWidgetItem(str(data['LoadingDate'])))
                self.historical_table.setItem(row, 8, QTableWidgetItem(str(data['LoadingTime'])))

            self.plot_historical_data(historical_data)
        else:
            self.historical_table.setRowCount(0)
            QMessageBox.warning(self, "No Data", "No historical data found for the selected date range.")

    def plot_historical_data(self, data):
        chart = QChart()
        chart.setTitle("Historical Loading Data")

        series = QLineSeries()
        series.setName("Loading Weight")

        for row in data:
            # Convert the date and time strings to QDateTime
            date_str = str(row['LoadingDate'])
            time_str = str(row['LoadingTime'])
            dt = QDateTime.fromString(f"{date_str} {time_str}", "yyyy-MM-dd HH:mm:ss")
            timestamp = dt.toMSecsSinceEpoch()
            series.append(timestamp, float(row['LoadingWeight']))

        chart.addSeries(series)

        date_axis = QDateTimeAxis()
        date_axis.setFormat("dd-MM-yyyy hh:mm")
        chart.addAxis(date_axis, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(date_axis)

        value_axis = QValueAxis()
        chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(value_axis)

        self.chart_view.setChart(chart)

    def set_connection_status(self, is_connected, message):
        self.is_connected = is_connected
        self.update_ui_elements()
        if is_connected:
            loading_arm_module.fetch_realtime_loading_arms()
        else:
            self.realtime_table.setRowCount(0)
            self.historical_table.setRowCount(0)

    def set_modbus_connection_status(self, is_connected):
        self.is_modbus_connected = is_connected
        if is_connected:
            self.realtime_chart_widget.start_chart_updates()
        else:
            self.realtime_chart_widget.stop_chart_updates()
        self.update_ui_elements()

    def update_ui_elements(self):
        enabled = self.is_connected and self.is_modbus_connected
        self.realtime_table.setEnabled(enabled)
        self.historical_table.setEnabled(self.is_connected)
        self.start_date.setEnabled(self.is_connected)
        self.end_date.setEnabled(self.is_connected)
        self.fetch_historical_button.setEnabled(self.is_connected)
        self.add_button.setEnabled(self.is_connected)
        self.edit_button.setEnabled(self.is_connected)
        self.delete_button.setEnabled(self.is_connected)
        self.realtime_chart_widget.setEnabled(enabled)

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def add_loading_arm(self):
        dialog = LoadingArmDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if loading_arm_module.add_loading_arm(**data):
                QMessageBox.information(self, "Success", "Loading arm added successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to add loading arm.")

    def edit_loading_arm(self):
        selected_row = self.realtime_table.currentRow()
        if selected_row >= 0:
            loading_arm_id = loading_arm_module.loading_arms[selected_row]['id']
            dialog = LoadingArmDialog(self, loading_arm_id)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if loading_arm_module.update_loading_arm(**data):
                    QMessageBox.information(self, "Success", "Loading arm updated successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to update loading arm.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a loading arm to edit.")

    def delete_loading_arm(self):
        selected_row = self.realtime_table.currentRow()
        if selected_row >= 0:
            loading_arm = loading_arm_module.loading_arms[selected_row]
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                           f"Are you sure you want to delete {loading_arm['name']}?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if loading_arm_module.delete_loading_arm(loading_arm['id']):
                    QMessageBox.information(self, "Success", "Loading arm deleted successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete loading arm.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a loading arm to delete.")

class LoadingArmDialog(QDialog):
    def __init__(self, parent=None, loading_arm_id=None):
        super().__init__(parent)
        self.loading_arm_id = loading_arm_id
        self.setWindowTitle("Add Loading Arm" if loading_arm_id is None else "Edit Loading Arm")
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.code_input = QLineEdit()
        self.name_input = QLineEdit()
        self.loading_weight_input = QLineEdit()
        self.loading_weight_input.setValidator(QDoubleValidator(0, 1000000, 2, self))
        self.unit_combo = QComboBox()
        self.remarks_input = QLineEdit()

        layout.addRow("Loading Arm Code:", self.code_input)
        layout.addRow("Loading Arm Name:", self.name_input)
        layout.addRow("Loading Weight:", self.loading_weight_input)
        layout.addRow("Unit:", self.unit_combo)
        layout.addRow("Remarks:", self.remarks_input)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)
        layout.addRow(buttons)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.populate_units()
        if self.loading_arm_id:
            self.populate_data()

    def populate_units(self):
        units = loading_arm_module.get_units()
        self.unit_combo.clear()
        if units and isinstance(units, list):
            for unit in units:
                self.unit_combo.addItem(str(unit['UnitName']), unit['UnitId'])
        else:
            QMessageBox.warning(self, "No Units", "No units found in the database.")

    def populate_data(self):
        details = loading_arm_module.get_loading_arm_details(self.loading_arm_id)
        if details:
            self.code_input.setText(details['LoadingArmCode'])
            self.name_input.setText(details['LoadingArmName'])
            self.loading_weight_input.setText(str(details['LoadingWeight']))
            index = self.unit_combo.findData(details['UnitId'])
            if index >= 0:
                self.unit_combo.setCurrentIndex(index)
            self.remarks_input.setText(details['Remarks'] if details['Remarks'] else '')
        else:
            QMessageBox.warning(self, "Error", "Failed to retrieve loading arm details.")

    def get_data(self):
        data = {
            'code': self.code_input.text(),
            'name': self.name_input.text(),
            'loading_weight': float(self.loading_weight_input.text()),
            'unit_id': self.unit_combo.currentData(),
            'remarks': self.remarks_input.text()
        }
        if self.loading_arm_id:
            data['loading_arm_id'] = self.loading_arm_id
        return data

class RealTimeChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_chart)

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.chart_view)

        self.chart = QChart()
        self.chart.setTitle("Real-Time Flow Rates")
        self.chart_view.setChart(self.chart)

        self.time_axis = QDateTimeAxis()
        self.time_axis.setFormat("hh:mm:ss")
        self.time_axis.setTitleText("Time")
        self.chart.addAxis(self.time_axis, Qt.AlignmentFlag.AlignBottom)

        self.value_axis = QValueAxis()
        self.value_axis.setTitleText("Flow Rate")
        self.chart.addAxis(self.value_axis, Qt.AlignmentFlag.AlignLeft)

        self.series_dict = {}

    def start_chart_updates(self):
        self.update_timer.start(1000)  # Update every second

    def stop_chart_updates(self):
        self.update_timer.stop()

    def update_chart(self, data=None):
        if data is None:
            data = loading_arm_module.loading_arms

        current_time = QDateTime.currentDateTime()

        for arm in data:
            if arm['name'] not in self.series_dict:
                new_series = QLineSeries()
                new_series.setName(arm['name'])
                self.chart.addSeries(new_series)
                new_series.attachAxis(self.time_axis)
                new_series.attachAxis(self.value_axis)
                self.series_dict[arm['name']] = new_series

            series = self.series_dict[arm['name']]
            series.append(current_time.toMSecsSinceEpoch(), arm['flow_rate'])

            # Keep only the last 50 points to avoid cluttering
            if series.count() > 50:
                series.remove(0)

        self.time_axis.setRange(current_time.addSecs(-300), current_time)  # Show last 5 minutes

        if data:
            self.value_axis.setRange(0, max(arm['flow_rate'] for arm in data) * 1.1)  # Set y-axis range with 10% margin
        else:
            self.value_axis.setRange(0, 1)  # Default range when no data is available

        # Remove series for loading arms that no longer exist
        arm_names = set(arm['name'] for arm in data)
        for name in list(self.series_dict.keys()):
            if name not in arm_names:
                self.chart.removeSeries(self.series_dict[name])
                del self.series_dict[name]

    def clear_chart(self):
        for series in self.series_dict.values():
            self.chart.removeSeries(series)
        self.series_dict.clear()