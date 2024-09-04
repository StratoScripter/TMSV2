import sys

import asyncio
import logging
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QStackedWidget, QLabel, QFrame, QTabWidget, QStatusBar,
                               QSizePolicy)
from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from ui.ui_styles import *

from modules.product.product_ui import ProductWidget
from modules.product.loadingarm_ui import LoadingArmWidget
from modules.product.server_ui import ServerWidget
from modules.product.weighbridge_ui import WeighbridgeWidget
from modules.product.storagetank_ui import StorageTankWidget
from modules.product.modbus_ui import ModbusWidget
from modules.contracts.contract_ui import ContractWidget
from modules.contracts.order_ui import OrderWidget
from modules.historical.historical_ui import HistoricalWidget
from modules.tankcar.party_ui import PartyWidget
from modules.tankcar.vehicle_ui import VehicleWidget
from modules.users.user_ui import UserWidget
from modules.product.server import server_module

class ModuleManager:
    def __init__(self):
        self.modules = {
            "Server": ServerWidget,
            "Product": ProductWidget,
            "Loading Arm": LoadingArmWidget,
            "WeighBridge": WeighbridgeWidget,
            "Storage Tank": StorageTankWidget,
            "Modbus": ModbusWidget,
            "Contract": ContractWidget,
            "Order": OrderWidget,
            "Historical": HistoricalWidget,
            "Party": PartyWidget,
            "Vehicle": VehicleWidget,
            "User": UserWidget
        }
        self.module_instances = {}
        self.current_module = None

    def initialize_modules(self, main_window):
        for name, module_class in self.modules.items():
            instance = module_class(main_window) if module_class == ServerWidget else module_class()
            apply_styles(instance, recursive=True)  # Apply styles to the module
            self.module_instances[name] = instance

    def switch_module(self, module_name):
        if self.current_module and hasattr(self.current_module, 'stop_refresh_timer'):
            self.current_module.stop_refresh_timer()

        self.current_module = self.module_instances.get(module_name)
        if self.current_module:
            if hasattr(self.current_module, 'start_refresh_timer'):
                self.current_module.start_refresh_timer()
            return self.current_module
        else:
            raise ValueError(f"Module {module_name} not found")

