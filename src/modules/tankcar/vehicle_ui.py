from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
                               QHeaderView, QAbstractItemView, QComboBox)
from PySide6.QtCore import Qt
from .vehicle import vehicle_module
from ui.ui_styles import apply_styles, Styles, TMSWidget
from modules.product.server import server_module
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class VehicleWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        apply_styles(self)
        self.init_ui()
        vehicle_module.data_updated.connect(self.refresh_table)
        vehicle_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)

    def show_error_message(self, message: str):
        logger.error(message)
        # Here you might want to update some UI element to show the error, instead of a message box

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Driver/Vehicle...")
        self.search_button = QPushButton("Search")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Driver/Vehicle")
        self.edit_button = QPushButton("Edit Driver/Vehicle")
        self.delete_button = QPushButton("Delete Driver/Vehicle")
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
        self.search_button.clicked.connect(self.search_driver_vehicles)
        self.add_button.clicked.connect(self.add_driver_vehicle)
        self.edit_button.clicked.connect(self.edit_driver_vehicle)
        self.delete_button.clicked.connect(self.delete_driver_vehicle)
        self.refresh_button.clicked.connect(self.refresh_table)

        self.update_ui_elements()

    def set_connection_status(self, is_connected: bool, message: str):
        self.is_connected = is_connected
        self.update_ui_elements()
        if is_connected:
            self.refresh_table()
        else:
            self.table.setRowCount(0)
        
    def update_server_info(self, server):
        # Update any server-specific information if needed
        pass
        
    def update_ui_elements(self):
        enabled = self.is_connected
        for widget in [self.add_button, self.edit_button, self.delete_button, 
                       self.refresh_button, self.search_button, self.search_input]:
            widget.setEnabled(enabled)

    def refresh_table(self):
        if not self.is_connected:
            return

        self.table.clear()
        if isinstance(vehicle_module.driver_vehicles, list):
            self.table.setRowCount(len(vehicle_module.driver_vehicles))
            self.table.setColumnCount(9)
            self.table.setHorizontalHeaderLabels([
                "Driver ID", "Driver Name", "License Number", "Contact Number",
                "License Plate", "Vehicle Type", "Capacity", "Unit", "Modified Date"
            ])

            for row, dv in enumerate(vehicle_module.driver_vehicles):
                self.table.setItem(row, 0, QTableWidgetItem(str(dv.get('DriverId', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(str(dv.get('DriverName', ''))))
                self.table.setItem(row, 2, QTableWidgetItem(str(dv.get('LicenseNumber', ''))))
                self.table.setItem(row, 3, QTableWidgetItem(str(dv.get('ContactNumber', ''))))
                self.table.setItem(row, 4, QTableWidgetItem(str(dv.get('LicensePlateNumber', ''))))
                self.table.setItem(row, 5, QTableWidgetItem(str(dv.get('VehicleType', ''))))
                self.table.setItem(row, 6, QTableWidgetItem(str(dv.get('Capacity', ''))))
                self.table.setItem(row, 7, QTableWidgetItem(str(dv.get('UnitName', ''))))
                self.table.setItem(row, 8, QTableWidgetItem(str(dv.get('ModifiedDate', ''))))

            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        else:
            logger.error(f"Unexpected type for vehicle_module.driver_vehicles: {type(vehicle_module.driver_vehicles)}")

    def search_driver_vehicles(self):
        if not self.is_connected:
            return
        search_term = self.search_input.text()
        vehicle_module.search_driver_vehicles(search_term)

    def add_driver_vehicle(self):
        if not self.is_connected:
            return
        dialog = DriverVehicleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if vehicle_module.add_driver_vehicle(data):
                logger.info("Driver/Vehicle added successfully.")
                vehicle_module.fetch_driver_vehicles()
            else:
                logger.error("Failed to add driver/vehicle.")

    def edit_driver_vehicle(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(vehicle_module.driver_vehicles, list) and 0 <= selected_row < len(vehicle_module.driver_vehicles):
            dv = vehicle_module.driver_vehicles[selected_row]
            dialog = DriverVehicleDialog(self, dv.get('DriverId'))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if vehicle_module.update_driver_vehicle(data):
                    logger.info("Driver/Vehicle updated successfully.")
                    vehicle_module.fetch_driver_vehicles()
                else:
                    logger.error("Failed to update driver/vehicle.")
        else:
            logger.warning("No driver/vehicle selected for editing.")

    def delete_driver_vehicle(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(vehicle_module.driver_vehicles, list) and 0 <= selected_row < len(vehicle_module.driver_vehicles):
            dv = vehicle_module.driver_vehicles[selected_row]
            driver_id = dv.get('DriverId')
            if driver_id:
                if vehicle_module.delete_driver_vehicle(driver_id):
                    logger.info(f"Driver/Vehicle {dv.get('DriverName', '')} deleted successfully.")
                    vehicle_module.fetch_driver_vehicles()
                else:
                    logger.error(f"Failed to delete driver/vehicle {dv.get('DriverName', '')}.")
            else:
                logger.error("Invalid driver ID for deletion.")
        else:
            logger.warning("No driver/vehicle selected for deletion.")


class DriverVehicleDialog(QDialog):
    def __init__(self, parent=None, driver_id: Optional[str] = None):
        super().__init__(parent)
        self.driver_id = driver_id
        self.setWindowTitle("Add Driver/Vehicle" if driver_id is None else "Edit Driver/Vehicle")
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.driver_name_input = QLineEdit()
        self.license_number_input = QLineEdit()
        self.contact_number_input = QLineEdit()
        self.license_plate_input = QLineEdit()
        self.vehicle_type_input = QLineEdit()
        self.capacity_input = QDoubleSpinBox()
        self.unit_combo = QComboBox()

        self.capacity_input.setRange(0, 1000000)
        self.capacity_input.setDecimals(2)


        layout.addRow("Driver Name:", self.driver_name_input)
        layout.addRow("License Number:", self.license_number_input)
        layout.addRow("Contact Number:", self.contact_number_input)
        layout.addRow("License Plate:", self.license_plate_input)
        layout.addRow("Vehicle Type:", self.vehicle_type_input)
        layout.addRow("Capacity:", self.capacity_input)
        layout.addRow("Unit:", self.unit_combo)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout.addRow(buttons)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.populate_units()
        if self.driver_id:
            self.populate_data()

    def populate_units(self):
        units = vehicle_module.get_units()
        self.unit_combo.clear()
        if units:
            for unit in units:
                self.unit_combo.addItem(unit.get('UnitName', ''), unit.get('UnitId'))
        else:
            self.unit_combo.addItem("No units available", None)

    def populate_data(self):
        details = vehicle_module.get_driver_vehicle_details(self.driver_id)
        if details and isinstance(details, dict):
            self.driver_name_input.setText(str(details.get('DriverName', '')))
            self.license_number_input.setText(str(details.get('LicenseNumber', '')))
            self.contact_number_input.setText(str(details.get('ContactNumber', '')))
            self.license_plate_input.setText(str(details.get('LicensePlateNumber', '')))
            self.vehicle_type_input.setText(str(details.get('VehicleType', '')))
            self.capacity_input.setValue(float(details.get('Capacity', 0)))
            self.set_combo_value(self.unit_combo, details.get('UnitId'))
        else:
            logger.error(f"Invalid driver/vehicle details: {details}")

    def set_combo_value(self, combo: QComboBox, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def get_data(self) -> Dict[str, Any]:
        return {
            'DriverId': self.driver_id,
            'DriverName': self.driver_name_input.text(),
            'LicenseNumber': self.license_number_input.text(),
            'ContactNumber': self.contact_number_input.text(),
            'LicensePlateNumber': self.license_plate_input.text(),
            'VehicleType': self.vehicle_type_input.text(),
            'Capacity': self.capacity_input.value(),
            'UnitId': self.unit_combo.currentData(),
        }