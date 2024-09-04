# storagetank.py

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from .server import server_module
from .modbus import modbus_module
from typing import List, Dict, Any, Optional, Union
import datetime
import logging

logger = logging.getLogger(__name__)

class StorageTankModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)
    real_time_update = Signal(dict)

    def __init__(self):
        super().__init__()
        self.storage_tanks = []
        self.connection = None
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.fetch_storage_tanks)
        server_module.connection_status_changed.connect(self.on_connection_status_changed)
        self.real_time_timer = QTimer()
        self.real_time_timer.timeout.connect(self.fetch_real_time_data)
        self.modbus_module = modbus_module

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
                self.fetch_storage_tanks()
                self.start_real_time_updates()
            else:
                logger.error(f"{self.__class__.__name__} failed to connect to database")
                self.error_occurred.emit("Failed to connect to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self.error_occurred.emit(f"Error connecting to database: {str(e)}")

    def disconnect_from_database(self):
        self.stop_refresh_timer()
        self.stop_real_time_updates()
        if self.connection:
            try:
                self.connection.close()
                logger.info("StorageTankModule disconnected from database")
            except Exception as e:
                logger.error(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.storage_tanks = []

    def execute_query(self, query: str, params: tuple = (), fetch: bool = True) -> Optional[Union[List[Dict[str, Any]], int]]:
        if not self.connection:
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
                    return cursor.rowcount if cursor.rowcount else 0
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            self.error_occurred.emit(f"Error executing query: {str(e)}")
            return None

    def start_refresh_timer(self):
        self.refresh_timer.start(300000)  # Refresh every 5 minutes

    def stop_refresh_timer(self):
        self.refresh_timer.stop()

    def start_real_time_updates(self):
        self.real_time_timer.start(10000)  # Fetch real-time data every 10 seconds

    def stop_real_time_updates(self):
        self.real_time_timer.stop()

    def fetch_storage_tanks(self):
        query = """
        SELECT 
            st.StorageTankId, st.StorageTankName, 
            p.ProductName, pa.PartyName AS OwnerName,
            st.TotalVolume, st.CurrentVolume, st.CurrentMass, st.CurrentTemperature,
            u.UnitName, st.LastReadingDateTime, st.Remarks
        FROM inventory.ActiveStorageTank st
        LEFT JOIN inventory.ActiveProduct p ON st.ProductId = p.ProductId
        LEFT JOIN inventory.ActiveParty pa ON st.OwnerId = pa.PartyId
        LEFT JOIN inventory.ActiveUnit u ON st.UnitId = u.UnitId
        ORDER BY st.StorageTankName
        """
        results = self.execute_query(query)
        if isinstance(results, list):
            self.storage_tanks = [
                {
                    'id': row['StorageTankId'],
                    'name': row['StorageTankName'],
                    'product_name': row['ProductName'],
                    'owner_name': row['OwnerName'],
                    'total_volume': row['TotalVolume'],
                    'current_volume': row['CurrentVolume'],
                    'current_mass': row['CurrentMass'],
                    'current_temperature': row['CurrentTemperature'],
                    'unit_name': row['UnitName'],
                    'last_reading_datetime': row['LastReadingDateTime'],
                    'remarks': row['Remarks']
                }
                for row in results
            ]
            self.data_updated.emit()
        else:
            self.error_occurred.emit("Failed to fetch storage tanks: No data returned")

    def fetch_real_time_data(self):
        try:
            real_time_data = {}
            for tank in self.storage_tanks:
                tank_id = tank['id']
                tank_data = self.get_tank_modbus_data(tank_id)
                if tank_data:
                    real_time_data[tank_id] = tank_data
                    self.update_database_with_modbus_data(tank_id, tank_data)
            
            self.real_time_update.emit(real_time_data)
        except Exception as e:
            logger.error(f"Error fetching real-time data: {e}")
            self.error_occurred.emit(f"Error fetching real-time data: {str(e)}")

    def get_tank_modbus_data(self, tank_id):
        try:
            query = """
            SELECT MappingId, SlaveAddress, RegisterAddress, MappedColumn
            FROM inventory.ActiveRegisterMapping
            WHERE MappedTable = 'StorageTank' AND MappedEntityId = ?
            """
            mappings = self.execute_query(query, params=(tank_id,))
            
            tank_data = {}
            for mapping in mappings:
                value = self.modbus_module.read_register(mapping['SlaveAddress'], mapping)
                if value is not None:
                    tank_data[mapping['MappedColumn']] = value
            
            return tank_data
        except Exception as e:
            logger.error(f"Error getting Modbus data for tank {tank_id}: {e}")
            return None

    def update_database_with_modbus_data(self, tank_id, tank_data):
        try:
            query = """
            UPDATE inventory.StorageTank
            SET CurrentVolume = ?, CurrentMass = ?, CurrentTemperature = ?, LastReadingDateTime = GETDATE()
            WHERE StorageTankId = ?
            """
            params = (
                tank_data.get('CurrentVolume'),
                tank_data.get('CurrentMass'),
                tank_data.get('CurrentTemperature'),
                tank_id
            )
            self.execute_query(query, params=params, fetch=False)
            logger.info(f"Updated database with Modbus data for tank {tank_id}")
        except Exception as e:
            logger.error(f"Error updating database with Modbus data for tank {tank_id}: {e}")

    def get_storage_tank_details(self, storage_tank_id):
        query = """
        SELECT 
            st.StorageTankId, st.StorageTankName, st.ProductId, st.OwnerId,
            st.TotalVolume, st.CurrentVolume, st.CurrentMass, st.CurrentTemperature, st.UnitId,
            st.LastReadingDateTime, st.Remarks,
            p.ProductName, pa.PartyName AS OwnerName, u.UnitName
        FROM inventory.ActiveStorageTank st
        LEFT JOIN inventory.ActiveProduct p ON st.ProductId = p.ProductId
        LEFT JOIN inventory.ActiveParty pa ON st.OwnerId = pa.PartyId
        LEFT JOIN inventory.ActiveUnit u ON st.UnitId = u.UnitId
        WHERE st.StorageTankId = ?
        """
        results = self.execute_query(query, params=(storage_tank_id,))
        if isinstance(results, list) and results:
            return results[0]
        return None

    def get_historical_data(self, storage_tank_id: int, start_date: datetime.datetime, end_date: datetime.datetime):
        query = """
        SELECT ReadingDateTime, Volume, Mass, Temperature
        FROM inventory.StorageTankReading
        WHERE StorageTankId = ? AND ReadingDateTime BETWEEN ? AND ?
        ORDER BY ReadingDateTime
        """
        params = (storage_tank_id, start_date, end_date)
        return self.execute_query(query, params=params)

    def add_storage_tank(self, name: str, product_id: int, owner_id: int, total_volume: float, current_volume: float, current_mass: float, current_temperature: float, unit_id: int, remarks: str) -> bool:
        query = """
        INSERT INTO inventory.StorageTank 
        (StorageTankName, ProductId, OwnerId, TotalVolume, CurrentVolume, CurrentMass, CurrentTemperature, UnitId, LastReadingDateTime, Remarks, IsDeleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, 0)
        """
        params = (name, product_id, owner_id, total_volume, current_volume, current_mass, current_temperature, unit_id, remarks)
        try:
            result = self.execute_query(query, params=params, fetch=False)
            if isinstance(result, int) and result > 0:
                self.fetch_storage_tanks()
                return True
        except Exception as e:
            if 'Violation of UNIQUE KEY constraint' in str(e):
                self.error_occurred.emit(f"A storage tank with the name '{name}' already exists.")
            else:
                self.error_occurred.emit(f"Error adding storage tank: {str(e)}")
        return False

    def update_storage_tank(self, storage_tank_id: int, name: str, product_id: int, owner_id: int, total_volume: float, current_volume: float, current_mass: float, current_temperature: float, unit_id: int, remarks: str) -> bool:
        query = """
        UPDATE inventory.StorageTank
        SET StorageTankName = ?, ProductId = ?, OwnerId = ?, TotalVolume = ?, CurrentVolume = ?, CurrentMass = ?, CurrentTemperature = ?, UnitId = ?, Remarks = ?, LastReadingDateTime = GETDATE()
        WHERE StorageTankId = ?
        """
        params = (name, product_id, owner_id, total_volume, current_volume, current_mass, current_temperature, unit_id, remarks, storage_tank_id)
        try:
            result = self.execute_query(query, params=params, fetch=False)
            if isinstance(result, int) and result > 0:
                self.fetch_storage_tanks()
                return True
        except Exception as e:
            if 'Violation of UNIQUE KEY constraint' in str(e):
                self.error_occurred.emit(f"Another storage tank with the name '{name}' already exists.")
            else:
                self.error_occurred.emit(f"Error updating storage tank: {str(e)}")
        return False

    def delete_storage_tank(self, storage_tank_id: int) -> bool:
        query = """
        UPDATE inventory.StorageTank
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE StorageTankId = ?
        """
        try:
            result = self.execute_query(query, params=(storage_tank_id,), fetch=False)
            if isinstance(result, int) and result > 0:
                self.fetch_storage_tanks()
                return True
        except Exception as e:
            self.error_occurred.emit(f"Error deleting storage tank: {str(e)}")
        return False

    def search_storage_tanks(self, search_term: str):
        query = """
        SELECT 
            st.StorageTankId, st.StorageTankName, 
            p.ProductName, pa.PartyName AS OwnerName,
            st.TotalVolume, st.CurrentVolume, st.CurrentMass, st.CurrentTemperature,
            u.UnitName, st.LastReadingDateTime, st.Remarks
        FROM inventory.ActiveStorageTank st
        LEFT JOIN inventory.ActiveProduct p ON st.ProductId = p.ProductId
        LEFT JOIN inventory.ActiveParty pa ON st.OwnerId = pa.PartyId
        LEFT JOIN inventory.ActiveUnit u ON st.UnitId = u.UnitId
        WHERE st.StorageTankName LIKE ? OR p.ProductName LIKE ? OR pa.PartyName LIKE ?
        ORDER BY st.StorageTankName
        """
        search_param = f"%{search_term}%"
        params = (search_param, search_param, search_param)
        results = self.execute_query(query, params=params)
        if isinstance(results, list):
            self.storage_tanks = [
                {
                    'id': row['StorageTankId'],
                    'name': row['StorageTankName'],
                    'product_name': row['ProductName'],
                    'owner_name': row['OwnerName'],
                    'total_volume': row['TotalVolume'],
                    'current_volume': row['CurrentVolume'],
                    'current_mass': row['CurrentMass'],
                    'current_temperature': row['CurrentTemperature'],
                    'unit_name': row['UnitName'],
                    'last_reading_datetime': row['LastReadingDateTime'],
                    'remarks': row['Remarks']
                }
                for row in results
            ]
            self.data_updated.emit()
        else:
            self.error_occurred.emit("Failed to search storage tanks")

    def get_products(self):
        query = "SELECT ProductId, ProductName FROM inventory.ActiveProduct"
        return self.execute_query(query)

    def get_owners(self):
        query = "SELECT PartyId, PartyName FROM inventory.ActiveParty"
        return self.execute_query(query)

    def get_units(self):
        query = "SELECT UnitId, UnitName FROM inventory.ActiveUnit"
        return self.execute_query(query)

storage_tank_module = StorageTankModule()