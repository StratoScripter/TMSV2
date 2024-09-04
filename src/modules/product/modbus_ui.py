from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
                               QHeaderView, QAbstractItemView, QComboBox, QSpinBox, QCheckBox,
                               QMessageBox, QTabWidget, QTextEdit, QLabel, QDialogButtonBox, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer, Slot
from .modbus import ModbusModule, modbus_module
from ui.ui_styles import apply_styles, Styles, TMSWidget
from .server import server_module
import datetime
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

class ModbusWidget(TMSWidget):
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.is_connected = False
        apply_styles(self)
        self.modbus_module = modbus_module
        self.init_ui()
        self.data_update_timer = QTimer(self)
        self.data_update_timer.timeout.connect(self.update_data_view)
        self.data_update_timer.start(500)  # Update UI every 500ms for a balance between responsiveness and performance
        self.modbus_module.data_updated.connect(self.on_data_updated)
        server_module.connection_status_changed.connect(self.set_connection_status)
        logger.info("Data update timer started")

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tab_widget)
        self.create_device_management_tab()
        self.create_data_view_tab()
        self.create_error_log_tab()

    def create_device_management_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Server connection status
        self.server_status_label = QLabel("Server Not Connected")
        layout.addWidget(self.server_status_label)

        # Modbus connection section
        modbus_connection_layout = QHBoxLayout()
        self.modbus_connect_button = QPushButton("Connect Modbus")
        self.modbus_disconnect_button = QPushButton("Disconnect Modbus")
        self.modbus_status_label = QLabel("Modbus Not Connected")
        modbus_connection_layout.addWidget(self.modbus_connect_button)
        modbus_connection_layout.addWidget(self.modbus_disconnect_button)
        modbus_connection_layout.addWidget(self.modbus_status_label)
        layout.addLayout(modbus_connection_layout)

        # Read button (now disabled when Modbus is connected)
        self.read_button = QPushButton("Read Slave Devices")
        layout.addWidget(self.read_button)

        # Slave Devices section
        slave_layout = QVBoxLayout()
        slave_layout.addWidget(QLabel("Slave Devices"))

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Device")
        self.edit_button = QPushButton("Edit Device")
        self.delete_button = QPushButton("Delete Device")
        self.refresh_button = QPushButton("Refresh")
        self.register_mapping_button = QPushButton("Register Mapping")

        for button in [self.add_button, self.edit_button, self.delete_button, self.refresh_button, self.register_mapping_button]:
            
            button_layout.addWidget(button)

        slave_layout.addLayout(button_layout)

        self.device_table = QTableWidget()
        
        self.device_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        slave_layout.addWidget(self.device_table)

        layout.addLayout(slave_layout)

        # Connect buttons
        self.modbus_connect_button.clicked.connect(self.open_connection_dialog)
        self.modbus_disconnect_button.clicked.connect(self.disconnect_modbus)
        self.read_button.clicked.connect(self.read_slaves)
        self.add_button.clicked.connect(self.add_device)
        self.edit_button.clicked.connect(self.edit_device)
        self.delete_button.clicked.connect(self.delete_device)
        self.refresh_button.clicked.connect(self.refresh_device_table)
        self.register_mapping_button.clicked.connect(self.open_register_mapping_dialog)
        self.device_table.itemSelectionChanged.connect(self.on_device_selection_changed)

        # Initial button states
        self.update_ui_elements()

        self.tab_widget.addTab(tab, "Device Management")

    def create_data_view_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.data_view_table = QTableWidget()
        
        self.data_view_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.data_view_table.setColumnCount(5)  # Set initial column count
        self.data_view_table.setHorizontalHeaderLabels(["Slave Address", "Register Address", "Value", "Timestamp", "Mapped Entity"])
        layout.addWidget(self.data_view_table)

        self.tab_widget.addTab(tab, "Real-time Data")

    def create_error_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.error_log = QTextEdit()
        self.error_log.setReadOnly(True)
        layout.addWidget(self.error_log)

        self.tab_widget.addTab(tab, "Error Log")

    def set_connection_status(self, is_connected: bool, message: str):
        self.is_connected = is_connected
        self.update_ui_elements()
        if is_connected:
            self.server_status_label.setText("Server Connected")
            self.connect_to_database()
        else:
            self.server_status_label.setText("Server Not Connected")
            self.disconnect_from_database()
        
    def update_server_info(self, server):
        # Update any server-specific information if needed
        pass
        
    def update_ui_elements(self):
        enabled = self.is_connected
        for widget in [self.modbus_connect_button, self.modbus_disconnect_button, 
                       self.read_button, self.add_button, self.edit_button, 
                       self.delete_button, self.refresh_button, self.register_mapping_button]:
            widget.setEnabled(enabled)

    def connect_to_database(self):
        try:
            self.modbus_module.connect_to_database()
            logger.info("Database connected successfully")
            self.refresh_device_table()
        except Exception as e:
            self.log_error(f"Database connection error: {str(e)}")

    def disconnect_from_database(self):
        try:
            self.modbus_module.disconnect_from_database()
            logger.info("Database disconnected successfully")
            self.device_table.setRowCount(0)
        except Exception as e:
            self.log_error(f"Database disconnection error: {str(e)}")

    def open_connection_dialog(self):
        dialog = ConnectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.connect_modbus(dialog.get_connection_params())

    def connect_modbus(self, params):
        try:
            logger.info(f"Attempting to connect to Modbus with parameters: {params}")
            self.modbus_module.set_connection_params(**params)
            self.modbus_module.connect_modbus()
            self.modbus_status_label.setText("Modbus Connected")
            self.modbus_connect_button.setEnabled(False)
            self.modbus_disconnect_button.setEnabled(True)
            self.read_button.setEnabled(False)  # Disable manual read button as reading is now continuous
            logger.info("Successfully connected to Modbus")
        except Exception as e:
            logger.error(f"Error connecting to Modbus: {str(e)}")
            self.log_error(f"Error connecting to Modbus: {str(e)}")

    def disconnect_modbus(self):
        try:
            self.modbus_module.disconnect_modbus()
            self.modbus_status_label.setText("Modbus Disconnected")
            self.modbus_connect_button.setEnabled(True)
            self.modbus_disconnect_button.setEnabled(False)
            self.read_button.setEnabled(True)  # Re-enable manual read button
        except Exception as e:
            self.log_error(f"Modbus disconnection error: {str(e)}")

    def read_slaves(self):
        try:
            self.modbus_module.read_all_slaves()
            self.log_error("Successfully read all slave devices")
            self.update_data_view()
        except Exception as e:
            self.log_error(f"Error reading slave devices: {str(e)}")

    def refresh_device_table(self):
        if not self.modbus_module.is_connected:
            return

        try:
            self.modbus_module.fetch_slaves()
            devices = self.modbus_module.slaves
            self.device_table.setRowCount(len(devices))
            self.device_table.setColumnCount(7)
            self.device_table.setHorizontalHeaderLabels([
                "Slave Address", "Name", "Baudrate", "Port", "Is Active", "Data Bits", "Parity"
            ])

            for row, device in enumerate(devices):
                self.device_table.setItem(row, 0, QTableWidgetItem(str(device['SlaveAddress'])))
                self.device_table.setItem(row, 1, QTableWidgetItem(device['SlaveName']))
                self.device_table.setItem(row, 2, QTableWidgetItem(str(device['Baudrate'])))
                self.device_table.setItem(row, 3, QTableWidgetItem(device['Port']))
                self.device_table.setItem(row, 4, QTableWidgetItem(str(device['IsActive'])))
                self.device_table.setItem(row, 5, QTableWidgetItem(str(device['Databits'])))
                self.device_table.setItem(row, 6, QTableWidgetItem(device['Parity']))

            self.device_table.resizeColumnsToContents()
            self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception as e:
            logger.error(f"Error refreshing device table: {str(e)}")
            self.log_error(f"Error refreshing device table: {str(e)}")

    def add_device(self):
        if not self.modbus_module.is_connected:
            return
        dialog = ModbusDeviceDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                if self.modbus_module.add_slave(**data):
                    logger.info("Device added successfully.")
                    self.refresh_device_table()
                else:
                    logger.error("Failed to add device.")
                    self.log_error("Failed to add device.")
            except Exception as e:
                logger.error(f"Error adding device: {str(e)}")
                self.log_error(f"Error adding device: {str(e)}")

    def edit_device(self):
        if not self.modbus_module.is_connected:
            return
        selected_row = self.device_table.currentRow()
        if 0 <= selected_row < self.device_table.rowCount():
            slave_address = int(self.device_table.item(selected_row, 0).text())
            dialog = ModbusDeviceDialog(self, slave_address)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                try:
                    if self.modbus_module.update_slave(**data):
                        logger.info("Device updated successfully.")
                        self.refresh_device_table()
                    else:
                        logger.error("Failed to update device.")
                        self.log_error("Failed to update device.")
                except Exception as e:
                    logger.error(f"Error updating device: {str(e)}")
                    self.log_error(f"Error updating device: {str(e)}")
        else:
            logger.warning("No device selected for editing.")

    def delete_device(self):
        if not self.modbus_module.is_connected:
            return
        selected_row = self.device_table.currentRow()
        if 0 <= selected_row < self.device_table.rowCount():
            slave_address = int(self.device_table.item(selected_row, 0).text())
            confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this device?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    if self.modbus_module.delete_slave(slave_address):
                        logger.info(f"Device {slave_address} deleted successfully.")
                        self.refresh_device_table()
                    else:
                        logger.error(f"Failed to delete device {slave_address}.")
                        self.log_error(f"Failed to delete device {slave_address}.")
                except Exception as e:
                    logger.error(f"Error deleting device: {str(e)}")
                    self.log_error(f"Error deleting device: {str(e)}")
        else:
            logger.warning("No device selected for deletion.")

    def on_device_selection_changed(self):
        self.register_mapping_button.setEnabled(len(self.device_table.selectedItems()) > 0)

    def open_register_mapping_dialog(self):
        selected_row = self.device_table.currentRow()
        if 0 <= selected_row < self.device_table.rowCount():
            slave_address = int(self.device_table.item(selected_row, 0).text())
            dialog = RegisterMappingDialog(self, self.modbus_module, slave_address)
            dialog.exec()

    @Slot(dict)
    def on_data_updated(self, data):
        self.update_data_view(data)

    def update_data_view(self, latest_data=None):
        if self.modbus_module.is_modbus_connected:
            try:
                if latest_data is None:
                    latest_data = self.modbus_module.last_values
                
                logger.info(f"Updating data view with data: {latest_data}")
                
                if not latest_data:
                    logger.warning("No data available to update the view")
                    return

                self.data_view_table.setRowCount(len(latest_data))
                self.data_view_table.setColumnCount(5)
                self.data_view_table.setHorizontalHeaderLabels(["Slave Address", "Register Address", "Value", "Timestamp", "Mapped Entity"])

                row = 0
                for (slave_address, mapping_id), value in latest_data.items():
                    mapping = self.modbus_module.get_register_mapping_details(mapping_id)
                    if mapping:
                        self.data_view_table.setItem(row, 0, QTableWidgetItem(str(slave_address)))
                        self.data_view_table.setItem(row, 1, QTableWidgetItem(str(mapping['RegisterAddress'])))
                        self.data_view_table.setItem(row, 2, QTableWidgetItem(str(value)))
                        self.data_view_table.setItem(row, 3, QTableWidgetItem(str(datetime.datetime.now())))
                        self.data_view_table.setItem(row, 4, QTableWidgetItem(f"{mapping['MappedTable']}.{mapping['MappedColumn']}"))
                        row += 1
                    else:
                        logger.warning(f"No mapping found for mapping_id: {mapping_id}")

                self.data_view_table.resizeColumnsToContents()
                logger.info(f"Updated data view with {row} rows of data")
            except Exception as e:
                logger.error(f"Error updating data view: {str(e)}", exc_info=True)
                self.log_error(f"Error updating data view: {str(e)}")
        else:
            logger.warning("Modbus not connected, skipping data view update")

    def log_error(self, message: str):
        self.error_log.append(f"{datetime.datetime.now()}: {message}")

class ConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modbus Connection")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.port_input = QLineEdit()
        self.baudrate_input = QComboBox()
        self.baudrate_input.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.parity_input = QComboBox()
        self.parity_input.addItems(['N', 'E', 'O'])
        self.stopbits_input = QComboBox()
        self.stopbits_input.addItems(['1', '2'])
        self.bytesize_input = QComboBox()
        self.bytesize_input.addItems(['7', '8'])
        self.timeout_input = QDoubleSpinBox()
        self.timeout_input.setRange(0.1, 10)
        self.timeout_input.setValue(1)
        self.timeout_input.setSingleStep(0.1)

        layout.addRow("Port:", self.port_input)
        layout.addRow("Baudrate:", self.baudrate_input)
        layout.addRow("Parity:", self.parity_input)
        layout.addRow("Stop Bits:", self.stopbits_input)
        layout.addRow("Byte Size:", self.bytesize_input)
        layout.addRow("Timeout:", self.timeout_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_connection_params(self):
        return {
            'port': self.port_input.text(),
            'baudrate': int(self.baudrate_input.currentText()),
            'parity': self.parity_input.currentText(),
            'stopbits': float(self.stopbits_input.currentText()),
            'bytesize': int(self.bytesize_input.currentText()),
            'timeout': self.timeout_input.value()
        }

class ModbusDeviceDialog(QDialog):
    def __init__(self, parent=None, slave_address: Optional[int] = None):
        super().__init__(parent)
        self.slave_address = slave_address
        self.setWindowTitle("Add Device" if slave_address is None else "Edit Device")
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.slave_address_input = QSpinBox()
        self.slave_address_input.setRange(1, 247)
        self.slave_name_input = QLineEdit()
        self.baudrate_input = QComboBox()
        self.baudrate_input.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.port_input = QLineEdit()
        self.is_active_input = QCheckBox()
        self.databits_input = QComboBox()
        self.databits_input.addItems(['7', '8'])
        self.parity_input = QComboBox()
        self.parity_input.addItems(['N', 'E', 'O'])
        self.stopbits_input = QComboBox()
        self.stopbits_input.addItems(['1', '2'])

        layout.addRow("Slave Address:", self.slave_address_input)
        layout.addRow("Slave Name:", self.slave_name_input)
        layout.addRow("Baudrate:", self.baudrate_input)
        layout.addRow("Port:", self.port_input)
        layout.addRow("Is Active:", self.is_active_input)
        layout.addRow("Data Bits:", self.databits_input)
        layout.addRow("Parity:", self.parity_input)
        layout.addRow("Stop Bits:", self.stopbits_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if self.slave_address is not None:
            self.populate_data()

    def populate_data(self):
        # Populate data for editing (you'll need to implement this based on your data structure)
        pass

    def get_data(self) -> Dict[str, Any]:
        return {
            'slave_address': self.slave_address_input.value(),
            'slave_name': self.slave_name_input.text(),
            'baudrate': int(self.baudrate_input.currentText()),
            'port': self.port_input.text(),
            'is_active': self.is_active_input.isChecked(),
            'databits': int(self.databits_input.currentText()),
            'parity': self.parity_input.currentText(),
            'stopbits': int(self.stopbits_input.currentText())
        }

class RegisterMappingDialog(QDialog):
    def __init__(self, parent, modbus_module: ModbusModule, slave_address: int):
        super().__init__(parent)
        self.modbus_module = modbus_module
        self.slave_address = slave_address
        self.setWindowTitle(f"Register Mapping for Slave {slave_address}")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Register Mapping Table
        self.mapping_table = QTableWidget()
        
        self.mapping_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mapping_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.mapping_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.mapping_table)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_mapping_button = QPushButton("Add Mapping")
        self.edit_mapping_button = QPushButton("Edit Mapping")
        self.delete_mapping_button = QPushButton("Delete Mapping")

        for button in [self.add_mapping_button, self.edit_mapping_button, self.delete_mapping_button]:
            
            button_layout.addWidget(button)

        layout.addLayout(button_layout)

        # Connect buttons
        self.add_mapping_button.clicked.connect(self.add_mapping)
        self.edit_mapping_button.clicked.connect(self.edit_mapping)
        self.delete_mapping_button.clicked.connect(self.delete_mapping)

        self.refresh_mapping_table()

    def refresh_mapping_table(self):
        self.modbus_module.fetch_register_mappings()
        mappings = [mapping for mapping in self.modbus_module.register_mappings.get(self.slave_address, [])]
        self.mapping_table.setRowCount(len(mappings))
        self.mapping_table.setColumnCount(5)
        self.mapping_table.setHorizontalHeaderLabels([
            "Mapping ID", "Register Address", "Register Type", "Mapped Table", "Mapped Column"
        ])

        for row, mapping in enumerate(mappings):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(str(mapping['MappingId'])))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(str(mapping['RegisterAddress'])))
            self.mapping_table.setItem(row, 2, QTableWidgetItem(mapping['RegisterType']))
            self.mapping_table.setItem(row, 3, QTableWidgetItem(mapping['MappedTable']))
            self.mapping_table.setItem(row, 4, QTableWidgetItem(mapping['MappedColumn']))

        self.mapping_table.resizeColumnsToContents()
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def add_mapping(self):
        dialog = MappingDetailDialog(self, self.modbus_module, self.slave_address)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            mapping_data = dialog.get_mapping_data()
            try:
                if self.modbus_module.add_register_mapping(self.slave_address, **mapping_data):
                    logger.info("Register mapping added successfully.")
                    self.refresh_mapping_table()
                else:
                    logger.error("Failed to add register mapping.")
                    QMessageBox.warning(self, "Error", "Failed to add register mapping.")
            except Exception as e:
                logger.error(f"Error adding register mapping: {str(e)}")
                QMessageBox.critical(self, "Error", f"Error adding register mapping: {str(e)}")

    def edit_mapping(self):
        selected_row = self.mapping_table.currentRow()
        if 0 <= selected_row < self.mapping_table.rowCount():
            mapping_id = int(self.mapping_table.item(selected_row, 0).text())
            current_mapping = self.modbus_module.get_register_mapping_details(mapping_id)
            if current_mapping:
                dialog = MappingDetailDialog(self, self.modbus_module, self.slave_address, current_mapping)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    updated_mapping = dialog.get_mapping_data()
                    try:
                        if self.modbus_module.update_register_mapping(mapping_id, self.slave_address, **updated_mapping):
                            logger.info("Register mapping updated successfully.")
                            self.refresh_mapping_table()
                        else:
                            logger.error("Failed to update register mapping.")
                            QMessageBox.warning(self, "Error", "Failed to update register mapping.")
                    except Exception as e:
                        logger.error(f"Error updating register mapping: {str(e)}")
                        QMessageBox.critical(self, "Error", f"Error updating register mapping: {str(e)}")
            else:
                logger.error("Failed to retrieve mapping details.")
                QMessageBox.warning(self, "Error", "Failed to retrieve mapping details.")
        else:
            QMessageBox.warning(self, "Warning", "No mapping selected for editing.")

    def delete_mapping(self):
        selected_row = self.mapping_table.currentRow()
        if 0 <= selected_row < self.mapping_table.rowCount():
            mapping_id = int(self.mapping_table.item(selected_row, 0).text())
            confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this mapping?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    if self.modbus_module.delete_register_mapping(mapping_id):
                        logger.info(f"Register mapping {mapping_id} deleted successfully.")
                        self.refresh_mapping_table()
                    else:
                        logger.error(f"Failed to delete register mapping {mapping_id}.")
                        QMessageBox.warning(self, "Error", f"Failed to delete register mapping {mapping_id}.")
                except Exception as e:
                    logger.error(f"Error deleting register mapping: {str(e)}")
                    QMessageBox.critical(self, "Error", f"Error deleting register mapping: {str(e)}")
        else:
            QMessageBox.warning(self, "Warning", "No mapping selected for deletion.")

