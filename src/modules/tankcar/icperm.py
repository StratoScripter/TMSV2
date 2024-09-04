from typing import List, Dict, Any, Optional
from modules.logger_config import get_logger

logger = get_logger('icperm')

class ICPermModule:
    def __init__(self, server_module):
        self.server_module = server_module

    def initialize(self, server_info):
        if not self.server_module.connect_to_database(server_info):
            raise ConnectionError(f"Failed to connect to server: {server_info.name}")

    def log_activity(self, module: str, action: str, status: str):
        self.server_module.log_activity(module, action, status)

    def execute_query(self, query, params=None, fetch=True):
        try:
            result = self.server_module.execute_query(query, params, fetch)
            return result
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise

    def get_all_drivers(self) -> List[Dict[str, Any]]:
        try:
            query = """
                SELECT DriverId, DriverName, LicenseNumber, ContactNumber, ModifiedDate
                FROM inventory.Driver
            """
            drivers = self.execute_query(query)
            self.log_activity("PermissionModule","Get All Drivers", f"Success: Retrieved {len(drivers)} drivers")
            return drivers
        except Exception as e:
            logger.error(f"Error fetching drivers: {e}")
            self.log_activity("PermissionModule","Get All Drivers", f"Failed: {str(e)}")
            return []

    def add_driver(self, driver: Dict[str, Any]) -> bool:
        try:
            query = """
                INSERT INTO inventory.Driver (DriverName, LicenseNumber, ContactNumber)
                OUTPUT INSERTED.DriverId
                VALUES (?, ?, ?)
            """
            result = self.execute_query(query, (driver['DriverName'], driver['LicenseNumber'], driver['ContactNumber']))
            driver_id = result[0]['DriverId']
            logger.info(f"Added new driver: {driver['DriverName']}")
            self.log_activity("PermissionModule","Add Driver", f"Success: {driver['DriverName']}")
            return True
        except Exception as e:
            logger.error(f"Error adding driver: {e}")
            self.log_activity("PermissionModule","Add Driver", f"Failed: {str(e)}")
            return False

    def get_driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT DriverId, DriverName, LicenseNumber, ContactNumber, ModifiedDate
                FROM inventory.Driver
                WHERE DriverId = ?
            """
            result = self.execute_query(query, (driver_id,))
            if result:
                self.log_activity("PermissionModule","Get Driver", f"Success: ID {driver_id}")
                return result[0]
            else:
                logger.warning(f"No driver found with ID: {driver_id}")
                return None
        except Exception as e:
            logger.error(f"Error fetching driver: {e}")
            self.log_activity("PermissionModule","Get Driver", f"Failed: {str(e)}")
            return None

    def update_driver(self, driver: Dict[str, Any]) -> bool:
        try:
            query = """
                UPDATE inventory.Driver
                SET DriverName = ?, LicenseNumber = ?, ContactNumber = ?
                WHERE DriverId = ?
            """
            self.execute_query(query, (driver['DriverName'], driver['LicenseNumber'], driver['ContactNumber'], driver['DriverId']), fetch=False)
            logger.info(f"Updated driver: {driver['DriverId']}")
            self.log_activity("PermissionModule","Update Driver", f"Success: ID {driver['DriverId']}")
            return True
        except Exception as e:
            logger.error(f"Error updating driver: {e}")
            self.log_activity("PermissionModule","Update Driver", f"Failed: {str(e)}")
            return False

    def delete_driver(self, driver_id: str) -> bool:
        try:
            query = "DELETE FROM inventory.Driver WHERE DriverId = ?"
            self.execute_query(query, (driver_id,), fetch=False)
            logger.info(f"Deleted driver: {driver_id}")
            self.log_activity("PermissionModule","Delete Driver", f"Success: ID {driver_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting driver: {e}")
            self.log_activity("PermissionModule","Delete Driver", f"Failed: {str(e)}")
            return False

    def search_drivers(self, search_term: str) -> List[Dict[str, Any]]:
        try:
            query = """
            SELECT DriverId, DriverName, LicenseNumber, ContactNumber, ModifiedDate
            FROM inventory.Driver
            WHERE DriverName LIKE ? OR LicenseNumber LIKE ? OR ContactNumber LIKE ?
            """
            drivers = self.execute_query(query, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            self.log_activity("PermissionModule","Search Drivers", f"Success: Found {len(drivers)} drivers")
            return drivers
        except Exception as e:
            logger.error(f"Error searching drivers: {e}")
            self.log_activity("PermissionModule","Search Drivers", f"Failed: {str(e)}")
            return []
