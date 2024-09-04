# loadingarm.py

from PySide6.QtCore import QObject, Signal, Slot, QTimer
from .server import server_module
from .modbus import modbus_module
from typing import List, Dict, Any, Optional, Union
import datetime
import logging

logger = logging.getLogger(__name__)

class LoadingArmModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)
    realtime_data_updated = Signal(list)

    def __init__(self):
        super().__init__()
        self.loading_arms = []
        self.connection = None
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.fetch_realtime_loading_arms)
        server_module.connection_status_changed.connect(self.on_connection_status_changed)
        modbus_module.data_updated.connect(self.on_modbus_data_updated)

    @Slot(bool, str)
    def on_connection_status_changed(self, is_connected, message):
        if is_connected:
            self.connect_to_database()
        else:
            self.disconnect_from_database()

    @Slot(dict)
    def on_modbus_data_updated(self, data):
        self.update_loading_arms_from_modbus(data)

    def update_loading_arms_from_modbus(self, modbus_data):
        for arm in self.loading_arms:
            arm_id = arm['id']
            if (arm_id, 'FlowRate') in modbus_data:
                arm['flow_rate'] = modbus_data[(arm_id, 'FlowRate')]
                arm['last_reading_datetime'] = datetime.datetime.now()
                arm['is_active'] = True
            else:
                arm['is_active'] = False

        self.realtime_data_updated.emit(self.loading_arms)

    def connect_to_database(self):
        try:
            self.connection = server_module.get_module_connection(self.__class__.__name__)
            if self.connection:
                logger.info(f"{self.__class__.__name__} connected to database")
                self.fetch_realtime_loading_arms()
                self.start_refresh_timer()
            else:
                logger.error(f"{self.__class__.__name__} failed to connect to database")
                self.error_occurred.emit("Failed to connect to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self.error_occurred.emit(f"Error connecting to database: {str(e)}")

    def disconnect_from_database(self):
        self.stop_refresh_timer()
        if self.connection:
            try:
                self.connection.close()
                logger.info("LoadingArmModule disconnected from database")
            except Exception as e:
                logger.error(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.loading_arms = []

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
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def stop_refresh_timer(self):
        self.refresh_timer.stop()

    def fetch_realtime_loading_arms(self):
        query = """
        SELECT 
            la.LoadingArmId, la.LoadingArmName, la.LoadingArmCode,
            la.LoadingWeight, u.UnitName,
            COALESCE(rm.MappingId, 0) as MappingId
        FROM inventory.ActiveLoadingArm la
        LEFT JOIN inventory.ActiveUnit u ON la.UnitId = u.UnitId
        LEFT JOIN inventory.RegisterMapping rm ON rm.MappedTable = 'LoadingArm' AND rm.MappedEntityId = la.LoadingArmId AND rm.MappedColumn = 'FlowRate'
        ORDER BY la.LoadingArmId
        """
        results = self.execute_query(query)
        if isinstance(results, list):
            self.loading_arms = [
                {
                    'id': row['LoadingArmId'],
                    'name': row['LoadingArmName'],
                    'code': row['LoadingArmCode'],
                    'flow_rate': 0,  # Will be updated by Modbus data
                    'is_active': False,  # Will be updated by Modbus data
                    'loading_weight': row['LoadingWeight'],
                    'unit_name': row['UnitName'],
                    'last_reading_datetime': None,  # Will be updated by Modbus data
                    'mapping_id': row['MappingId']
                }
                for row in results
            ]
            self.realtime_data_updated.emit(self.loading_arms)
            self.data_updated.emit()
        else:
            self.error_occurred.emit("Failed to fetch real-time loading arm data")

    def get_historical_loading_arm_data(self, start_date, end_date):
        query = """
        SELECT 
            la.LoadingArmCode, la.LoadingArmName,
            s.PartyName AS SellerName, b.PartyName AS BuyerName,
            p.ProductName, o.ActualQuantity AS LoadingWeight, u.UnitName,
            o.LoadingDate, o.LoadingTime
        FROM inventory.ActiveOrder o
        JOIN inventory.ActiveLoadingArm la ON o.LoadingArmId = la.LoadingArmId
        JOIN inventory.ActiveParty s ON o.SellerId = s.PartyId
        JOIN inventory.ActiveParty b ON o.BuyerId = b.PartyId
        JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
        JOIN inventory.ActiveUnit u ON o.UnitId = u.UnitId
        WHERE o.LoadingDate BETWEEN ? AND ?
        ORDER BY o.LoadingDate DESC, o.LoadingTime DESC
        """
        return self.execute_query(query, params=(start_date, end_date))

    def get_loading_arm_details(self, loading_arm_id):
        query = """
        SELECT 
            la.LoadingArmId, la.LoadingArmCode, la.LoadingArmName, la.LoadingWeight, la.UnitId,
            la.LastReadingDateTime, la.Remarks, u.UnitName
        FROM inventory.ActiveLoadingArm la
        LEFT JOIN inventory.ActiveUnit u ON la.UnitId = u.UnitId
        WHERE la.LoadingArmId = ?
        """
        results = self.execute_query(query, params=(loading_arm_id,))
        if isinstance(results, list) and results:
            return results[0]
        return None

    def get_units(self):
        query = "SELECT UnitId, UnitName FROM inventory.ActiveUnit"
        return self.execute_query(query)

    def add_loading_arm(self, code: str, name: str, loading_weight: float, unit_id: int, remarks: str) -> bool:
        query = """
        INSERT INTO inventory.LoadingArm (LoadingArmCode, LoadingArmName, LoadingWeight, UnitId, Remarks)
        VALUES (?, ?, ?, ?, ?);
        """
        params = (code, name, loading_weight, unit_id, remarks)
        result = self.execute_query(query, params=params, fetch=False)
        if isinstance(result, int) and result > 0:
            self.fetch_realtime_loading_arms()  # Refresh the data after successful addition
            return True
        return False

    def update_loading_arm(self, loading_arm_id: int, code: str, name: str, loading_weight: float, unit_id: int, remarks: str) -> bool:
        query = """
        UPDATE inventory.LoadingArm
        SET LoadingArmCode = ?, LoadingArmName = ?, LoadingWeight = ?, UnitId = ?, Remarks = ?
        WHERE LoadingArmId = ?;
        """
        params = (code, name, loading_weight, unit_id, remarks, loading_arm_id)
        result = self.execute_query(query, params=params, fetch=False)
        if isinstance(result, int) and result > 0:
            self.fetch_realtime_loading_arms()  # Refresh the data after successful update
            return True
        return False

    def delete_loading_arm(self, loading_arm_id):
        query = """
        UPDATE inventory.LoadingArm
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE LoadingArmId = ?;
        """
        result = self.execute_query(query, params=(loading_arm_id,), fetch=False)
        if isinstance(result, int) and result > 0:
            self.fetch_realtime_loading_arms()  # Refresh the data after successful deletion
            return True
        return False

    def search_loading_arms(self, search_term):
        query = """
        SELECT 
            la.LoadingArmId, la.LoadingArmCode, la.LoadingArmName, la.LoadingWeight,
            u.UnitName, la.LastReadingDateTime, la.Remarks
        FROM inventory.ActiveLoadingArm la
        LEFT JOIN inventory.ActiveUnit u ON la.UnitId = u.UnitId
        WHERE la.LoadingArmCode LIKE ? OR la.LoadingArmName LIKE ?
        ORDER BY la.LoadingArmId DESC
        """
        search_param = f"%{search_term}%"
        params = (search_param, search_param)
        results = self.execute_query(query, params=params)
        if isinstance(results, list):
            self.loading_arms = [
                {
                    'id': row['LoadingArmId'],
                    'code': row['LoadingArmCode'],
                    'name': row['LoadingArmName'],
                    'loading_weight': row['LoadingWeight'],
                    'unit_name': row['UnitName'],
                    'last_reading_date': row['LastReadingDateTime'],
                    'remarks': row['Remarks']
                }
                for row in results
            ]
            self.data_updated.emit()
        else:
            self.error_occurred.emit("Failed to search loading arms")

loading_arm_module = LoadingArmModule()