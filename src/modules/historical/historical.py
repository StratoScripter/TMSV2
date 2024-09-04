from PySide6.QtCore import QObject, Signal, Slot
from modules.product.server import server_module
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class HistoricalModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.historical_data: List[Dict[str, Any]] = []
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
                self.fetch_historical_data()
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
                logger.info("HistoricalModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.historical_data = []

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

    def get_all_historical_data(self) -> List[Dict[str, Any]]:
        query = """
        SELECT 
            h.HistoricalDataId, h.OrderId, h.ProductId, h.SellerId, h.BuyerId,
            h.Quantity, h.UnitId, h.DriverId, h.InitialWeight, h.FinalWeight, 
            h.LoadingArmId, h.TransactionDate, h.CreatedDate,
            p.ProductName, u.UnitName, dv.DriverName, dv.LicensePlateNumber,
            seller.PartyName as SellerName, buyer.PartyName as BuyerName,
            la.LoadingArmName
        FROM inventory.ActiveHistoricalData h
        LEFT JOIN inventory.ActiveProduct p ON h.ProductId = p.ProductId
        LEFT JOIN inventory.ActiveUnit u ON h.UnitId = u.UnitId
        LEFT JOIN inventory.ActiveDriverVehicle dv ON h.DriverId = dv.DriverId
        LEFT JOIN inventory.ActiveParty seller ON h.SellerId = seller.PartyId
        LEFT JOIN inventory.ActiveParty buyer ON h.BuyerId = buyer.PartyId
        LEFT JOIN inventory.ActiveLoadingArm la ON h.LoadingArmId = la.LoadingArmId
        ORDER BY h.TransactionDate DESC
        """
        results = self.execute_query(query)
        if results is not None:
            self.historical_data = results
            self.data_updated.emit()
            return results
        else:
            logger.error("Failed to fetch historical data")
            self.error_occurred.emit("Failed to fetch historical data")
            return []

    def fetch_historical_data(self):
        self.get_all_historical_data()

    def search_historical_data(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, 
                               loading_arm: Optional[str] = None, product: Optional[str] = None, 
                               seller: Optional[str] = None, buyer: Optional[str] = None, 
                               license_plate: Optional[str] = None, driver: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
        SELECT 
            h.HistoricalDataId, h.OrderId, h.ProductId, h.SellerId, h.BuyerId,
            h.Quantity, h.UnitId, h.DriverId, h.InitialWeight, h.FinalWeight, 
            h.LoadingArmId, h.TransactionDate, h.CreatedDate,
            p.ProductName, u.UnitName, dv.DriverName, dv.LicensePlateNumber,
            seller.PartyName as SellerName, buyer.PartyName as BuyerName,
            la.LoadingArmName
        FROM inventory.ActiveHistoricalData h
        LEFT JOIN inventory.ActiveProduct p ON h.ProductId = p.ProductId
        LEFT JOIN inventory.ActiveUnit u ON h.UnitId = u.UnitId
        LEFT JOIN inventory.ActiveDriverVehicle dv ON h.DriverId = dv.DriverId
        LEFT JOIN inventory.ActiveParty seller ON h.SellerId = seller.PartyId
        LEFT JOIN inventory.ActiveParty buyer ON h.BuyerId = buyer.PartyId
        LEFT JOIN inventory.ActiveLoadingArm la ON h.LoadingArmId = la.LoadingArmId
        WHERE 1=1
        """
        params = []

        if start_time:
            query += " AND h.TransactionDate >= ?"
            params.append(start_time)
        if end_time:
            query += " AND h.TransactionDate <= ?"
            params.append(end_time)
        if loading_arm:
            query += " AND la.LoadingArmName LIKE ?"
            params.append(f"%{loading_arm}%")
        if product:
            query += " AND p.ProductName LIKE ?"
            params.append(f"%{product}%")
        if seller:
            query += " AND seller.PartyName LIKE ?"
            params.append(f"%{seller}%")
        if buyer:
            query += " AND buyer.PartyName LIKE ?"
            params.append(f"%{buyer}%")
        if license_plate:
            query += " AND dv.LicensePlateNumber LIKE ?"
            params.append(f"%{license_plate}%")
        if driver:
            query += " AND dv.DriverName LIKE ?"
            params.append(f"%{driver}%")

        query += " ORDER BY h.TransactionDate DESC"

        results = self.execute_query(query, tuple(params))
        if results is not None:
            self.historical_data = results
            self.data_updated.emit()
            logger.info(f"Found {len(results)} historical data records")
            return results
        else:
            logger.error("Failed to search historical data")
            self.error_occurred.emit("Failed to search historical data")
            return []
historical_module = HistoricalModule()