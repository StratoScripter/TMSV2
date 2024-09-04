# storagetank_ui.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QComboBox, QDateTimeEdit,
                               QMessageBox, QHeaderView, QAbstractItemView, QDoubleSpinBox, QTextEdit,
                               QTabWidget, QLabel, QSpinBox, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QDateTime, Slot
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
from ui.ui_styles import apply_styles, Styles, TMSWidget
from .storagetank import storage_tank_module
from .server import server_module
import logging
import datetime

logger = logging.getLogger(__name__)

class StorageTankWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        apply_styles(self)
        self.init_ui()
        storage_tank_module.data_updated.connect(self.refresh_table)
        storage_tank_module.real_time_update.connect(self.update_real_time_data)
        storage_tank_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)

    def show_error_message(self, message):
        QMessageBox.critical(self, "Error", message)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tab_widget)
        # Overview tab
        overview_tab = QWidget()
        self.tab_widget.addTab(overview_tab, "Overview")
        self.setup_overview_tab(overview_tab)

        # Real-time data tab
        realtime_tab = QWidget()
        self.tab_widget.addTab(realtime_tab, "Real-time Data")
        self.setup_realtime_tab(realtime_tab)

        # Historical data tab
        historical_tab = QWidget()
        self.tab_widget.addTab(historical_tab, "Historical Data")
        self.setup_historical_tab(historical_tab)

    def setup_overview_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Storage Tanks...")
        
        self.search_button = QPushButton("Search")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Storage Tank")
        self.edit_button = QPushButton("Edit Storage Tank")
        self.delete_button = QPushButton("Delete Storage Tank")
        self.refresh_button = QPushButton("Refresh")

        for button in [self.add_button, self.edit_button, self.delete_button, self.refresh_button]:
            
            button_layout.addWidget(button)

        layout.addLayout(button_layout)

        # Table
        self.table = QTableWidget()
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Connect signals
        self.search_button.clicked.connect(self.search_storage_tanks)
        self.add_button.clicked.connect(self.add_storage_tank)
        self.edit_button.clicked.connect(self.edit_storage_tank)
        self.delete_button.clicked.connect(self.delete_storage_tank)
        self.refresh_button.clicked.connect(self.refresh_table)

    def setup_realtime_tab(self, tab):
        layout = QVBoxLayout(tab)
        self.realtime_table = QTableWidget()
        
        self.realtime_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.realtime_table)

    def setup_historical_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Date range selection
        date_layout = QHBoxLayout()
        self.start_date = QDateTimeEdit(QDateTime.currentDateTime().addDays(-7))
        self.end_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.fetch_historical_button = QPushButton("Fetch Data")
        self.fetch_historical_button.clicked.connect(self.fetch_historical_data)
        date_layout.addWidget(QLabel("Start Date:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("End Date:"))
        date_layout.addWidget(self.end_date)
        date_layout.addWidget(self.fetch_historical_button)
        layout.addLayout(date_layout)

        # Chart
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.chart_view)

    def set_connection_status(self, is_connected, message):
        self.is_connected = is_connected
        self.update_ui_elements()
        if is_connected:
            self.refresh_table()
        else:
            self.table.setRowCount(0)
            self.realtime_table.setRowCount(0)

    def update_ui_elements(self):
        enabled = self.is_connected
        for widget in [self.add_button, self.edit_button, self.delete_button, 
                       self.refresh_button, self.search_button, self.search_input,
                       self.fetch_historical_button]:
            widget.setEnabled(enabled)

    @Slot()
    def refresh_table(self):
        if not self.is_connected:
            return

        self.table.clear()
        self.table.setRowCount(len(storage_tank_module.storage_tanks))
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Storage Tank Name", "Product Name", "Owner", "Total Volume",
            "Current Volume", "Current Mass", "Current Temperature", "Unit", "Last Reading", "Remarks"
        ])

        for row, tank in enumerate(storage_tank_module.storage_tanks):
            self.table.setItem(row, 0, QTableWidgetItem(tank['name']))
            self.table.setItem(row, 1, QTableWidgetItem(tank['product_name']))
            self.table.setItem(row, 2, QTableWidgetItem(tank['owner_name']))
            self.table.setItem(row, 3, QTableWidgetItem(str(tank['total_volume'])))
            self.table.setItem(row, 4, QTableWidgetItem(str(tank['current_volume'])))
            self.table.setItem(row, 5, QTableWidgetItem(str(tank['current_mass'])))
            self.table.setItem(row, 6, QTableWidgetItem(str(tank['current_temperature'])))
            self.table.setItem(row, 7, QTableWidgetItem(tank['unit_name']))
            self.table.setItem(row, 8, QTableWidgetItem(str(tank['last_reading_datetime'])))
            self.table.setItem(row, 9, QTableWidgetItem(tank['remarks']))

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    @Slot(dict)
    def update_real_time_data(self, data):
        self.realtime_table.clear()
        self.realtime_table.setRowCount(len(data))
        self.realtime_table.setColumnCount(5)
        self.realtime_table.setHorizontalHeaderLabels([
            "Storage Tank Name", "Current Volume", "Current Mass", "Current Temperature", "Last Reading"
        ])

        for row, (tank_id, tank_data) in enumerate(data.items()):
            tank_name = next((tank['name'] for tank in storage_tank_module.storage_tanks if tank['id'] == tank_id), "Unknown")
            self.realtime_table.setItem(row, 0, QTableWidgetItem(tank_name))
            self.realtime_table.setItem(row, 1, QTableWidgetItem(str(tank_data.get('CurrentVolume', 'N/A'))))
            self.realtime_table.setItem(row, 2, QTableWidgetItem(str(tank_data.get('CurrentMass', 'N/A'))))
            self.realtime_table.setItem(row, 3, QTableWidgetItem(str(tank_data.get('CurrentTemperature', 'N/A'))))
            self.realtime_table.setItem(row, 4, QTableWidgetItem(str(datetime.datetime.now())))

        self.realtime_table.resizeColumnsToContents()
        self.realtime_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def search_storage_tanks(self):
        if not self.is_connected:
            return
        search_term = self.search_input.text()
        storage_tank_module.search_storage_tanks(search_term)

    def add_storage_tank(self):
        if not self.is_connected:
            return
        dialog = StorageTankDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if storage_tank_module.add_storage_tank(**data):
                QMessageBox.information(self, "Success", "Storage tank added successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to add storage tank.")

    def edit_storage_tank(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            storage_tank = storage_tank_module.storage_tanks[selected_row]
            dialog = StorageTankDialog(self, str(storage_tank['id']))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if storage_tank_module.update_storage_tank(**data):
                    QMessageBox.information(self, "Success", "Storage tank updated successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to update storage tank.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a storage tank to edit.")

    def delete_storage_tank(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            storage_tank = storage_tank_module.storage_tanks[selected_row]
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                           f"Are you sure you want to delete {storage_tank['name']}?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if storage_tank_module.delete_storage_tank(storage_tank['id']):
                    QMessageBox.information(self, "Success", "Storage tank deleted successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete storage tank.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a storage tank to delete.")

    def fetch_historical_data(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            storage_tank = storage_tank_module.storage_tanks[selected_row]
            start_date = self.start_date.dateTime().toPython()
            end_date = self.end_date.dateTime().toPython()
            historical_data = storage_tank_module.get_historical_data(storage_tank['id'], start_date, end_date)
            self.plot_historical_data(storage_tank['name'], historical_data)
        else:
            QMessageBox.warning(self, "No Selection", "Please select a storage tank to view historical data.")

    def plot_historical_data(self, tank_name, data):
        chart = QChart()
        chart.setTitle(f"Historical Data for {tank_name}")

        volume_series = QLineSeries()
        volume_series.setName("Volume")
        mass_series = QLineSeries()
        mass_series.setName("Mass")
        temperature_series = QLineSeries()
        temperature_series.setName("Temperature")

        for reading in data:
            timestamp = reading['ReadingDateTime'].timestamp() * 1000  # Convert to milliseconds
            volume_series.append(timestamp, reading['Volume'])
            mass_series.append(timestamp, reading['Mass'])
            temperature_series.append(timestamp, reading['Temperature'])

        chart.addSeries(volume_series)
        chart.addSeries(mass_series)
        chart.addSeries(temperature_series)

        date_axis = QDateTimeAxis()
        date_axis.setFormat("dd-MM-yyyy hh:mm")
        chart.addAxis(date_axis, Qt.AlignmentFlag.AlignBottom)
        volume_series.attachAxis(date_axis)
        mass_series.attachAxis(date_axis)
        temperature_series.attachAxis(date_axis)

        value_axis = QValueAxis()
        chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        volume_series.attachAxis(value_axis)
        mass_series.attachAxis(value_axis)
        temperature_series.attachAxis(value_axis)

        self.chart_view.setChart(chart)

class StorageTankDialog(QDialog):
    def __init__(self, parent=None, storage_tank_id=None):
        super().__init__(parent)
        self.storage_tank_id = storage_tank_id
        self.setWindowTitle("Add Storage Tank" if storage_tank_id is None else "Edit Storage Tank")
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.product_combo = QComboBox()
        self.owner_combo = QComboBox()
        self.total_volume_input = QDoubleSpinBox()
        self.current_volume_input = QDoubleSpinBox()
        self.current_mass_input = QDoubleSpinBox()
        self.current_temperature_input = QDoubleSpinBox()
        self.unit_combo = QComboBox()
        self.remarks_input = QTextEdit()

        

        

        

        layout.addRow("Storage Tank Name:", self.name_input)
        layout.addRow("Product:", self.product_combo)
        layout.addRow("Owner:", self.owner_combo)
        layout.addRow("Total Volume:", self.total_volume_input)
        layout.addRow("Current Volume:", self.current_volume_input)
        layout.addRow("Current Mass:", self.current_mass_input)
        layout.addRow("Current Temperature:", self.current_temperature_input)
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

        self.populate_combos()
        if self.storage_tank_id:
            self.populate_data()

    def populate_combos(self):
        products = storage_tank_module.get_products()
        owners = storage_tank_module.get_owners()
        units = storage_tank_module.get_units()

        self._populate_combo(self.product_combo, products)
        self._populate_combo(self.owner_combo, owners)
        self._populate_combo(self.unit_combo, units)

    def _populate_combo(self, combo, items):
        combo.clear()
        if items:
            for item in items:
                combo.addItem(item['ProductName'] if 'ProductName' in item else item['PartyName'] if 'PartyName' in item else item['UnitName'], 
                              item['ProductId'] if 'ProductId' in item else item['PartyId'] if 'PartyId' in item else item['UnitId'])
        else:
            combo.addItem("No items available", None)

    def set_combo_value(self, combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setCurrentIndex(0)  # Set to first item if value not found

    def get_data(self):
        data = {
            'name': self.name_input.text(),
            'product_id': self.product_combo.currentData(),
            'owner_id': self.owner_combo.currentData(),
            'total_volume': self.total_volume_input.value(),
            'current_volume': self.current_volume_input.value(),
            'current_mass': self.current_mass_input.value(),
            'current_temperature': self.current_temperature_input.value(),
            'unit_id': self.unit_combo.currentData(),
            'remarks': self.remarks_input.toPlainText()
        }

        if self.storage_tank_id is not None:
            data['storage_tank_id'] = int(self.storage_tank_id)

        return data

    def populate_data(self):
        details = storage_tank_module.get_storage_tank_details(int(self.storage_tank_id))
        if details:
            self.name_input.setText(details['StorageTankName'])
            self.set_combo_value(self.product_combo, details['ProductId'])
            self.set_combo_value(self.owner_combo, details['OwnerId'])
            self.total_volume_input.setValue(details['TotalVolume'] or 0)
            self.current_volume_input.setValue(details['CurrentVolume'] or 0)
            self.current_mass_input.setValue(details['CurrentMass'] or 0)
            self.current_temperature_input.setValue(details['CurrentTemperature'] or 0)
            self.set_combo_value(self.unit_combo, details['UnitId'])
            self.remarks_input.setPlainText(details['Remarks'] if details['Remarks'] else '')
        else:
            QMessageBox.warning(self, "Error", "Failed to retrieve storage tank details.")