class MappingDetailDialog(QDialog):
    def __init__(self, parent, modbus_module: ModbusModule, slave_address: int, mapping: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.modbus_module = modbus_module
        self.slave_address = slave_address
        self.mapping = mapping
        self.setWindowTitle("Register Mapping Details")
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.register_address_input = QSpinBox()
        self.register_address_input.setRange(0, 65535)

        self.register_type_input = QComboBox()
        self.register_type_input.addItems(["Coil", "DiscreteInput", "InputRegister", "HoldingRegister"])

        self.function_code_input = QComboBox()
        self.function_code_input.addItems(["1", "2", "3", "4"])

        self.mapped_table_input = QComboBox()
        self.mapped_table_input.addItems(self.modbus_module.get_available_tables())

        self.mapped_column_input = QComboBox()

        self.mapped_entity_id_input = QSpinBox()
        self.mapped_entity_id_input.setRange(1, 1000000)

        self.scale_factor_input = QDoubleSpinBox()
        self.scale_factor_input.setRange(-1000000, 1000000)
        self.scale_factor_input.setDecimals(6)
        self.scale_factor_input.setValue(1.0)

        self.offset_input = QDoubleSpinBox()
        self.offset_input.setRange(-1000000, 1000000)
        self.offset_input.setDecimals(6)

        self.store_historical_input = QCheckBox()
        self.is_read_only_input = QCheckBox()

        layout.addRow("Register Address:", self.register_address_input)
        layout.addRow("Register Type:", self.register_type_input)
        layout.addRow("Function Code:", self.function_code_input)
        layout.addRow("Mapped Table:", self.mapped_table_input)
        layout.addRow("Mapped Column:", self.mapped_column_input)
        layout.addRow("Mapped Entity ID:", self.mapped_entity_id_input)
        layout.addRow("Scale Factor:", self.scale_factor_input)
        layout.addRow("Offset:", self.offset_input)
        layout.addRow("Store Historical:", self.store_historical_input)
        layout.addRow("Read Only:", self.is_read_only_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.mapped_table_input.currentIndexChanged.connect(self.update_mapped_columns)
        self.update_mapped_columns()

        if self.mapping:
            self.populate_fields()

    def update_mapped_columns(self):
        selected_table = self.mapped_table_input.currentText()
        self.mapped_column_input.clear()
        columns = self.modbus_module.get_table_columns(selected_table)
        if selected_table == "Weighbridge":
            columns.append("CurrentWeight")
        self.mapped_column_input.addItems(columns)

    def populate_fields(self):
        if self.mapping:
            self.register_address_input.setValue(self.mapping['RegisterAddress'])
            self.register_type_input.setCurrentText(self.mapping['RegisterType'])
            self.function_code_input.setCurrentText(str(self.mapping['FunctionCode']))
            self.mapped_table_input.setCurrentText(self.mapping['MappedTable'])
            self.mapped_column_input.setCurrentText(self.mapping['MappedColumn'])
            self.mapped_entity_id_input.setValue(self.mapping['MappedEntityId'])
            self.scale_factor_input.setValue(self.mapping['ScaleFactor'])
            self.offset_input.setValue(self.mapping['Offset'])
            self.store_historical_input.setChecked(self.mapping['StoreHistorical'])
            self.is_read_only_input.setChecked(self.mapping['IsReadOnly'])

    def get_mapping_data(self) -> Dict[str, Any]:
        return {
            'register_address': self.register_address_input.value(),
            'register_type': self.register_type_input.currentText(),
            'function_code': int(self.function_code_input.currentText()),
            'mapped_table': self.mapped_table_input.currentText(),
            'mapped_column': self.mapped_column_input.currentText(),
            'mapped_entity_id': self.mapped_entity_id_input.value(),
            'scale_factor': self.scale_factor_input.value(),
            'offset': self.offset_input.value(),
            'store_historical': self.store_historical_input.isChecked(),
            'is_read_only': self.is_read_only_input.isChecked()
        }