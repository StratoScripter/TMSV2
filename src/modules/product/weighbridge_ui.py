# weighbridge_ui.py

import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QDateEdit,
                               QMessageBox, QSizePolicy, QDialog, QFormLayout, QComboBox, 
                               QDialogButtonBox, QTabWidget)
from PySide6.QtCore import Qt, Slot, QDate
from PySide6.QtGui import QIcon
from ui.ui_styles import Styles, apply_styles, TMSWidget, StyledPushButton, apply_table_styles, set_layout_properties
from .weighbridge import weighbridge_module

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeighbridgeWidget(TMSWidget):
    """
    Main widget for the weighbridge interface.
    """
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.init_ui()
        apply_styles(self, recursive=True)
        set_layout_properties(self)

        weighbridge_module.realtime_data_updated.connect(self.update_realtime_data)
        weighbridge_module.error_occurred.connect(self.show_error_message)
        weighbridge_module.current_weight_updated.connect(self.update_current_weight)

    def init_ui(self):
        """
        Initialize the user interface.
        """
        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tab_widget)

        self.realtime_tab = QWidget()
        self.init_realtime_tab()
        self.tab_widget.addTab(self.realtime_tab, "Real-time View")

        self.historical_tab = QWidget()
        self.init_historical_tab()
        self.tab_widget.addTab(self.historical_tab, "Historical Data")

        apply_styles(self)

    def init_realtime_tab(self):
        """
        Initialize the real-time data tab.
        """
        layout = QVBoxLayout(self.realtime_tab)

        self.realtime_table = QTableWidget()
        apply_styles(self.realtime_table)
        apply_table_styles(self.realtime_table)
        self.realtime_table.setColumnCount(5)
        self.realtime_table.setHorizontalHeaderLabels([
            "Weighbridge", "Current Weight", "Tare Weight", "Gross Weight", "Status"
        ])
        self.realtime_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.realtime_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        apply_styles(self.realtime_table)
        layout.addWidget(self.realtime_table)

        weighing_layout = QHBoxLayout()
        self.start_weighing_button = StyledPushButton("Start New Weighing", "add")
        self.set_tare_button = StyledPushButton("Set Tare Weight", "edit")
        self.set_gross_button = StyledPushButton("Set Gross Weight", "edit")
        self.cancel_weighing_button = StyledPushButton("Cancel Weighing", "delete")
        weighing_layout.addWidget(self.start_weighing_button)
        weighing_layout.addWidget(self.set_tare_button)
        weighing_layout.addWidget(self.set_gross_button)
        weighing_layout.addWidget(self.cancel_weighing_button)
        layout.addLayout(weighing_layout)

        self.start_weighing_button.clicked.connect(self.start_new_weighing)
        self.set_tare_button.clicked.connect(self.set_tare_weight)
        self.set_gross_button.clicked.connect(self.set_gross_weight)
        self.cancel_weighing_button.clicked.connect(self.cancel_weighing)

    def init_historical_tab(self):
        """
        Initialize the historical data tab.
        """
        layout = QVBoxLayout(self.historical_tab)

        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.end_date = QDateEdit(QDate.currentDate())
        self.product_filter = QLineEdit()
        self.weighbridge_filter = QLineEdit()
        self.filter_button = StyledPushButton("Search", "search")
        
        apply_styles(self.start_date)
        apply_styles(self.end_date)
        apply_styles(self.product_filter)
        apply_styles(self.weighbridge_filter)

        self.product_filter.setPlaceholderText("Filter by Product")
        self.weighbridge_filter.setPlaceholderText("Filter by Weighbridge")
        
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(self.product_filter)
        filter_layout.addWidget(self.weighbridge_filter)
        filter_layout.addWidget(self.filter_button)
        layout.addLayout(filter_layout)

        self.historical_table = QTableWidget()
        apply_styles(self.historical_table)
        apply_table_styles(self.historical_table)
        self.historical_table.setColumnCount(11)
        self.historical_table.setHorizontalHeaderLabels([
            "Date", "Time", "Weighbridge", "Driver", "Vehicle", "Product", 
            "Initial Weight", "Final Weight", "Net Weight", "Status", "Actions"
        ])
        self.historical_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.historical_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        apply_styles(self.historical_table)
        layout.addWidget(self.historical_table)

        self.filter_button.clicked.connect(self.fetch_weighing_records)

    def show_error_message(self, message):
        """
        Display an error message to the user.
        """
        logger.error(f"Error: {message}")
        msg_box = QMessageBox()
        apply_styles(msg_box)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("Error")
        msg_box.exec()

    def show_success_message(self, message):
        """
        Display a success message to the user.
        """
        logger.info(f"Success: {message}")
        msg_box = QMessageBox()
        apply_styles(msg_box)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(message)
        msg_box.setWindowTitle("Success")
        msg_box.exec()

    def show_info_message(self, title, message):
        """
        Display an informational message to the user.
        """
        logger.info(f"Info: {title} - {message}")
        msg_box = QMessageBox()
        apply_styles(msg_box)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.exec()

    @Slot(list)
    def update_realtime_data(self, data):
        """
        Update the real-time data table with current weighbridge information.
        """
        self.realtime_table.setRowCount(len(data))
        
        for row, weighbridge in enumerate(data):
            name_item = QTableWidgetItem(weighbridge.get('name', ''))
            name_item.setData(Qt.ItemDataRole.UserRole, weighbridge.get('id'))
            self.realtime_table.setItem(row, 0, name_item)
            self.realtime_table.setItem(row, 1, QTableWidgetItem(f"{weighbridge.get('current_weight', 0):.2f}"))
            self.realtime_table.setItem(row, 2, QTableWidgetItem(f"{weighbridge.get('tare_weight', 'N/A')}"))
            self.realtime_table.setItem(row, 3, QTableWidgetItem(f"{weighbridge.get('gross_weight', 'N/A')}"))
            
            status = "Idle"
            if weighbridge['id'] in weighbridge_module.active_weighings:
                status = "In Progress"
            self.realtime_table.setItem(row, 4, QTableWidgetItem(status))

    @Slot(int, float)
    def update_current_weight(self, weighbridge_id: int, weight: float):
        """
        Update the current weight for a specific weighbridge in the real-time table.
        """
        for row in range(self.realtime_table.rowCount()):
            if self.realtime_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == weighbridge_id:
                self.realtime_table.setItem(row, 1, QTableWidgetItem(f"{weight:.2f}"))
                break

    def start_new_weighing(self):
        """
        Initiate a new weighing process.
        """
        try:
            if not weighbridge_module.connection:
                raise ConnectionError("No active database connection. Please reconnect to the database.")

            weighbridges = weighbridge_module.weighbridges
            drivers = weighbridge_module.get_drivers()
            available_orders = weighbridge_module.get_pending_orders()

            logger.info(f"Fetched {len(weighbridges)} weighbridges")
            logger.info(f"Fetched {len(drivers)} drivers")
            logger.info(f"Fetched {len(available_orders)} available orders")

            if not available_orders:
                raise ValueError("There are no orders available for weighing.")

            dialog = StartWeighingDialog(self)
            dialog.populate_data(weighbridges, drivers, available_orders)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                logger.info(f"Starting new weighing with data: {data}")
                weighbridge_module.start_new_weighing(**data)
                self.show_success_message("Started weighing process successfully.")
        except (ConnectionError, ValueError) as e:
            self.show_error_message(f"An error occurred: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in start_new_weighing UI operation: {e}")
            self.show_error_message(f"An unexpected error occurred. Please check the logs for more details.")

    def set_tare_weight(self):
        """
        Set the tare weight for the selected weighbridge.
        """
        try:
            selected_row = self.realtime_table.currentRow()
            if selected_row < 0:
                raise ValueError("Please select a weighbridge to set tare weight.")

            weighbridge_id = self.realtime_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            if weighbridge_id is None:
                weighbridge_id = int(self.realtime_table.item(selected_row, 0).text().split()[0])
            
            weighbridge_module.set_tare_weight(weighbridge_id)
            self.show_success_message("Tare weight set successfully.")
        except ValueError as e:
            self.show_error_message(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error setting tare weight: {str(e)}")
            self.show_error_message("An unexpected error occurred. Please check the logs for more details.")

    def set_gross_weight(self):
        """
        Set the gross weight for the selected weighbridge.
        """
        try:
            selected_row = self.realtime_table.currentRow()
            if selected_row < 0:
                raise ValueError("Please select a weighbridge to set gross weight.")

            weighbridge_id = self.realtime_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            weighbridge_module.set_gross_weight(weighbridge_id)
            self.show_success_message("Gross weight set and weighing completed successfully.")
        except ValueError as e:
            self.show_error_message(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error setting gross weight: {str(e)}")
            self.show_error_message("An unexpected error occurred. Please check the logs for more details.")

    def cancel_weighing(self):
        """
        Cancel the active weighing process for the selected weighbridge.
        """
        try:
            selected_row = self.realtime_table.currentRow()
            if selected_row < 0:
                raise ValueError("Please select a weighbridge to cancel weighing.")

            weighbridge_id = self.realtime_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            weighbridge_module.cancel_weighing(weighbridge_id)
            self.show_success_message("The weighing process has been cancelled.")
        except ValueError as e:
            self.show_error_message(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error cancelling weighing: {str(e)}")
            self.show_error_message("An unexpected error occurred. Please check the logs for more details.")

    def fetch_weighing_records(self):
        """
        Fetch and display historical weighing records.
        """
        start_date = self.start_date.date()
        end_date = self.end_date.date()
        product_filter = self.product_filter.text()
        weighbridge_filter = self.weighbridge_filter.text()

        try:
            weighing_records = weighbridge_module.get_weighing_records(
                start_date=start_date,
                end_date=end_date,
                product_filter=product_filter,
                weighbridge_filter=weighbridge_filter
            )

            self.historical_table.setRowCount(len(weighing_records))
            for row, record in enumerate(weighing_records):
                self.historical_table.setItem(row, 0, QTableWidgetItem(str(record['LoadingDate'])))
                self.historical_table.setItem(row, 1, QTableWidgetItem(str(record['LoadingTime'])))
                self.historical_table.setItem(row, 2, QTableWidgetItem(record['WeighbridgeName']))
                self.historical_table.setItem(row, 3, QTableWidgetItem(record['DriverName']))
                self.historical_table.setItem(row, 4, QTableWidgetItem(record['LicensePlateNumber']))
                self.historical_table.setItem(row, 5, QTableWidgetItem(record['ProductName']))
                
                initial_weight = record['InitialWeight']
                self.historical_table.setItem(row, 6, QTableWidgetItem(f"{initial_weight:.2f}" if initial_weight is not None else "N/A"))
                
                final_weight = record['FinalWeight']
                self.historical_table.setItem(row, 7, QTableWidgetItem(f"{final_weight:.2f}" if final_weight is not None else "N/A"))
                
                checkout_weight = record['CheckoutWeight']
                self.historical_table.setItem(row, 8, QTableWidgetItem(f"{checkout_weight:.2f}" if checkout_weight is not None else "N/A"))
                
                self.historical_table.setItem(row, 9, QTableWidgetItem(record['Status']))

                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                view_button = StyledPushButton("View", "info")
                view_button.clicked.connect(lambda _, order_id=record['OrderId']: self.view_weighing_details(order_id))
                action_layout.addWidget(view_button)
                self.historical_table.setCellWidget(row, 10, action_widget)

            logger.info(f"Populated historical table with {len(weighing_records)} records")
            self.show_success_message(f"Successfully loaded {len(weighing_records)} weighing records.")
        except Exception as e:
            logger.error(f"Error fetching weighing records: {str(e)}")
            self.show_error_message(f"Failed to fetch weighing records: {str(e)}")

    def view_weighing_details(self, order_id):
        """
        Display detailed information for a specific weighing record.
        """
        try:
            details = weighbridge_module.get_weighing_details(order_id)
            if details:
                message = f"Weighing Details:\n\n"
                for key, value in details.items():
                    message += f"{key}: {value}\n"
                self.show_info_message("Weighing Details", message)
            else:
                raise ValueError("No details found for the selected weighing record.")
        except ValueError as e:
            self.show_error_message(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error viewing weighing details: {str(e)}")
            self.show_error_message(f"Failed to fetch weighing details: {str(e)}")

class StartWeighingDialog(QDialog):
    """
    Dialog for starting a new weighing process.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start New Weighing")
        self.init_ui()
        apply_styles(self, recursive=True)

    def init_ui(self):
        """
        Initialize the dialog's user interface.
        """
        layout = QFormLayout(self)

        self.weighbridge_combo = QComboBox()
        self.order_combo = QComboBox()
        self.driver_combo = QComboBox()
        self.vehicle_combo = QComboBox()

        apply_styles(self.weighbridge_combo)
        apply_styles(self.order_combo)
        apply_styles(self.driver_combo)
        apply_styles(self.vehicle_combo)

        layout.addRow("Weighbridge:", self.weighbridge_combo)
        layout.addRow("Order:", self.order_combo)
        layout.addRow("Driver:", self.driver_combo)
        layout.addRow("Vehicle License:", self.vehicle_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        apply_styles(button_box)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

        self.driver_combo.currentIndexChanged.connect(self.update_vehicle_combo)

    def validate_and_accept(self):
        """
        Validate the input and accept the dialog if all fields are filled.
        """
        if (self.weighbridge_combo.currentData() and
            self.order_combo.currentData() and
            self.driver_combo.currentData() and
            self.vehicle_combo.currentText()):
            self.accept()
        else:
            QMessageBox.warning(self, "Input Error", "Please select all required fields.")

    def populate_data(self, weighbridges, drivers, orders):
        """
        Populate the dialog with available data.
        """
        logger.info("Populating data in StartWeighingDialog")
        logger.info(f"Received {len(weighbridges)} weighbridges, {len(drivers)} drivers, and {len(orders)} orders")

        self.weighbridge_combo.clear()
        self.order_combo.clear()
        self.driver_combo.clear()

        for wb in weighbridges:
            self.weighbridge_combo.addItem(wb['name'], wb['id'])
        
        self.order_combo.addItem("Select Order", None)
        for order in orders:
            order_text = f"Order {order['OrderId']} - {order['ProductName']} ({order['PlannedQuantity']})"
            self.order_combo.addItem(order_text, order['OrderId'])
            logger.info(f"Added order to combo: {order_text}")

        self.drivers = drivers
        self.driver_combo.addItem("Select Driver", None)
        for driver in drivers:
            self.driver_combo.addItem(driver['DriverName'], driver['DriverId'])

        logger.info(f"Populated {self.weighbridge_combo.count()} weighbridges, {self.order_combo.count()} orders, and {self.driver_combo.count()} drivers")

    def update_vehicle_combo(self, index):
        """
        Update the vehicle combo box based on the selected driver.
        """
        self.vehicle_combo.clear()
        if index > 0:
            driver = self.drivers[index - 1]  # -1 because of "Select Driver" item
            self.vehicle_combo.addItem(driver['LicensePlateNumber'], driver['LicensePlateNumber'])

    def get_data(self):
        """
        Get the selected data from the dialog.
        """
        return {
            'weighbridge_id': self.weighbridge_combo.currentData(),
            'order_id': self.order_combo.currentData(),
            'driver_id': self.driver_combo.currentData(),
            'vehicle_license': self.vehicle_combo.currentText()
        }
