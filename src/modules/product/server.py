import pyodbc
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from datetime import datetime
from collections import deque
import threading
import time
import re
import os
import json
from dataclasses import dataclass, asdict
import logging
from PySide6.QtCore import QObject, Signal
from logging.handlers import RotatingFileHandler

# Constants
CONFIG_FILE = 'config.json'
LOG_FILE = 'server_module.log'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    filename='server_module.log',
    filemode='a'
)
logger = logging.getLogger(__name__)
db_activity_logger = logging.getLogger('db_activity')

@dataclass
class ServerInfo:
    id: Optional[int]
    name: str
    ip_addr: str
    port: int
    database: str
    user: str
    password: str
    server_type: str
    is_active: bool = True
    last_connection: Optional[str] = None
    remarks: str = ""

    def to_dict(self):
        return asdict(self)

class DatabaseConnector:
    @staticmethod
    def connect(server_info: ServerInfo) -> pyodbc.Connection:
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_info.ip_addr},{server_info.port};"
                f"DATABASE={server_info.database};"
                f"UID={server_info.user};"
                f"PWD={server_info.password};"
                "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
            )
            return pyodbc.connect(conn_str)
        except pyodbc.Error as e:
            logger.error(f"Failed to connect to {server_info.name}: {str(e)}")
            raise

    @staticmethod
    def disconnect(connection: pyodbc.Connection) -> None:
        try:
            connection.close()
        except pyodbc.Error as e:
            logger.error(f"Error disconnecting: {str(e)}")

class ServerModule(QObject):
    connection_status_changed = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.servers = self.config.get('servers', [])
        self.activity_log = deque(maxlen=2000)
        self.active_server: Optional[ServerInfo] = None
        self.connection = None

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            return {'servers': []}
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {'servers': []}

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")

    def add_server(self, server_info: ServerInfo) -> bool:
        try:
            self._validate_server_info(server_info)
            server_info.id = max([s['id'] for s in self.servers] + [0]) + 1
            self.servers.append(server_info.to_dict())
            self.config['servers'] = self.servers
            self.save_config()
            logger.info(f"Added new server: {server_info.name}")
            self.log_activity("ServerModule", "Add Server", "Success")
            return True
        except Exception as e:
            logger.exception(f"Error adding server: {e}")
            self.log_activity("ServerModule", "Add Server", f"Error: {str(e)}")
            return False

    def get_all_servers(self) -> List[ServerInfo]:
        return [ServerInfo(**server) for server in self.servers]

    def get_server(self, server_id: int) -> Optional[ServerInfo]:
        for server in self.servers:
            if server['id'] == server_id:
                return ServerInfo(**server)
        return None

    def update_server(self, server_info: ServerInfo) -> bool:
        try:
            self._validate_server_info(server_info)
            for i, server in enumerate(self.servers):
                if server['id'] == server_info.id:
                    self.servers[i] = server_info.to_dict()
                    self.config['servers'] = self.servers
                    self.save_config()
                    logger.info(f"Updated server: {server_info.name}")
                    self.log_activity("ServerModule", "Update Server", "Success")
                    return True
            logger.error(f"Failed to update server: Server with ID {server_info.id} not found")
            return False
        except Exception as e:
            logger.exception(f"Error updating server: {e}")
            return False

    def delete_server(self, server_id: int) -> bool:
        try:
            self.servers = [s for s in self.servers if s['id'] != server_id]
            self.config['servers'] = self.servers
            self.save_config()
            logger.info(f"Deleted server with ID: {server_id}")
            self.log_activity("ServerModule", f"Server ID Deleted: {server_id}", "Success")
            return True
        except Exception as e:
            logger.exception(f"Error deleting server: {e}")
            return False

    def connect_to_database(self, server_info: ServerInfo) -> bool:
        try:
            self.connection = DatabaseConnector.connect(server_info)
            self.active_server = server_info
            server_info.last_connection = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.update_server(server_info)
            logger.info(f"Connected to database: {server_info.name}")
            self.log_activity("ServerModule", "Connect", "Success")
            self.connection_status_changed.emit(True, f"Connected successfully to {server_info.name}")
            return True
        except Exception as e:
            logger.exception(f"Error connecting to database: {e}")
            self.log_activity("ServerModule", "Connect", f"Error: {str(e)}")
            self.connection_status_changed.emit(False, f"Error connecting to {server_info.name}")
            return False
    
    

    def disconnect_from_database(self) -> None:
        if self.active_server and self.connection:
            try:
                DatabaseConnector.disconnect(self.connection)
                logger.info(f"Disconnected from database: {self.active_server.name}")
                self.log_activity("ServerModule", "Disconnect", "Success")
                self.active_server = None
                self.connection = None
                self.connection_status_changed.emit(False, "Disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
                self.log_activity("ServerModule", "Disconnect", f"Error: {str(e)}")
                self.connection_status_changed.emit(False, f"Error disconnecting: {str(e)}")
        else:
            logger.warning("No active server to disconnect from")
            self.connection_status_changed.emit(False, "No active connection to disconnect")

    def _validate_server_info(self, server_info: ServerInfo) -> None:
        if not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', server_info.ip_addr):
            raise ValueError(f"Invalid IP address: {server_info.ip_addr}")
        if not 1 <= server_info.port <= 65535:
            raise ValueError(f"Invalid port number: {server_info.port}")
        if not server_info.name or not server_info.database or not server_info.user or not server_info.password:
            raise ValueError("Name, database, user, and password cannot be empty")

    def execute_query(self, query: str, params=None, fetch=True):
        if not self.active_server or not self.connection:
            raise ValueError("No active server connection")
        
        try:
            with self.connection.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                else:
                    self.connection.commit()
                    return None
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise

    def log_activity(self, module: str, action: str, status: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        activity = {
            "timestamp": timestamp,
            "module": module,
            "server": self.active_server.name if self.active_server else "Unknown",
            "action": action,
            "status": status
        }
        self.activity_log.appendleft(activity)
        db_activity_logger.info(f"{module} | {activity['server']} | {action} | {status}")

    def get_recent_activities(self) -> List[Dict]:
        return list(self.activity_log)

    def is_connected(self) -> bool:
        return self.connection is not None and self.active_server is not None

    def get_module_connection(self, module_name: str) -> Optional[pyodbc.Connection]:
        if not self.is_connected():
            self.error_occurred.emit(f"No active server connection for {module_name}")
            return None
        try:
            if self.active_server is None:
                raise ValueError("Active server is None")
            connection = DatabaseConnector.connect(self.active_server)
            logger.info(f"Created connection for module: {module_name}")
            return connection
        except Exception as e:
            logger.error(f"Error creating connection for module {module_name}: {e}")
            self.error_occurred.emit(f"Error creating connection for {module_name}: {str(e)}")
            return None

    def get_active_server(self) -> Optional[ServerInfo]:
        return self.active_server

server_module = ServerModule()