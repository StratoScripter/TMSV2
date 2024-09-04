# weighbridge_ui.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QDateEdit,
                               QMessageBox, QSizePolicy, QDialog, QFormLayout, QComboBox, 
                               QDialogButtonBox, QTabWidget)
from PySide6.QtCore import Qt, Slot, QDate
from ui.ui_styles import Styles, apply_styles, TMSWidget, StyledPushButton, apply_table_styles, set_layout_properties
from .weighbridge import weighbridge_module
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeighbridgeWidget(TMSWidget):
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
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.tab_widget)

        # Real-time tab
        self.realtime_tab = QWidget()
        self.init_realtime_tab()
        self.tab_widget.addTab(self.realtime_tab, "Real-time View")

        # Historical tab
        self.historical_tab = QWidget()
        self.init_historical_tab()
        self.tab_widget.addTab(self.historical_tab, "Historical Data")

        apply_styles(self)

    def init_realtime_tab(self):
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

        # Weighing process buttons
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

        # Connect buttons
        self.start_weighing_button.clicked.connect(self.start_new_weighing)
        self.set_tare_button.clicked.connect(self.set_tare_weight)
        self.set_gross_button.clicked.connect(self.set_gross_weight)
        self.cancel_weighing_button.clicked.connect(self.cancel_weighing)

    def init_historical_tab(self):
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

        # Connect signals
        self.filter_button.clicked.connect(self.fetch_weighing_records)

    def fetch_weighing_records(self):
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

                # Actions
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                view_button = StyledPushButton("View", "info")
                view_button.clicked.connect(lambda _, order_id=record['OrderId']: self.view_weighing_details(order_id))
                action_layout.addWidget(view_button)
                self.historical_table.setCellWidget(row, 10, action_widget)

            logger.info(f"Populated historical table with {len(weighing_records)} records")
        except Exception as e:
            logger.error(f"Error fetching weighing records: {str(e)}")
            msg_box = QMessageBox()
            apply_styles(msg_box)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setText(f"Failed to fetch weighing records: {str(e)}")
            msg_box.setWindowTitle("Error")
            msg_box.exec()

    def view_weighing_details(self, order_id):
        details = weighbridge_module.get_weighing_details(order_id)
        if details:
            message = f"Weighing Details:\n\n"
            for key, value in details.items():
                message += f"{key}: {value}\n"
            msg_box = QMessageBox()
            apply_styles(msg_box)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(message)
            msg_box.setWindowTitle("Weighing Details")
            msg_box.exec()
        else:
            msg_box = QMessageBox()
            apply_styles(msg_box)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("Failed to fetch weighing details.")
            msg_box.setWindowTitle("Error")
            msg_box.exec()

    def show_error_message(self, message):
        msg_box = QMessageBox()
        apply_styles(msg_box)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("Error")
        msg_box.exec()

    @Slot(list)
    def update_realtime_data(self, data):
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

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            view_button = StyledPushButton("View", "info")
            view_button.clicked.connect(lambda _, wb_id=weighbridge.get('id'): self.view_weighbridge_details(wb_id))
            action_layout.addWidget(view_button)
            self.realtime_table.setCellWidget(row, 5, action_widget)

    @Slot(int, float)
    def update_current_weight(self, weighbridge_id: int, weight: float):
        for row in range(self.realtime_table.rowCount()):
            if self.realtime_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == weighbridge_id:
                self.realtime_table.setItem(row, 1, QTableWidgetItem(f"{weight:.2f}"))
                break

    def start_new_weighing(self):
        try:
            if not weighbridge_module.connection:
                msg_box = QMessageBox()
                apply_styles(msg_box)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("No active database connection. Please reconnect to the database.")
                msg_box.setWindowTitle("Error")
                msg_box.exec()
                return

            weighbridges = weighbridge_module.weighbridges
            drivers = weighbridge_module.get_drivers()
            available_orders = weighbridge_module.get_pending_orders()

            logger.info(f"Fetched {len(weighbridges)} weighbridges")
            logger.info(f"Fetched {len(drivers)} drivers")
            logger.info(f"Fetched {len(available_orders)} available orders")

            if not available_orders:
                msg_box = QMessageBox()
                apply_styles(msg_box)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("There are no orders available for weighing.")
                msg_box.setWindowTitle("No Available Orders")
                msg_box.exec()
                return

            dialog = StartWeighingDialog(self)
            dialog.populate_data(weighbridges, drivers, available_orders)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                logger.info(f"Starting new weighing with data: {data}")
                if weighbridge_module.start_new_weighing(**data):
                    msg_box = QMessageBox()
                    apply_styles(msg_box)
                    msg_box.setIcon(QMessageBox.Icon.Information)
                    msg_box.setText("Started weighing process successfully.")
                    msg_box.setWindowTitle("New Weighing")
                    msg_box.exec()
                else:
                    msg_box = QMessageBox()
                    apply_styles(msg_box)
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText("Failed to start weighing process. Please check the logs for more details.")
                    msg_box.setWindowTitle("Error")
                    msg_box.exec()
        except Exception as e:
            logger.error(f"Error in start_new_weighing UI operation: {e}")
            msg_box = QMessageBox()
            apply_styles(msg_box)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setText(f"An unexpected error occurred: {str(e)}")
            msg_box.setWindowTitle("Error")
            msg_box.exec()

    def set_tare_weight(self):
        selected_row = self.realtime_table.currentRow()
        if selected_row >= 0:
            weighbridge_id = self.realtime_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            if weighbridge_id is None:
                weighbridge_id = int(self.realtime_table.item(selected_row, 0).text().split()[0])  # Assuming the ID is the first part of the name
            
            if weighbridge_id in weighbridge_module.active_weighings:
                if weighbridge_module.set_tare_weight(weighbridge_id):
                    QMessageBox.information(self, "Tare Weight Set", "Tare weight set successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to set tare weight.")
            else:
                QMessageBox.warning(self, "No Active Weighing", f"No active weighing for weighbridge {weighbridge_id}. Please start a new weighing first.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a weighbridge to set tare weight.")

    def set_gross_weight(self):
        selected_row = self.realtime_table.currentRow()
        if selected_row >= 0:
            weighbridge_id = self.realtime_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            if weighbridge_module.set_gross_weight(weighbridge_id):
                QMessageBox.information(self, "Gross Weight Set", "Gross weight set and weighing completed successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to set gross weight.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a weighbridge to set gross weight.")

    def cancel_weighing(self):
        selected_row = self.realtime_table.currentRow()
        if selected_row >= 0:
            weighbridge_id = self.realtime_table.item(selected_row, 0).data(Qt.ItemDataRole.UserRole)
            if weighbridge_module.cancel_weighing(weighbridge_id):
                QMessageBox.information(self, "Weighing Cancelled", "The weighing process has been cancelled.")
            else:
                QMessageBox.warning(self, "Error", "Failed to cancel the weighing process.")
        else:
            QMessageBox.warning(self, "No Selection", "Please select a weighbridge to cancel weighing.")

    def view_weighbridge_details(self, weighbridge_id):
        details = weighbridge_module.get_weighbridge_details(weighbridge_id)
        if details:
            message = f"Weighbridge Details:\n\n"
            for key, value in details.items():
                message += f"{key}: {value}\n"
            QMessageBox.information(self, "Weighbridge Details", message)
        else:
            QMessageBox.warning(self, "Error", "Failed to fetch weighbridge details.")


class StartWeighingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start New Weighing")
        self.init_ui()
        apply_styles(self, recursive=True)

    def init_ui(self):
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
        if (self.weighbridge_combo.currentData() and
            self.order_combo.currentData() and
            self.driver_combo.currentData() and
            self.vehicle_combo.currentText()):
            self.accept()
        else:
            msg_box = QMessageBox()
            apply_styles(msg_box)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("Please select all required fields.")
            msg_box.setWindowTitle("Error")
            msg_box.exec()

    def populate_data(self, weighbridges, drivers, orders):
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
        self.vehicle_combo.clear()
        if index > 0:
            driver = self.drivers[index - 1]  # -1 because of "Select Driver" item
            self.vehicle_combo.addItem(driver['LicensePlateNumber'], driver['LicensePlateNumber'])

    def get_data(self):
        return {
            'weighbridge_id': self.weighbridge_combo.currentData(),
            'order_id': self.order_combo.currentData(),
            'driver_id': self.driver_combo.currentData(),
            'vehicle_license': self.vehicle_combo.currentText()
        }

