from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QTextEdit,
                               QHeaderView, QAbstractItemView, QComboBox, QLabel)
from PySide6.QtCore import Qt
from .party import party_module
from ui.ui_styles import apply_styles, Styles, TMSWidget
from modules.product.server import server_module
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PartyWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.all_parties = []  # Store all parties
        apply_styles(self)
        self.init_ui()
        party_module.data_updated.connect(self.refresh_table)
        party_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)

    def show_error_message(self, message: str):
        logger.error(message)
        # Here you might want to update some UI element to show the error, instead of a message box

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Parties...")
        
        self.search_button = QPushButton("Search")
        
        self.role_filter = QComboBox()
        self.role_filter.addItems(["All", "Buyer", "Seller", "Both"])
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(QLabel("Role:"))
        search_layout.addWidget(self.role_filter)
        layout.addLayout(search_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Party")
        self.edit_button = QPushButton("Edit Party")
        self.delete_button = QPushButton("Delete Party")
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
        self.search_button.clicked.connect(self.search_parties)
        self.add_button.clicked.connect(self.add_party)
        self.edit_button.clicked.connect(self.edit_party)
        self.delete_button.clicked.connect(self.delete_party)
        self.refresh_button.clicked.connect(self.refresh_table)
        self.role_filter.currentIndexChanged.connect(self.filter_parties)

        self.update_ui_elements()

    def set_connection_status(self, is_connected: bool, message: str):
        self.is_connected = is_connected
        self.update_ui_elements()
        if is_connected:
            self.refresh_table()
        else:
            self.table.setRowCount(0)

    def update_ui_elements(self):
        enabled = self.is_connected
        for widget in [self.add_button, self.edit_button, self.delete_button, 
                       self.refresh_button, self.search_button, self.search_input, self.role_filter]:
            widget.setEnabled(enabled)

    def refresh_table(self):
        if not self.is_connected:
            return

        self.all_parties = party_module.fetch_parties()
        self.filter_and_display_parties()

    def get_role_name(self, role_id):
        roles = {1: "Buyer", 2: "Seller", 3: "Both"}
        return roles.get(role_id, "Unknown")

    def search_parties(self):
        if not self.is_connected:
            return
        search_term = self.search_input.text()
        searched_parties = party_module.search_parties(search_term)
        self.display_parties(searched_parties if searched_parties is not None else [])

    def display_parties(self, parties):
        self.table.setRowCount(len(parties))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Party ID", "Party Name", "Contact Person", "Contact Number", "Email", "Address", "Created Date", "Role"
        ])

        for row, party in enumerate(parties):
            self.table.setItem(row, 0, QTableWidgetItem(str(party.get('PartyId', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(party.get('PartyName', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(party.get('ContactPerson', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(party.get('ContactNumber', ''))))
            self.table.setItem(row, 4, QTableWidgetItem(str(party.get('Email', ''))))
            self.table.setItem(row, 5, QTableWidgetItem(str(party.get('Address', ''))))
            self.table.setItem(row, 6, QTableWidgetItem(str(party.get('CreatedDate', ''))))
            self.table.setItem(row, 7, QTableWidgetItem(self.get_role_name(party.get('PartyRoleId', 0))))

        self.table.resizeColumnsToContents()
        # Use ResizeToContents instead of Stretch
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


    def add_party(self):
        if not self.is_connected:
            return
        dialog = PartyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if party_module.add_party(data):
                logger.info("Party added successfully.")
                party_module.fetch_parties()
            else:
                logger.error("Failed to add party.")

    def edit_party(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(party_module.parties, list) and 0 <= selected_row < len(party_module.parties):
            party = party_module.parties[selected_row]
            dialog = PartyDialog(self, party.get('PartyId'))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if party_module.update_party(data):
                    logger.info("Party updated successfully.")
                    party_module.fetch_parties()
                else:
                    logger.error("Failed to update party.")
        else:
            logger.warning("No party selected for editing.")

    def delete_party(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(party_module.parties, list) and 0 <= selected_row < len(party_module.parties):
            party = party_module.parties[selected_row]
            party_id = party.get('PartyId')
            if party_id:
                if party_module.delete_party(party_id):
                    logger.info(f"Party {party.get('PartyName', '')} deleted successfully.")
                    party_module.fetch_parties()
                else:
                    logger.error(f"Failed to delete party {party.get('PartyName', '')}.")
            else:
                logger.error("Invalid party ID for deletion.")
        else:
            logger.warning("No party selected for deletion.")

    def filter_parties(self):
        self.filter_and_display_parties()

    def get_selected_role_id(self):
        role_text = self.role_filter.currentText()
        if role_text == "All":
            return None
        elif role_text == "Buyer":
            return 1
        elif role_text == "Seller":
            return 2
        elif role_text == "Both":
            return 3
        else:
            return None

    def filter_and_display_parties(self):
        role_id = self.get_selected_role_id()
        filtered_parties = self.all_parties
        if role_id is not None:
            filtered_parties = [party for party in self.all_parties if party.get('PartyRoleId') == role_id]
        self.display_parties(filtered_parties)

class PartyDialog(QDialog):
    def __init__(self, parent=None, party_id: Optional[int] = None):
        super().__init__(parent)
        self.party_id = party_id
        self.setWindowTitle("Add Party" if party_id is None else "Edit Party")
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.contact_person_input = QLineEdit()
        self.contact_number_input = QLineEdit()
        self.email_input = QLineEdit()
        self.address_input = QTextEdit()
        self.role_combo = QComboBox()

        

        

        layout.addRow("Party Name:", self.name_input)
        layout.addRow("Contact Person:", self.contact_person_input)
        layout.addRow("Contact Number:", self.contact_number_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Address:", self.address_input)
        layout.addRow("Role:", self.role_combo)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)

        

        layout.addRow(buttons)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.populate_roles()
        if self.party_id:
            self.populate_data()

    def populate_roles(self):
        self.role_combo.addItems(["Buyer", "Seller", "Both"])

    def populate_data(self):
        if self.party_id is not None:
            party_data = party_module.get_party(self.party_id)
            if party_data:
                self.name_input.setText(party_data.get('PartyName', ''))
                self.contact_person_input.setText(party_data.get('ContactPerson', ''))
                self.contact_number_input.setText(party_data.get('ContactNumber', ''))
                self.email_input.setText(party_data.get('Email', ''))
                self.address_input.setPlainText(party_data.get('Address', ''))
                self.role_combo.setCurrentIndex(party_data.get('PartyRoleId', 1) - 1)
            else:
                logger.error(f"Invalid party data for ID: {self.party_id}")
        else:
            logger.warning("No party ID provided for editing")

    def get_data(self) -> Dict[str, Any]:
        return {
            'PartyId': self.party_id,
            'PartyName': self.name_input.text(),
            'ContactPerson': self.contact_person_input.text(),
            'ContactNumber': self.contact_number_input.text(),
            'Email': self.email_input.text(),
            'Address': self.address_input.toPlainText(),
            'PartyRoleId': self.role_combo.currentIndex() + 1,
        }