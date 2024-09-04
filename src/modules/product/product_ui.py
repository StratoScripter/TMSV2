from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
                               QHeaderView, QAbstractItemView, QComboBox)
from PySide6.QtCore import Qt
from .product import product_module
from ui.ui_styles import apply_styles, Styles, TMSWidget, StyledPushButton
from .server import server_module
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ProductWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.init_ui()
        product_module.data_updated.connect(self.refresh_table)
        product_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)

    def show_error_message(self, message: str):
        logger.error(message)
        # Here you might want to update some UI element to show the error, instead of a message box

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Products...")
        self.search_input.setStyleSheet(Styles.line_edit())
        
        self.search_button = StyledPushButton("Search", "search")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = StyledPushButton("Add Product", "add")
        self.edit_button = StyledPushButton("Edit Product", "edit")
        self.delete_button = StyledPushButton("Delete Product", "delete")
        self.refresh_button = StyledPushButton("Refresh", "search")

        for button in [self.add_button, self.edit_button, self.delete_button, self.refresh_button]:
            button_layout.addWidget(button)

        layout.addLayout(button_layout)

        # Table
        self.table = QTableWidget()
        self.table.setStyleSheet(Styles.table_widget())
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.table)

        # Connect signals
        self.search_button.clicked.connect(self.search_products)
        self.add_button.clicked.connect(self.add_product)
        self.edit_button.clicked.connect(self.edit_product)
        self.delete_button.clicked.connect(self.delete_product)
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
        if isinstance(product_module.products, list):
            self.table.setRowCount(len(product_module.products))
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "Product Code", "Product Name", "Description", "Density", "State",
                "Current Reserve", "Unit", "Storage Tank Name"
            ])

            for row, product in enumerate(product_module.products):
                self.table.setItem(row, 0, QTableWidgetItem(str(product.get('ProductCode', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(str(product.get('ProductName', ''))))
                self.table.setItem(row, 2, QTableWidgetItem(str(product.get('Description', ''))))
                self.table.setItem(row, 3, QTableWidgetItem(str(product.get('Density', ''))))
                self.table.setItem(row, 4, QTableWidgetItem(str(product.get('State', ''))))
                self.table.setItem(row, 5, QTableWidgetItem(str(product.get('CurrentReserve', ''))))
                self.table.setItem(row, 6, QTableWidgetItem(str(product.get('UnitName', ''))))
                self.table.setItem(row, 7, QTableWidgetItem(str(product.get('StorageTankName', ''))))

            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.table.horizontalHeader().setStyleSheet(Styles.header_view())
            self.table.verticalHeader().setStyleSheet(Styles.header_view())
        else:
            logger.error(f"Unexpected type for product_module.products: {type(product_module.products)}")

    def search_products(self):
        if not self.is_connected:
            return
        search_term = self.search_input.text()
        product_module.search_products(search_term)

    def add_product(self):
        if not self.is_connected:
            return
        dialog = ProductDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if product_module.add_product(data):
                logger.info("Product added successfully.")
                product_module.fetch_products()
            else:
                logger.error("Failed to add product.")

    def edit_product(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(product_module.products, list) and 0 <= selected_row < len(product_module.products):
            product = product_module.products[selected_row]
            dialog = ProductDialog(self, product.get('ProductId'))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if product_module.update_product(data):
                    logger.info("Product updated successfully.")
                    product_module.fetch_products()
                else:
                    logger.error("Failed to update product.")
        else:
            logger.warning("No product selected for editing.")

    def delete_product(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(product_module.products, list) and 0 <= selected_row < len(product_module.products):
            product = product_module.products[selected_row]
            product_id = product.get('ProductId')
            if product_id:
                if product_module.delete_product(product_id):
                    logger.info(f"Product {product.get('ProductName', '')} deleted successfully.")
                    product_module.fetch_products()
                else:
                    logger.error(f"Failed to delete product {product.get('ProductName', '')}.")
            else:
                logger.error("Invalid product ID for deletion.")
        else:
            logger.warning("No product selected for deletion.")


class ProductDialog(QDialog):
    def __init__(self, parent=None, product_id: Optional[str] = None):
        super().__init__(parent)
        self.product_id = product_id
        self.setWindowTitle("Add Product" if product_id is None else "Edit Product")
        self.setStyleSheet(Styles.dialog())
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.code_input = QLineEdit()
        self.name_input = QLineEdit()
        self.description_input = QLineEdit()
        self.density_input = QDoubleSpinBox()
        self.state_input = QLineEdit()
        self.current_reserve_input = QDoubleSpinBox()
        self.unit_combo = QComboBox()
        self.storage_tank_combo = QComboBox()

        for widget in [self.code_input, self.name_input, self.description_input, self.state_input]:
            widget.setStyleSheet(Styles.line_edit())

        for spinbox in [self.density_input, self.current_reserve_input]:
            spinbox.setStyleSheet(Styles.spin_box())
            spinbox.setRange(0, 1000000)
            spinbox.setDecimals(2)

        for combo in [self.unit_combo, self.storage_tank_combo]:
            combo.setStyleSheet(Styles.combo_box())

        layout.addRow("Product Code:", self.code_input)
        layout.addRow("Product Name:", self.name_input)
        layout.addRow("Description:", self.description_input)
        layout.addRow("Density:", self.density_input)
        layout.addRow("State:", self.state_input)
        layout.addRow("Current Reserve:", self.current_reserve_input)
        layout.addRow("Unit:", self.unit_combo)
        layout.addRow("Storage Tank:", self.storage_tank_combo)

        buttons = QHBoxLayout()
        self.save_button = StyledPushButton("Save")
        self.cancel_button = StyledPushButton("Cancel")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        layout.addRow(buttons)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.populate_units()
        self.populate_storage_tanks()
        if self.product_id:
            self.populate_data()

    def populate_units(self):
        units = product_module.get_units()
        self.unit_combo.clear()
        if units:
            for unit in units:
                self.unit_combo.addItem(unit.get('UnitName', ''), unit.get('UnitId'))
        else:
            self.unit_combo.addItem("No units available", None)

    def populate_storage_tanks(self):
        storage_tanks = product_module.get_storage_tanks()
        self.storage_tank_combo.clear()
        self.storage_tank_combo.addItem("No Storage Tank", None)
        if storage_tanks:
            for tank in storage_tanks:
                status = "Assigned" if tank.get('ProductId') else "Unassigned"
                self.storage_tank_combo.addItem(f"{tank.get('StorageTankName', '')} ({status})", tank.get('StorageTankId'))

    def populate_data(self):
        details = product_module.get_product_details(self.product_id)
        if details and isinstance(details, dict):
            self.code_input.setText(str(details.get('ProductCode', '')))
            self.name_input.setText(str(details.get('ProductName', '')))
            self.description_input.setText(str(details.get('Description', '')))
            self.density_input.setValue(float(details.get('Density', 0)))
            self.state_input.setText(str(details.get('State', '')))
            self.current_reserve_input.setValue(float(details.get('CurrentReserve', 0)))
            self.set_combo_value(self.unit_combo, details.get('UnitId'))
            self.set_combo_value(self.storage_tank_combo, details.get('StorageTankId'))
        else:
            logger.error(f"Invalid product details: {details}")

    def set_combo_value(self, combo: QComboBox, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def get_data(self) -> Dict[str, Any]:
        return {
            'ProductId': self.product_id,
            'ProductCode': self.code_input.text(),
            'ProductName': self.name_input.text(),
            'Description': self.description_input.text(),
            'Density': self.density_input.value(),
            'State': self.state_input.text(),
            'CurrentReserve': self.current_reserve_input.value(),
            'UnitId': self.unit_combo.currentData(),
            'StorageTankId': self.storage_tank_combo.currentData(),
        }