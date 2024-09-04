# icperm_ui.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QHeaderView,
                             QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QDialog,
                             QFormLayout, QComboBox, QFrame, QScrollArea)
from PySide6.QtCore import Qt
from .icperm import ICPermModule
from modules.base_table_widget import BaseTableWidget
from ui.ui_styles import apply_styles
from modules.logger_config import get_logger

logger = get_logger('icperm_ui')
db_activity_logger = get_logger('db_activity')

class ICPermWidget(BaseTableWidget):
    def __init__(self, main_window, server_module):
        super().__init__(main_window)
        self.server_module = server_module
        self.icperm_module = None
        apply_styles(self, 'tankcar')
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

        self.driver_table = QTableWidget()
        self.create_driver_table()
        self.add_table(self.driver_table)
        scroll_layout.addWidget(self.driver_table)

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
        
        self.add_button = QPushButton("Add")
        self.modify_button = QPushButton("Modify")
        self.delete_button = QPushButton("Delete")
        self.search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")

        bar_layout.addWidget(self.add_button)
        bar_layout.addWidget(self.modify_button)
        bar_layout.addWidget(self.delete_button)
        bar_layout.addWidget(self.search_label)
        bar_layout.addWidget(self.search_input)
        bar_layout.addWidget(self.search_button)
        bar_layout.addStretch(1)

        self.add_button.clicked.connect(self.add_driver)
        self.modify_button.clicked.connect(self.modify_driver)
        self.delete_button.clicked.connect(self.delete_driver)
        self.search_button.clicked.connect(self.search_drivers)
        self.search_input.returnPressed.connect(self.search_drivers)

    def create_driver_table(self):
        self.driver_table.setColumnCount(5)
        self.driver_table.setHorizontalHeaderLabels([
            "Driver ID", "Driver Name", "License Number", "Contact Number", "Modified Date"
        ])
        self.driver_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.driver_table.verticalHeader().setVisible(False)
        self.driver_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.driver_table.setSelectionMode(QTableWidget.SingleSelection)
        self.driver_table.cellClicked.connect(self.driver_selected)
        self.driver_table.cellDoubleClicked.connect(self.modify_driver)

    def update_server_list(self, server_list):
        self.server_combo.clear()
        self.server_combo.addItem("Select a server", None)
        for server in server_list:
            self.server_combo.addItem(server.name, server)
    
    def on_server_changed(self, index):
        server_info = self.server_combo.itemData(index)
        if server_info:
            try:
                self.icperm_module = ICPermModule(self.server_module)
                self.icperm_module.initialize(server_info)
                self.load_all_drivers()
            except ConnectionError as e:
                QMessageBox.critical(self, "Connection Error", str(e))
                self.driver_table.setRowCount(0)
        else:
            self.icperm_module = None
            self.driver_table.setRowCount(0)

    def load_all_drivers(self):
        if self.icperm_module:
            try:
                drivers = self.icperm_module.get_all_drivers()
                self.populate_driver_table(drivers)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load drivers: {str(e)}")
        else:
            QMessageBox.warning(self, "No Server Selected", "Please select a server first.")


    def populate_driver_table(self, drivers):
        self.driver_table.setRowCount(len(drivers))
        for row, driver in enumerate(drivers):
            self.driver_table.setItem(row, 0, QTableWidgetItem(str(driver['DriverId'])))
            self.driver_table.setItem(row, 1, QTableWidgetItem(driver['DriverName']))
            self.driver_table.setItem(row, 2, QTableWidgetItem(driver['LicenseNumber']))
            self.driver_table.setItem(row, 3, QTableWidgetItem(driver['ContactNumber']))
            self.driver_table.setItem(row, 4, QTableWidgetItem(str(driver['ModifiedDate'])))

        self.driver_table.resizeRowsToContents()
        self.modify_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def driver_selected(self, row, column):
        self.modify_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def add_driver(self):
        if not self.icperm_module:
            QMessageBox.warning(self, "No Server Selected", "Please select a server first.")
            return
        dialog = DriverEditDialog(self, icperm_module=self.icperm_module)
        if dialog.exec() == QDialog.Accepted:
            self.load_all_drivers()

    def modify_driver(self):
        if not self.icperm_module:
            QMessageBox.warning(self, "No Server Selected", "Please select a server first.")
            return
        selected_rows = self.driver_table.selectionModel().selectedRows()
        if len(selected_rows) == 1:
            driver_id = self.driver_table.item(selected_rows[0].row(), 0).text()
            dialog = DriverEditDialog(self, driver_id=driver_id, icperm_module=self.icperm_module)
            if dialog.exec() == QDialog.Accepted:
                self.load_all_drivers()
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a single row to edit.")

    def delete_driver(self):
        if not self.icperm_module:
            QMessageBox.warning(self, "No Server Selected", "Please select a server first.")
            return
        selected_rows = self.driver_table.selectionModel().selectedRows()
        if len(selected_rows) == 1:
            driver_id = self.driver_table.item(selected_rows[0].row(), 0).text()
            confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this driver?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if self.icperm_module.delete_driver(driver_id):
                    self.load_all_drivers()
                else:
                    QMessageBox.warning(self, "Deletion Error", "Failed to delete the driver.")
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a single row to delete.")

    def search_drivers(self):
        if not self.icperm_module:
            QMessageBox.warning(self, "No Server Selected", "Please select a server first.")
            return
        search_term = self.search_input.text().strip()
        drivers = self.icperm_module.search_drivers(search_term)
        if drivers:
            self.populate_driver_table(drivers)
        else:
            QMessageBox.information(self, "Search Results", "No drivers found matching the search term.")

class DriverEditDialog(QDialog):
    def __init__(self, parent=None, driver_id=None, icperm_module=None):
        super().__init__(parent)
        apply_styles(self, 'tankcar')
        self.driver_id = driver_id
        self.icperm_module = icperm_module
        self.setWindowTitle("Edit Driver" if driver_id else "Add Driver")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)

        self.driver_name_input = QLineEdit()
        self.license_number_input = QLineEdit()
        self.contact_number_input = QLineEdit()

        for label, widget in [
            ("Driver Name:", self.driver_name_input),
            ("License Number:", self.license_number_input),
            ("Contact Number:", self.contact_number_input)
        ]:
            form_layout.addRow(QLabel(label), widget)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        main_layout.addLayout(button_box)

        save_button.clicked.connect(self.save_driver)
        cancel_button.clicked.connect(self.reject)

        if self.driver_id:
            self.load_data()

    def load_data(self):
        driver_data = self.icperm_module.get_driver(self.driver_id)
        if driver_data:
            self.driver_name_input.setText(driver_data['DriverName'])
            self.license_number_input.setText(driver_data['LicenseNumber'])
            self.contact_number_input.setText(driver_data['ContactNumber'])

    def save_driver(self):
        driver_data = {
            'DriverName': self.driver_name_input.text(),
            'LicenseNumber': self.license_number_input.text(),
            'ContactNumber': self.contact_number_input.text()
        }

        if self.driver_id:
            driver_data['DriverId'] = self.driver_id
            success = self.icperm_module.update_driver(driver_data)
            message = "Updated"
        else:
            success = self.icperm_module.add_driver(driver_data)
            message = "Added"

        if success:
            QMessageBox.information(self, "Success", f"Driver {message} successfully.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", f"Failed to save the driver.")