class RibbonTab(TMSWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(10, 5, 10, 5)
        self.setStyleSheet(Styles.widget())

    def addWidget(self, widget):
        self._layout.addWidget(widget)

class TMSMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TMS - Oil Refinery")
        self.resize(1200, 800)

        # Apply base styles to the entire application
        Styles.apply_base_styles(QApplication.instance())

        self.module_manager = ModuleManager()
        self.module_manager.initialize_modules(self)

        self.setup_logging()
        self.init_ui()
        self.setup_shortcuts()
        self.setup_statusbar()
        
        server_module.connection_status_changed.connect(self.on_connection_status_changed)

        # Apply styles to the main window and all its children (including modules)
        self.apply_styles_recursively(self)

        # Load last selected module
        self.load_last_module()

        # Set the main window style
        self.setStyleSheet(Styles.main_window())

    def apply_styles_recursively(self, widget):
        apply_styles(widget, recursive=True)
        for module_instance in self.module_manager.module_instances.values():
            apply_styles(module_instance, recursive=True)

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def init_ui(self):
        main_widget = TMSWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.create_ribbon(main_layout)
        self.create_content_area(main_layout)

        self.setCentralWidget(main_widget)

    def create_ribbon(self, main_layout):
        self.ribbon = QTabWidget()
        self.ribbon.setObjectName("ribbon")
        self.ribbon.setTabPosition(QTabWidget.TabPosition.North)
        self.ribbon.setMovable(False)
        self.ribbon.setDocumentMode(True)
        self.ribbon.setStyleSheet(Styles.tab_widget())
        
        modules = [
            ("Connectivity", [
                ("🖥️ Server", "Server"),
                ("🔌 Modbus", "Modbus"),
            ]),
            ("Operations", [
                ("🛢️ Product", "Product"),
                ("🦾 Loading Arm", "Loading Arm"),
                ("⚖️ WeighBridge", "WeighBridge"),
                ("🫙 Storage Tank", "Storage Tank"),
            ]),
            ("Management", [
                ("📝 Contract", "Contract"),
                ("📦 Order", "Order"),
                ("📊 Historical", "Historical"),
            ]),
            ("Logistics", [
                ("🎉 Party", "Party"),
                ("🚚 Vehicle", "Vehicle"),
            ]),
            ("Administration", [
                ("👤 User", "User"),
            ]),
        ]

        for group_name, group_modules in modules:
            group_tab = RibbonTab()
            for icon, name in group_modules:
                button = StyledPushButton(f"{icon} {name}")
                button.setFont(Fonts.MAIN)
                button.clicked.connect(lambda checked, n=name: self.switch_module(n))
                group_tab.addWidget(button)
            self.ribbon.addTab(group_tab, group_name)

        # Create a container widget for the ribbon and connection status
        ribbon_container = TMSWidget()
        ribbon_layout = QHBoxLayout(ribbon_container)
        ribbon_layout.setContentsMargins(0, 0, 0, 0)
        ribbon_layout.setSpacing(0)

        # Add the ribbon to the left side of the container
        ribbon_layout.addWidget(self.ribbon)

        # Add a stretch to push the connection status label to the right
        ribbon_layout.addStretch(1)

        # Add connection status label
        self.connection_status_label = QLabel("Not connected")
        self.connection_status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.connection_status_label.setStyleSheet(f"color: {Colors.ACCENT}; font-weight: bold; padding-right: 10px;")
        ribbon_layout.addWidget(self.connection_status_label)

        # Add the ribbon container to the main layout
        main_layout.addWidget(ribbon_container)

        # Set the size policy of the ribbon to prefer its minimum size
        self.ribbon.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

    def create_content_area(self, main_layout):
        content_widget = TMSWidget()
        content_widget.setObjectName("content")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)  # Reduce spacing
        content_layout.setContentsMargins(10, 10, 10, 10)

        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        for instance in self.module_manager.module_instances.values():
            self.stacked_widget.addWidget(instance)

        main_layout.addWidget(content_widget, 1)

    def setup_shortcuts(self):
        for i, (name, _) in enumerate(self.module_manager.modules.items(), start=1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut.activated.connect(lambda n=name: self.switch_module(n))

    def setup_statusbar(self):
        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet(Styles.status_bar())
        self.setStatusBar(self.statusbar)

    def switch_module(self, module_name):
        try:
            module_instance = self.module_manager.switch_module(module_name)
            if module_instance:
                self.stacked_widget.setCurrentWidget(module_instance)
                apply_styles(module_instance, recursive=True)  # Reapply styles
                self.save_last_module(module_name)
                self.logger.info(f"Switched to module: {module_name}")
                self.statusbar.showMessage(f"Current module: {module_name}", 3000)
                
                # Highlight active module
                for i in range(self.ribbon.count()):
                    tab = self.ribbon.widget(i)
                    for j in range(tab.layout().count()):
                        button = tab.layout().itemAt(j).widget()
                        if isinstance(button, StyledPushButton) and button.text().endswith(module_name):
                            button.setStyleSheet(f"background-color: {Colors.PRIMARY}; color: {Colors.TEXT};")
                        else:
                            button.setStyleSheet(Styles.push_button())
            else:
                raise ValueError(f"Module {module_name} not found")
        except Exception as e:
            self.logger.error(f"Error switching to module {module_name}: {str(e)}")
            self.statusbar.showMessage(f"Error switching to module: {module_name}", 3000)

    def on_connection_status_changed(self, is_connected, message):
        self.statusbar.showMessage(message, 5000)
        
        # Update connection status label
        if is_connected:
            server = server_module.get_active_server()
            if server:
                self.connection_status_label.setText(f"Connected to: {server.name}")
        else:
            self.connection_status_label.setText("Not connected")
        
        self.connection_status_label.setStyleSheet(Styles.connection_status_label(is_connected))

    def on_server_changed(self, server):
        self.logger.info(f"Server changed to: {server.name}")
        is_connected = server_module.is_connected()
        message = f"Connected to: {server.name}" if is_connected else "Disconnected from server"
        self.on_connection_status_changed(is_connected, message)

        for instance in self.module_manager.module_instances.values():
            if hasattr(instance, 'set_connection_status'):
                instance.set_connection_status(is_connected, message)
            if hasattr(instance, 'refresh_table'):
                instance.refresh_table()
            if hasattr(instance, 'update_server_info'):
                instance.update_server_info(server)

        self.logger.info(f"Server change to {server.name} completed successfully")

    def save_last_module(self, module_name):
        # TODO: Implement saving the last selected module to a file or settings
        pass

    def load_last_module(self):
        # TODO: Implement loading the last selected module from a file or settings
        # For now, we'll just switch to the "Server" module as a default
        self.switch_module("Server")

if __name__ == "__main__":
    
    app = QApplication(sys.argv)

    window = TMSMainWindow()
    window.show()   
    sys.exit(app.exec())