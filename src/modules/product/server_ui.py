from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QHeaderView,
                               QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QDialog,
                               QFormLayout, QSpinBox, QComboBox, QTextEdit, QSplitter, QCheckBox)
from PySide6.QtCore import Qt, Signal, QTimer, QObject, QThread
from PySide6.QtGui import QIcon
from .server import server_module, ServerInfo
from ui.ui_styles import TMSWidget, StyledPushButton, Styles, Colors, Fonts, apply_styles
import logging

logger = logging.getLogger('server_ui')

class DatabaseActivityWorker(QObject):
    activity_updated = Signal(list)

    def update_activity(self):
        try:
            activities = server_module.get_recent_activities()
            self.activity_updated.emit(activities)
        except Exception as e:
            logger.exception(f"Error updating database activity: {e}")

class ServerWidget(TMSWidget):
    server_added = Signal(ServerInfo)
    server_updated = Signal(ServerInfo)
    server_deleted = Signal(int)

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.init_ui()
        self.load_all_servers()
        self.start_activity_monitor()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Main content
        content = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(content)

        # Left panel - Server Management
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search servers...")
        
        self.search_button = StyledPushButton("", "search")
        self.search_button.setFixedSize(32, 32)
        self.search_button.clicked.connect(self.search_servers)
        self.search_input.returnPressed.connect(self.search_servers)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        left_layout.addLayout(search_layout)

        # Server table
        self.server_table = QTableWidget()
        self.create_server_table()
        left_layout.addWidget(self.server_table)

        # Action buttons
        button_layout = QHBoxLayout()
        self.add_button = StyledPushButton("Add", "add")
        self.modify_button = StyledPushButton("Modify", "edit")
        self.delete_button = StyledPushButton("Delete", "delete")
        self.connect_button = StyledPushButton("Connect", "connect")
        
        for button in [self.add_button, self.modify_button, self.delete_button, self.connect_button]:
            button_layout.addWidget(button)
            button.setFixedHeight(40)

        self.add_button.clicked.connect(self.add_server)
        self.modify_button.clicked.connect(self.modify_server)
        self.delete_button.clicked.connect(self.delete_server)
        self.connect_button.clicked.connect(self.connect_to_server)
        
        left_layout.addLayout(button_layout)

        # Right panel - Database Activity
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        activity_label = QLabel("Database Activity")
        activity_label.setFont(Fonts.SUBTITLE)
        right_layout.addWidget(activity_label)

        self.activity_table = QTableWidget()
        self.create_activity_table()
        right_layout.addWidget(self.activity_table)

        content.addWidget(left_panel)
        content.addWidget(right_panel)
        content.setStretchFactor(0, 2)
        content.setStretchFactor(1, 1)

    def create_server_table(self):
        headers = ["ID", "Name", "IP Address", "Type", "Active", "Connected", "Last Connection"]
        self.server_table.setColumnCount(len(headers))
        self.server_table.setHorizontalHeaderLabels(headers)
    
        # Set horizontal header properties
        horizontal_header = self.server_table.horizontalHeader()
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setStretchLastSection(True)
        # Enable interactive resizing for all columns
        for i in range(len(headers)):
            horizontal_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # Set vertical header properties
        vertical_header = self.server_table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    
        # Set table properties
        self.server_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.server_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.server_table.setAlternatingRowColors(True)
        self.server_table.setSortingEnabled(True)
        self.server_table.setWordWrap(True)
    
        # Connect signals
        self.server_table.cellClicked.connect(self.server_selected)
        self.server_table.cellDoubleClicked.connect(self.modify_server)
    
        # Apply style
        
        
        # Adjust table to contents
        self.server_table.resizeColumnsToContents()
        self.server_table.resizeRowsToContents()
        self.server_table.setColumnWidth(0, 50)  # Set a fixed width for the ID column
        horizontal_header.setMinimumSectionSize(100)  # Set a minimum width for all columns


    def create_activity_table(self):
        headers = ["Timestamp", "Module", "Server", "Action", "Status"]
        self.activity_table.setColumnCount(len(headers))
        self.activity_table.setHorizontalHeaderLabels(headers)
        
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.activity_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setSortingEnabled(True)
        
        self.activity_table.setWordWrap(True)
        self.activity_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)


    def load_all_servers(self):
        try:
            servers = server_module.get_all_servers()
            self.populate_server_table(servers)
        except Exception as e:
            logger.exception(f"Error loading servers: {e}")
            QMessageBox.critical(self, "Load Error", f"Failed to load servers: {str(e)}")

    def populate_server_table(self, servers):
        self.server_table.setSortingEnabled(False)
        self.server_table.setRowCount(len(servers))
        for row, server in enumerate(servers):
            self.server_table.setItem(row, 0, QTableWidgetItem(str(server.id)))
            self.server_table.setItem(row, 1, QTableWidgetItem(server.name))
            self.server_table.setItem(row, 2, QTableWidgetItem(server.ip_addr))
            self.server_table.setItem(row, 3, QTableWidgetItem(server.server_type))
            self.server_table.setItem(row, 4, QTableWidgetItem("Yes" if server.is_active else "No"))
            self.server_table.setItem(row, 5, QTableWidgetItem("Yes" if server_module.is_connected() and server_module.get_active_server() == server else "No"))
            self.server_table.setItem(row, 6, QTableWidgetItem(str(server.last_connection)))
            self.server_table.setItem(row, 7, QTableWidgetItem(server.remarks))
        
        self.server_table.resizeRowsToContents()
        self.update_button_states()
        self.server_table.setSortingEnabled(True)

    def server_selected(self, row, column):
        self.update_button_states()

    def update_button_states(self):
        selected = bool(self.server_table.selectionModel().selectedRows())
        self.modify_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)
        self.connect_button.setEnabled(selected)

    def add_server(self):
        try:
            dialog = ServerConnectionDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                server_info = dialog.get_server_info()
                if server_module.add_server(server_info):
                    self.server_added.emit(server_info)
                    self.load_all_servers()
                    QMessageBox.information(self, "Add Server", "Server added successfully.")
                else:
                    QMessageBox.warning(self, "Add Server", "Failed to add server. Please check the connection details and try again.")
        except Exception as e:
            logger.exception(f"Error adding server: {e}")
            QMessageBox.critical(self, "Add Server Error", f"An unexpected error occurred: {str(e)}")

    def modify_server(self):
        try:
            selected_rows = self.server_table.selectionModel().selectedRows()
            if len(selected_rows) == 1:
                server_id = int(self.server_table.item(selected_rows[0].row(), 0).text())
                server = server_module.get_server(server_id)
                if server:
                    dialog = ServerConnectionDialog(self, server)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        updated_server_info = dialog.get_server_info()
                        if server_module.update_server(updated_server_info):
                            self.server_updated.emit(updated_server_info)
                            self.load_all_servers()
                            QMessageBox.information(self, "Server Updated", f"Server '{updated_server_info.name}' has been updated successfully.")
                        else:
                            QMessageBox.warning(self, "Update Error", "Failed to update the server. Please check the connection details and try again.")
                else:
                    QMessageBox.warning(self, "Server Not Found", f"Server with ID {server_id} not found.")
            else:
                QMessageBox.warning(self, "Selection Error", "Please select a single row to edit.")
        except Exception as e:
            logger.exception(f"Error modifying server: {e}")
            QMessageBox.critical(self, "Modify Server Error", f"An unexpected error occurred: {str(e)}")

    def delete_server(self):
        try:
            selected_rows = self.server_table.selectionModel().selectedRows()
            if len(selected_rows) == 1:
                server_id = int(self.server_table.item(selected_rows[0].row(), 0).text())
                confirm = QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this server?",
                                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if confirm == QMessageBox.StandardButton.Yes:
                    if server_module.delete_server(server_id):
                        self.server_deleted.emit(server_id)
                        self.load_all_servers()
                        QMessageBox.information(self, "Server Deleted", "The server has been deleted.")
                    else:
                        QMessageBox.warning(self, "Delete Error", "Failed to delete the server. Please try again.")
            else:
                QMessageBox.warning(self, "Selection Error", "Please select a single row to delete.")
        except Exception as e:
            logger.exception(f"Error deleting server: {e}")
            QMessageBox.critical(self, "Delete Server Error", f"An unexpected error occurred: {str(e)}")

    def connect_to_server(self):
        try:
            selected_rows = self.server_table.selectionModel().selectedRows()
            if len(selected_rows) == 1:
                server_id = int(self.server_table.item(selected_rows[0].row(), 0).text())
                server = server_module.get_server(server_id)
                if server:
                    confirm = QMessageBox.question(self, "Connect to Server", 
                                                f"Are you sure you want to connect to {server.name}?",
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if confirm == QMessageBox.StandardButton.Yes:
                        if server_module.connect_to_database(server):
                            QMessageBox.information(self, "Connection Successful", f"Successfully connected to {server.name}")
                            self.load_all_servers()
                            self.main_window.on_server_changed(server)
                        else:
                            QMessageBox.warning(self, "Connection Failed", f"Failed to connect to {server.name}")
                else:
                    QMessageBox.warning(self, "Server Not Found", f"Server with ID {server_id} not found.")
            else:
                QMessageBox.warning(self, "Selection Error", "Please select a single server to connect.")
        except Exception as e:
            logger.exception(f"Error connecting to server: {e}")
            QMessageBox.critical(self, "Connection Error", f"An unexpected error occurred: {str(e)}")

    def search_servers(self):
        try:
            search_term = self.search_input.text().strip().lower()
            all_servers = server_module.get_all_servers()
            filtered_servers = [s for s in all_servers if search_term in s.name.lower()]
            self.populate_server_table(filtered_servers)
        except Exception as e:
            logger.exception(f"Error searching servers: {e}")
            QMessageBox.critical(self, "Search Error", f"An unexpected error occurred while searching: {str(e)}")

    def start_activity_monitor(self):
        self.worker = DatabaseActivityWorker()
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        self.worker.activity_updated.connect(self.update_activity_table)
        self.worker_thread.started.connect(self.worker.update_activity)

        self.timer = QTimer()
        self.timer.setInterval(5000)  # Update every 5 seconds
        self.timer.timeout.connect(self.worker.update_activity)

        self.worker_thread.start()
        self.timer.start()

    def update_activity_table(self, activities):
        self.activity_table.setSortingEnabled(False)
        self.activity_table.setRowCount(len(activities))
        
        for row, activity in enumerate(activities):
            for col, key in enumerate(['timestamp', 'module', 'server', 'action', 'status']):
                item = QTableWidgetItem(str(activity[key]))
                if col == 0:  # Timestamp column
                    item.setData(Qt.ItemDataRole.UserRole, activity[key])
                self.activity_table.setItem(row, col, item)
        
        self.activity_table.setSortingEnabled(True)
        self.activity_table.sortItems(0, Qt.SortOrder.DescendingOrder)

    def closeEvent(self, event):
        try:
            if hasattr(self, 'timer'):
                self.timer.stop()
            if hasattr(self, 'worker_thread'):
                self.worker_thread.quit()
                self.worker_thread.wait()
            super().closeEvent(event)
        except Exception as e:
            logger.exception(f"Error in closeEvent: {e}")

class ServerConnectionDialog(QDialog):
    def __init__(self, parent=None, server_info=None):
        super().__init__(parent)
        self.setWindowTitle("Server Connection" if server_info is None else "Edit Server Connection")
        self.server_info = server_info
        self.init_ui()
        apply_styles(self)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.inputs = {
            'name': QLineEdit(),
            'host': QLineEdit(),
            'port': QSpinBox(),
            'dbname': QLineEdit(),
            'user': QLineEdit(),
            'password': QLineEdit(),
            'server_type': QComboBox(),
            'is_active': QCheckBox("Active"),
            'remarks': QTextEdit()
        }

        self.inputs['port'].setRange(1, 65535)
        self.inputs['port'].setValue(1433)
        self.inputs['password'].setEchoMode(QLineEdit.EchoMode.Password)
        self.inputs['server_type'].addItems(["Primary", "Secondary", "Backup"])
        self.inputs['is_active'].setChecked(True)

        

        for label, widget in [
            ("Name:", self.inputs['name']),
            ("Host:", self.inputs['host']),
            ("Port:", self.inputs['port']),
            ("Database:", self.inputs['dbname']),
            ("User:", self.inputs['user']),
            ("Password:", self.inputs['password']),
            ("Server Type:", self.inputs['server_type']),
            ("Status:", self.inputs['is_active']),
            ("Remarks:", self.inputs['remarks'])
        ]:
            form_layout.addRow(QLabel(label), widget)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        save_button = StyledPushButton("Save", "add")
        cancel_button = StyledPushButton("Cancel", "delete")
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        if self.server_info:
            self.populate_fields()

    def populate_fields(self):
        if self.server_info:
            self.inputs['name'].setText(self.server_info.name)
            self.inputs['host'].setText(self.server_info.ip_addr)
            self.inputs['port'].setValue(self.server_info.port)
            self.inputs['dbname'].setText(self.server_info.database)
            self.inputs['user'].setText(self.server_info.user)
            self.inputs['password'].setText(self.server_info.password)
            self.inputs['server_type'].setCurrentText(self.server_info.server_type)
            self.inputs['is_active'].setChecked(self.server_info.is_active)
            self.inputs['remarks'].setPlainText(self.server_info.remarks)

    def get_server_info(self):
        return ServerInfo(
            id=self.server_info.id if self.server_info else None,
            name=self.inputs['name'].text(),
            ip_addr=self.inputs['host'].text(),
            port=self.inputs['port'].value(),
            database=self.inputs['dbname'].text(),
            user=self.inputs['user'].text(),
            password=self.inputs['password'].text(),
            server_type=self.inputs['server_type'].currentText(),
            is_active=self.inputs['is_active'].isChecked(),
            last_connection=self.server_info.last_connection if self.server_info else None,
            remarks=self.inputs['remarks'].toPlainText()
        )
