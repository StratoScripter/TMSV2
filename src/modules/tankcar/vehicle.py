from PySide6.QtCore import QObject, Signal, Slot
from modules.product.server import server_module
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class VehicleModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.driver_vehicles: List[Dict[str, Any]] = []
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
                self.fetch_driver_vehicles()
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
                logger.info("VehicleModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.driver_vehicles = []

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

    def fetch_driver_vehicles(self):
        query = """
        SELECT dv.DriverId, dv.DriverName, dv.LicenseNumber, dv.ContactNumber,
               dv.LicensePlateNumber, dv.VehicleType, dv.Capacity, u.UnitName, dv.ModifiedDate
        FROM inventory.DriverVehicle dv
        LEFT JOIN inventory.Unit u ON dv.UnitId = u.UnitId
        WHERE dv.IsDeleted = 0
        ORDER BY dv.DriverName
        """
        results = self.execute_query(query)
        if results is not None:
            self.driver_vehicles = results
            self.data_updated.emit()
        else:
            logger.error("Failed to fetch driver vehicles")
            self.error_occurred.emit("Failed to fetch driver vehicles")

    def get_driver_vehicle_details(self, driver_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if driver_id is None:
            logger.error("get_driver_vehicle_details called with None driver_id")
            return None

        query = """
        SELECT DriverId, DriverName, LicenseNumber, ContactNumber,
               LicensePlateNumber, VehicleType, Capacity, UnitId, ModifiedDate
        FROM inventory.DriverVehicle
        WHERE DriverId = ? AND IsDeleted = 0
        """
        results = self.execute_query(query, params=(driver_id,))
        return results[0] if results and isinstance(results, list) else None

    def add_driver_vehicle(self, driver_vehicle_data: Dict[str, Any]) -> bool:
        query = """
        INSERT INTO inventory.DriverVehicle 
        (DriverName, LicenseNumber, ContactNumber, LicensePlateNumber, VehicleType, Capacity, UnitId)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            driver_vehicle_data['DriverName'], driver_vehicle_data['LicenseNumber'],
            driver_vehicle_data['ContactNumber'], driver_vehicle_data['LicensePlateNumber'],
            driver_vehicle_data['VehicleType'], driver_vehicle_data['Capacity'],
            driver_vehicle_data['UnitId']
        )
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error("Failed to add driver vehicle")
            return False
        return True

    def update_driver_vehicle(self, driver_vehicle_data: Dict[str, Any]) -> bool:
        query = """
        UPDATE inventory.DriverVehicle
        SET DriverName=?, LicenseNumber=?, ContactNumber=?, LicensePlateNumber=?, 
            VehicleType=?, Capacity=?, UnitId=?, ModifiedDate=GETDATE()
        WHERE DriverId=? AND IsDeleted = 0
        """
        params = (
            driver_vehicle_data['DriverName'], driver_vehicle_data['LicenseNumber'],
            driver_vehicle_data['ContactNumber'], driver_vehicle_data['LicensePlateNumber'],
            driver_vehicle_data['VehicleType'], driver_vehicle_data['Capacity'],
            driver_vehicle_data['UnitId'], driver_vehicle_data['DriverId']
        )
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to update driver vehicle with ID {driver_vehicle_data['DriverId']}")
            return False
        return True

    def delete_driver_vehicle(self, driver_id: str) -> bool:
        query = """
        UPDATE inventory.DriverVehicle
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE DriverId = ?
        """
        result = self.execute_query(query, params=(driver_id,), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to delete driver vehicle with ID {driver_id}")
            return False
        return True

    def search_driver_vehicles(self, search_term: str):
        query = """
        SELECT dv.DriverId, dv.DriverName, dv.LicenseNumber, dv.ContactNumber,
               dv.LicensePlateNumber, dv.VehicleType, dv.Capacity, u.UnitName, dv.ModifiedDate
        FROM inventory.DriverVehicle dv
        LEFT JOIN inventory.Unit u ON dv.UnitId = u.UnitId
        WHERE dv.IsDeleted = 0 AND (dv.DriverName LIKE ? OR dv.LicensePlateNumber LIKE ? OR dv.LicenseNumber LIKE ?)
        ORDER BY dv.DriverName
        """
        search_param = f"%{search_term}%"
        results = self.execute_query(query, params=(search_param, search_param, search_param))
        if results is not None:
            self.driver_vehicles = results
            self.data_updated.emit()
        else:
            logger.error("Failed to search driver vehicles")
            self.error_occurred.emit("Failed to search driver vehicles")

    def get_units(self) -> List[Dict[str, Any]]:
        query = "SELECT UnitId, UnitName FROM inventory.Unit WHERE IsDeleted = 0"
        return self.execute_query(query) or []

vehicle_module = VehicleModule()