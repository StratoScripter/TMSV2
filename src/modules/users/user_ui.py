# user_ui.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QDialog, QFormLayout, QLineEdit,QListWidgetItem,
                               QHeaderView, QAbstractItemView, QComboBox, QCheckBox, QListWidget)
from PySide6.QtCore import Qt
from .user import user_module
from ui.ui_styles import apply_styles, Styles, TMSWidget
from modules.product.server import server_module
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class UserWidget(TMSWidget):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        apply_styles(self)
        self.init_ui()
        user_module.data_updated.connect(self.refresh_table)
        user_module.error_occurred.connect(self.show_error_message)
        server_module.connection_status_changed.connect(self.set_connection_status)

    def show_error_message(self, message: str):
        logger.error(message)
        # Here you might want to update some UI element to show the error, instead of a message box

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Users...")
        self.search_button = QPushButton("Search")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add User")
        self.edit_button = QPushButton("Edit User")
        self.delete_button = QPushButton("Delete User")
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
        self.search_button.clicked.connect(self.search_users)
        self.add_button.clicked.connect(self.add_user)
        self.edit_button.clicked.connect(self.edit_user)
        self.delete_button.clicked.connect(self.delete_user)
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
        if isinstance(user_module.users, list):
            self.table.setRowCount(len(user_module.users))
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels([
                "User ID", "Username", "Email", "First Name", "Last Name", "Is Active", "Last Login", "Roles"
            ])

            for row, user in enumerate(user_module.users):
                self.table.setItem(row, 0, QTableWidgetItem(str(user.get('UserId', ''))))
                self.table.setItem(row, 1, QTableWidgetItem(str(user.get('Username', ''))))
                self.table.setItem(row, 2, QTableWidgetItem(str(user.get('Email', ''))))
                self.table.setItem(row, 3, QTableWidgetItem(str(user.get('FirstName', ''))))
                self.table.setItem(row, 4, QTableWidgetItem(str(user.get('LastName', ''))))
                self.table.setItem(row, 5, QTableWidgetItem('Yes' if user.get('IsActive') else 'No'))
                self.table.setItem(row, 6, QTableWidgetItem(str(user.get('LastLoginDate', ''))))
                self.table.setItem(row, 7, QTableWidgetItem(str(user.get('Roles', ''))))

            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        else:
            logger.error(f"Unexpected type for user_module.users: {type(user_module.users)}")

    def search_users(self):
        if not self.is_connected:
            return
        search_term = self.search_input.text()
        user_module.search_users(search_term)

    def add_user(self):
        if not self.is_connected:
            return
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if user_module.add_user(data):
                logger.info("User added successfully.")
                user_module.fetch_users()
            else:
                logger.error("Failed to add user.")

    def edit_user(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(user_module.users, list) and 0 <= selected_row < len(user_module.users):
            user = user_module.users[selected_row]
            dialog = UserDialog(self, user.get('UserId'))
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if user_module.update_user(data):
                    logger.info("User updated successfully.")
                    user_module.fetch_users()
                else:
                    logger.error("Failed to update user.")
        else:
            logger.warning("No user selected for editing.")

    def delete_user(self):
        if not self.is_connected:
            return
        selected_row = self.table.currentRow()
        if isinstance(user_module.users, list) and 0 <= selected_row < len(user_module.users):
            user = user_module.users[selected_row]
            user_id = user.get('UserId')
            if user_id:
                if user_module.delete_user(user_id):
                    logger.info(f"User {user.get('Username', '')} deleted successfully.")
                    user_module.fetch_users()
                else:
                    logger.error(f"Failed to delete user {user.get('Username', '')}.")
            else:
                logger.error("Invalid user ID for deletion.")
        else:
            logger.warning("No user selected for deletion.")


class UserDialog(QDialog):
    def __init__(self, parent=None, user_id: Optional[int] = None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Add User" if user_id is None else "Edit User")
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.username_input = QLineEdit()
        self.email_input = QLineEdit()
        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()
        self.is_active_input = QCheckBox()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.roles_list = QListWidget()
        self.roles_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        layout.addRow("Username:", self.username_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("First Name:", self.first_name_input)
        layout.addRow("Last Name:", self.last_name_input)
        layout.addRow("Is Active:", self.is_active_input)
        layout.addRow("Password:", self.password_input)
        layout.addRow("Roles:", self.roles_list)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)


        layout.addRow(buttons)

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.populate_roles()
        if self.user_id:
            self.populate_data()

    def populate_roles(self):
        roles = user_module.get_all_roles()
        for role in roles:
            item = QListWidgetItem(role['RoleName'])
            item.setData(Qt.ItemDataRole.UserRole, role['RoleId'])
            self.roles_list.addItem(item)

    def populate_data(self):
        if self.user_id is not None:
            user = user_module.get_user(self.user_id)
        else:
            user = None
        if user:
            self.username_input.setText(user.get('Username', ''))
            self.email_input.setText(user.get('Email', ''))
            self.first_name_input.setText(user.get('FirstName', ''))
            self.last_name_input.setText(user.get('LastName', ''))
            self.is_active_input.setChecked(user.get('IsActive', False))
            self.password_input.setPlaceholderText("Leave blank to keep current password")

            if self.user_id is not None:
                user_roles = user_module.get_user_roles(self.user_id)
            else:
                user_roles = []
            for i in range(self.roles_list.count()):
                item = self.roles_list.item(i)
                if any(role['RoleId'] == item.data(Qt.ItemDataRole.UserRole) for role in user_roles):
                    item.setSelected(True)

    def get_data(self) -> Dict[str, Any]:
        data = {
            'UserId': self.user_id,
            'Username': self.username_input.text(),
            'Email': self.email_input.text(),
            'FirstName': self.first_name_input.text(),
            'LastName': self.last_name_input.text(),
            'IsActive': self.is_active_input.isChecked(),
            'Roles': [item.data(Qt.ItemDataRole.UserRole) for item in self.roles_list.selectedItems()]
        }
        if self.password_input.text():
            data['PasswordHash'] = self.password_input.text()  # In a real app, this should be hashed
        return data