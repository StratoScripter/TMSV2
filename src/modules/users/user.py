# user.py

from PySide6.QtCore import QObject, Signal, Slot
from modules.product.server import server_module
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class UserModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.users: List[Dict[str, Any]] = []
        self.connection = None
        server_module.connection_status_changed.connect(self.on_connection_status_changed)

    @Slot(bool, str)
    def on_connection_status_changed(self, is_connected: bool, message: str):
        if is_connected:
            self.connect_to_database()
        else:
            self.disconnect_from_database()

    def connect_to_database(self):
        try:
            self.connection = server_module.get_module_connection(self.__class__.__name__)
            if self.connection:
                logger.info(f"{self.__class__.__name__} connected to database")
                self.fetch_users()
            else:
                logger.error(f"{self.__class__.__name__} failed to connect to database")
                self.error_occurred.emit("Failed to connect to database")
        except Exception as e:
            logger.exception(f"Error connecting to database: {e}")
            self.error_occurred.emit(f"Error connecting to database: {str(e)}")

    def disconnect_from_database(self):
        if self.connection:
            try:
                self.connection.close()
                logger.info("UserModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.users = []

    def execute_query(self, query: str, params: tuple = (), fetch: bool = True) -> Optional[List[Dict[str, Any]]]:
        if not self.connection:
            logger.error("No active database connection")
            self.error_occurred.emit("No active database connection")
            return None
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                if fetch:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                else:
                    self.connection.commit()
                    return [{"affected_rows": cursor.rowcount}]
        except Exception as e:
            logger.exception(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            self.connection.rollback()
            self.error_occurred.emit(f"Error executing query: {str(e)}")
            return None

    def fetch_users(self):
        query = """
        SELECT u.UserId, u.Username, u.Email, u.FirstName, u.LastName, u.IsActive, u.LastLoginDate, u.ModifiedDate,
               STRING_AGG(r.RoleName, ', ') AS Roles
        FROM inventory.ActiveUser u
        LEFT JOIN inventory.ActiveUserRole ur ON u.UserId = ur.UserId
        LEFT JOIN inventory.Role r ON ur.RoleId = r.RoleId
        GROUP BY u.UserId, u.Username, u.Email, u.FirstName, u.LastName, u.IsActive, u.LastLoginDate, u.ModifiedDate
        ORDER BY u.Username
        """
        results = self.execute_query(query)
        if results is not None:
            self.users = results
            self.data_updated.emit()
        else:
            logger.error("Failed to fetch users")
            self.error_occurred.emit("Failed to fetch users")

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        query = """
        SELECT u.UserId, u.Username, u.Email, u.FirstName, u.LastName, u.IsActive, u.LastLoginDate, u.ModifiedDate,
               STRING_AGG(r.RoleName, ', ') AS Roles
        FROM inventory.ActiveUser u
        LEFT JOIN inventory.ActiveUserRole ur ON u.UserId = ur.UserId
        LEFT JOIN inventory.Role r ON ur.RoleId = r.RoleId
        WHERE u.UserId = ?
        GROUP BY u.UserId, u.Username, u.Email, u.FirstName, u.LastName, u.IsActive, u.LastLoginDate, u.ModifiedDate
        """
        results = self.execute_query(query, params=(user_id,))
        return results[0] if results and isinstance(results, list) else None

    def add_user(self, user_data: Dict[str, Any]) -> bool:
        query = """
        INSERT INTO inventory.[User] 
        (Username, PasswordHash, Email, FirstName, LastName, IsActive)
        OUTPUT INSERTED.UserId
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            user_data['Username'], user_data['PasswordHash'], user_data['Email'],
            user_data['FirstName'], user_data['LastName'], user_data['IsActive']
        )
        result = self.execute_query(query, params=params)
        if result is None or len(result) == 0:
            logger.error("Failed to add user")
            return False
        
        user_id = result[0]['UserId']
        if 'Roles' in user_data and user_data['Roles']:
            self.update_user_roles(user_id, user_data['Roles'])
        
        return True

    def update_user(self, user_data: Dict[str, Any]) -> bool:
        query = """
        UPDATE inventory.[User]
        SET Username = ?, Email = ?, FirstName = ?, LastName = ?, IsActive = ?, ModifiedDate = GETDATE()
        WHERE UserId = ?
        """
        params = (
            user_data['Username'], user_data['Email'], user_data['FirstName'],
            user_data['LastName'], user_data['IsActive'], user_data['UserId']
        )
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to update user with ID {user_data['UserId']}")
            return False
        
        if 'Roles' in user_data:
            self.update_user_roles(user_data['UserId'], user_data['Roles'])
        
        return True

    def delete_user(self, user_id: int) -> bool:
        query = """
        UPDATE inventory.[User]
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE UserId = ?
        """
        result = self.execute_query(query, params=(user_id,), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to delete user with ID {user_id}")
            return False
        return True

    def search_users(self, search_term: str):
        query = """
        SELECT u.UserId, u.Username, u.Email, u.FirstName, u.LastName, u.IsActive, u.LastLoginDate, u.ModifiedDate,
               STRING_AGG(r.RoleName, ', ') AS Roles
        FROM inventory.ActiveUser u
        LEFT JOIN inventory.ActiveUserRole ur ON u.UserId = ur.UserId
        LEFT JOIN inventory.Role r ON ur.RoleId = r.RoleId
        WHERE u.Username LIKE ? OR u.Email LIKE ? OR u.FirstName LIKE ? OR u.LastName LIKE ?
        GROUP BY u.UserId, u.Username, u.Email, u.FirstName, u.LastName, u.IsActive, u.LastLoginDate, u.ModifiedDate
        ORDER BY u.Username
        """
        search_param = f"%{search_term}%"
        results = self.execute_query(query, params=(search_param, search_param, search_param, search_param))
        if results is not None:
            self.users = results
            self.data_updated.emit()
        else:
            logger.error("Failed to search users")
            self.error_occurred.emit("Failed to search users")

    def get_all_roles(self) -> List[Dict[str, Any]]:
        query = "SELECT RoleId, RoleName FROM inventory.Role ORDER BY RoleName"
        return self.execute_query(query) or []

    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        query = """
        SELECT r.RoleId, r.RoleName
        FROM inventory.ActiveUserRole ur
        JOIN inventory.Role r ON ur.RoleId = r.RoleId
        WHERE ur.UserId = ?
        """
        return self.execute_query(query, params=(user_id,)) or []

    def update_user_roles(self, user_id: int, role_ids: List[int]) -> bool:
        try:
            # First, remove all existing roles for the user
            remove_query = "DELETE FROM inventory.UserRole WHERE UserId = ?"
            self.execute_query(remove_query, params=(user_id,), fetch=False)

            # Then, add the new roles
            add_query = "INSERT INTO inventory.UserRole (UserId, RoleId) VALUES (?, ?)"
            for role_id in role_ids:
                self.execute_query(add_query, params=(user_id, role_id), fetch=False)

            return True
        except Exception as e:
            logger.error(f"Failed to update roles for user {user_id}: {e}")
            return False

user_module = UserModule()