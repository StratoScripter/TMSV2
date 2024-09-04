from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QHeaderView,
                               QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QDialog, QFrame,
                               QFormLayout, QDoubleSpinBox, QDateEdit, QComboBox, QTextEdit, QScrollArea,
                               QTabWidget, QSplitter, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from .contract import contract_module
from modules.product.server import server_module
from ui.ui_styles import TMSWidget, apply_styles, Styles
import os
import logging

logger = logging.getLogger('contract_ui')

class RibbonButton(QPushButton):
    def __init__(self, text, icon_path, parent=None):
        super().__init__(text, parent)
        self.setIcon(QIcon(os.path.join(os.path.dirname(__file__), '..', 'icons', icon_path)))
        self.setObjectName("ribbonButton")

class ContractWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        apply_styles(self)
        self.init_ui()
        contract_module.data_updated.connect(self.refresh_table)
        contract_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)

    def show_error_message(self, message: str):
        logger.error(message)
        QMessageBox.critical(self, "Error", message)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.create_ribbon()
        main_layout.addWidget(self.ribbon)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        self.create_contract_table()
        content_layout.addWidget(self.contract_table)

        main_layout.addWidget(content_widget)

    def create_ribbon(self):
        self.ribbon = QTabWidget()
        self.ribbon.setObjectName("ribbon")

        home_tab = QWidget()
        home_layout = QHBoxLayout(home_tab)
        home_layout.setContentsMargins(10, 5, 10, 5)
        home_layout.setSpacing(10)

        self.buttons = {
            "add_button": RibbonButton("Add Contract", "add_icon.png"),
            "modify_button": RibbonButton("Modify Contract", "edit_icon.png"),
            "delete_button": RibbonButton("Delete Contract", "delete_icon.png"),
            "refresh_button": RibbonButton("Refresh", "refresh_icon.png"),
        }

        for button in self.buttons.values():
            home_layout.addWidget(button)

        home_layout.addStretch(1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search contracts...")
        self.search_input.setObjectName("searchInput")
        self.search_button = RibbonButton("Search", "search_icon.png")

        home_layout.addWidget(self.search_input)
        home_layout.addWidget(self.search_button)

        self.ribbon.addTab(home_tab, "Home")

        # Connect button signals
        self.buttons["add_button"].clicked.connect(self.add_contract)
        self.buttons["modify_button"].clicked.connect(self.modify_contract)
        self.buttons["delete_button"].clicked.connect(self.delete_contract)
        self.buttons["refresh_button"].clicked.connect(self.refresh_table)
        self.search_button.clicked.connect(self.search_contracts)
        self.search_input.returnPressed.connect(self.search_contracts)

    def create_contract_table(self):
        self.contract_table = QTableWidget()
        self.contract_table.setObjectName("contractTable")
        headers = ["Contract ID", "Seller", "Buyer", "Product", "Planned Quantity",
                   "Unit", "Start Date", "End Date", "Sign Date", "Signer", "Status", "Remarks"]
        self.contract_table.setColumnCount(len(headers))
        self.contract_table.setHorizontalHeaderLabels(headers)
        
        self.contract_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.contract_table.verticalHeader().setVisible(False)
        self.contract_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.contract_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.contract_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.contract_table.cellClicked.connect(self.contract_selected)
        self.contract_table.cellDoubleClicked.connect(self.modify_contract)

        self.contract_table.setAlternatingRowColors(True)
        self.contract_table.setSortingEnabled(True)

    def set_connection_status(self, is_connected: bool, message: str):
        self.is_connected = is_connected
        self.update_ui_elements()
        if is_connected:
            self.refresh_table()
        else:
            self.contract_table.setRowCount(0)

    def update_server_info(self, server):
        # Update any server-specific information if needed
        pass

    def update_ui_elements(self):
        enabled = self.is_connected
        for button in self.buttons.values():
            button.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.search_button.setEnabled(enabled)

    def refresh_table(self):
        if not self.is_connected:
            return

        contracts = contract_module.get_all_contracts()
        self.populate_contract_table(contracts)

    def populate_contract_table(self, contracts):
        self.contract_table.setSortingEnabled(False)
        self.contract_table.setRowCount(len(contracts))
        for row, contract in enumerate(contracts):
            self.contract_table.setItem(row, 0, QTableWidgetItem(str(contract['ContractId'])))
            self.contract_table.setItem(row, 1, QTableWidgetItem(contract['Seller']))
            self.contract_table.setItem(row, 2, QTableWidgetItem(contract['Buyer']))
            self.contract_table.setItem(row, 3, QTableWidgetItem(contract['ProductName']))
            self.contract_table.setItem(row, 4, QTableWidgetItem(str(contract['PlannedQuantity'])))
            self.contract_table.setItem(row, 5, QTableWidgetItem(contract['UnitName']))
            self.contract_table.setItem(row, 6, QTableWidgetItem(str(contract['StartDate'])))
            self.contract_table.setItem(row, 7, QTableWidgetItem(str(contract['EndDate'])))
            self.contract_table.setItem(row, 8, QTableWidgetItem(str(contract['SignDate'])))
            self.contract_table.setItem(row, 9, QTableWidgetItem(contract['Signer']))
            self.contract_table.setItem(row, 10, QTableWidgetItem(contract['Status']))
            self.contract_table.setItem(row, 11, QTableWidgetItem(contract['Remarks']))
        
        self.contract_table.resizeRowsToContents()
        self.update_button_states()
        self.contract_table.setSortingEnabled(True)

    def contract_selected(self, row, column):
        self.update_button_states()

    def update_button_states(self):
        selected = bool(self.contract_table.selectionModel().selectedRows())
        self.buttons["modify_button"].setEnabled(selected and self.is_connected)
        self.buttons["delete_button"].setEnabled(selected and self.is_connected)

    def add_contract(self):
        if not self.is_connected:
            return
        dialog = ContractEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            contract_data = dialog.get_contract_data()
            success, _, message = contract_module.add_contract(contract_data)
            if success:
                self.refresh_table()
                QMessageBox.information(self, "Success", "Contract added successfully.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to add contract: {message}")

    def modify_contract(self):
        if not self.is_connected:
            return
        selected_rows = self.contract_table.selectionModel().selectedRows()
        if len(selected_rows) == 1:
            contract_id = int(self.contract_table.item(selected_rows[0].row(), 0).text())
            dialog = ContractEditDialog(self, contract_id)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                contract_data = dialog.get_contract_data()
                success, message = contract_module.update_contract(contract_data)
                if success:
                    self.refresh_table()
                    QMessageBox.information(self, "Success", "Contract updated successfully.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to update contract: {message}")
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a single row to edit.")

    def delete_contract(self):
        if not self.is_connected:
            return
        selected_rows = self.contract_table.selectionModel().selectedRows()
        if len(selected_rows) == 1:
            contract_id = int(self.contract_table.item(selected_rows[0].row(), 0).text())
            confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this contract?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                if contract_module.delete_contract(contract_id):
                    self.refresh_table()
                    QMessageBox.information(self, "Success", "Contract deleted successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete the contract. Please try again.")
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a single row to delete.")

    def search_contracts(self):
        if not self.is_connected:
            return
        search_term = self.search_input.text().strip()
        contracts = contract_module.search_contracts(search_term)
        self.populate_contract_table(contracts)

class ContractEditDialog(QDialog):
    def __init__(self, parent=None, contract_id=None):
        super().__init__(parent)
        apply_styles(self)
        self.setWindowTitle("Add Contract" if contract_id is None else "Edit Contract")
        self.contract_id = contract_id
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        form_layout = QFormLayout(scroll_widget)
        form_layout.setSpacing(15)

        self.inputs = {
            'seller': QComboBox(),
            'buyer': QComboBox(),
            'product': QComboBox(),
            'planned_quantity': QDoubleSpinBox(),
            'unit': QComboBox(),
            'start_date': QDateEdit(),
            'end_date': QDateEdit(),
            'sign_date': QDateEdit(),
            'signer': QLineEdit(),
            'status': QComboBox(),
            'remarks': QTextEdit()
        }

        self.inputs['planned_quantity'].setRange(0, 1000000)
        self.inputs['status'].addItems(["Active", "Completed", "Cancelled"])

        for label, widget in [
            ("Seller:", self.inputs['seller']),
            ("Buyer:", self.inputs['buyer']),
            ("Product:", self.inputs['product']),
            ("Planned Quantity:", self.inputs['planned_quantity']),
            ("Unit:", self.inputs['unit']),
            ("Start Date:", self.inputs['start_date']),
            ("End Date:", self.inputs['end_date']),
            ("Sign Date:", self.inputs['sign_date']),
            ("Signer:", self.inputs['signer']),
            ("Status:", self.inputs['status']),
            ("Remarks:", self.inputs['remarks'])
        ]:
            form_layout.addRow(QLabel(label), widget)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        main_layout.addLayout(buttons)

        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        self.populate_dropdowns()
        if self.contract_id:
            self.load_contract_data()

    def populate_dropdowns(self):
        parties = contract_module.get_all_parties()
        products = contract_module.get_all_products()
        units = contract_module.get_all_units()

        for party in parties:
            self.inputs['seller'].addItem(party['PartyName'], party['PartyId'])
            self.inputs['buyer'].addItem(party['PartyName'], party['PartyId'])

        for product in products:
            self.inputs['product'].addItem(product['ProductName'], product['ProductId'])

        for unit in units:
            self.inputs['unit'].addItem(unit['UnitName'], unit['UnitId'])

    def load_contract_data(self):
        if self.contract_id is not None:
            contract = contract_module.get_contract(int(self.contract_id))
        else:
            # Handle the case when self.contract_id is None
            # You can raise an exception, return a default value, or perform any other appropriate action.
            # For example:
            raise ValueError("Contract ID is not provided.")
        if contract:
            self.inputs['seller'].setCurrentIndex(self.inputs['seller'].findData(contract['SellerId']))
            self.inputs['buyer'].setCurrentIndex(self.inputs['buyer'].findData(contract['BuyerId']))
            self.inputs['product'].setCurrentIndex(self.inputs['product'].findData(contract['ProductId']))
            self.inputs['planned_quantity'].setValue(contract['PlannedQuantity'])
            self.inputs['unit'].setCurrentIndex(self.inputs['unit'].findData(contract['UnitId']))
            self.inputs['start_date'].setDate(contract['StartDate'])
            self.inputs['end_date'].setDate(contract['EndDate'])
            self.inputs['sign_date'].setDate(contract['SignDate'])
            self.inputs['signer'].setText(contract['Signer'])
            self.inputs['status'].setCurrentText(contract['Status'])
            self.inputs['remarks'].setPlainText(contract['Remarks'])

    def get_contract_data(self):
        return {
            'ContractId': self.contract_id,
            'SellerId': self.inputs['seller'].currentData(),
            'BuyerId': self.inputs['buyer'].currentData(),
            'ProductId': self.inputs['product'].currentData(),
            'PlannedQuantity': self.inputs['planned_quantity'].value(),
            'UnitId': self.inputs['unit'].currentData(),
            'StartDate': self.inputs['start_date'].date().toPython(),
            'EndDate': self.inputs['end_date'].date().toPython(),
            'SignDate': self.inputs['sign_date'].date().toPython(),
            'Signer': self.inputs['signer'].text(),
            'Status': self.inputs['status'].currentText(),
            'Remarks': self.inputs['remarks'].toPlainText()
        }

