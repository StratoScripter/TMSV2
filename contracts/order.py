from PySide6.QtCore import QObject, Signal, Slot
from modules.product.server import server_module
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class OrderModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.orders: List[Dict[str, Any]] = []
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
                self.fetch_orders()
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
                logger.info("OrderModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.orders = []

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

    def fetch_orders(self):
        query = """
            SELECT o.OrderId, o.SellerId, o.BuyerId, o.ProductId, o.DriverId, o.VehicleId,
                o.LoadingArmId, o.StorageTankId, o.WeighbridgeId, o.PlannedQuantity,
                o.ActualQuantity, o.UnitId, o.InitialWeight, o.FinalWeight,
                o.CheckoutWeight, o.LoadingDate, o.LoadingTime, o.Status, o.Remarks,
                s.PartyName as SellerName, b.PartyName as BuyerName, p.ProductName,
                d.DriverName, d.LicensePlateNumber, la.LoadingArmName, st.StorageTankName,
                w.WeighbridgeName, u.UnitName
            FROM inventory.ActiveOrder o
            LEFT JOIN inventory.ActiveParty s ON o.SellerId = s.PartyId
            LEFT JOIN inventory.ActiveParty b ON o.BuyerId = b.PartyId
            LEFT JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
            LEFT JOIN inventory.ActiveDriverVehicle d ON o.DriverId = d.DriverId
            LEFT JOIN inventory.ActiveLoadingArm la ON o.LoadingArmId = la.LoadingArmId
            LEFT JOIN inventory.ActiveStorageTank st ON o.StorageTankId = st.StorageTankId
            LEFT JOIN inventory.ActiveWeighbridge w ON o.WeighbridgeId = w.WeighbridgeId
            LEFT JOIN inventory.ActiveUnit u ON o.UnitId = u.UnitId
        """
        results = self.execute_query(query)
        if results is not None:
            self.orders = results
            self.data_updated.emit()
        else:
            logger.error("Failed to fetch orders")
            self.error_occurred.emit("Failed to fetch orders")

    def get_order_details(self, order_id: int) -> Optional[Dict[str, Any]]:
        query = """
            SELECT o.*, s.PartyName as SellerName, b.PartyName as BuyerName, p.ProductName,
                   d.DriverName, d.LicensePlateNumber, la.LoadingArmName, st.StorageTankName,
                   w.WeighbridgeName, u.UnitName
            FROM inventory.ActiveOrder o
            LEFT JOIN inventory.ActiveParty s ON o.SellerId = s.PartyId
            LEFT JOIN inventory.ActiveParty b ON o.BuyerId = b.PartyId
            LEFT JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
            LEFT JOIN inventory.ActiveDriverVehicle d ON o.DriverId = d.DriverId
            LEFT JOIN inventory.ActiveLoadingArm la ON o.LoadingArmId = la.LoadingArmId
            LEFT JOIN inventory.ActiveStorageTank st ON o.StorageTankId = st.StorageTankId
            LEFT JOIN inventory.ActiveWeighbridge w ON o.WeighbridgeId = w.WeighbridgeId
            LEFT JOIN inventory.ActiveUnit u ON o.UnitId = u.UnitId
            WHERE o.OrderId = ?
        """
        result = self.execute_query(query, (order_id,))
        return result[0] if result else None

    def add_order(self, order: Dict[str, Any]) -> Tuple[bool, str, str]:
        query = """
            INSERT INTO inventory.[Order] 
            (SellerId, BuyerId, ProductId, DriverId, VehicleId, LoadingArmId, StorageTankId,
             WeighbridgeId, PlannedQuantity, ActualQuantity, UnitId, InitialWeight, FinalWeight,
             CheckoutWeight, LoadingDate, LoadingTime, Status, Remarks)
            OUTPUT INSERTED.OrderId
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (order['SellerId'], order['BuyerId'], order['ProductId'], order['DriverId'],
                  order['VehicleId'], order['LoadingArmId'], order['StorageTankId'],
                  order['WeighbridgeId'], order['PlannedQuantity'], order['ActualQuantity'],
                  order['UnitId'], order['InitialWeight'], order['FinalWeight'],
                  order['CheckoutWeight'], order['LoadingDate'], order['LoadingTime'],
                  order['Status'], order['Remarks'])
        result = self.execute_query(query, params)
        if result and len(result) > 0 and 'OrderId' in result[0]:
            order_id = result[0]['OrderId']
            logger.info(f"Added new order with ID: {order_id}")
            return True, str(order_id), "Order added successfully"
        logger.error("Failed to add order: No OrderId returned")
        return False, "", "Failed to add order"

    def update_order(self, order: Dict[str, Any]) -> Tuple[bool, str]:
        query = """
            UPDATE inventory.[Order]
            SET SellerId = ?, BuyerId = ?, ProductId = ?, 
                DriverId = ?, VehicleId = ?, LoadingArmId = ?, 
                StorageTankId = ?, WeighbridgeId = ?, 
                PlannedQuantity = ?, ActualQuantity = ?, 
                UnitId = ?, InitialWeight = ?, FinalWeight = ?,
                CheckoutWeight = ?, LoadingDate = ?, 
                LoadingTime = ?, Status = ?, Remarks = ?
            WHERE OrderId = ?
        """
        params = (order['SellerId'], order['BuyerId'], order['ProductId'], 
                  order['DriverId'], order['VehicleId'], order['LoadingArmId'], 
                  order['StorageTankId'], order['WeighbridgeId'], 
                  order['PlannedQuantity'], order['ActualQuantity'], 
                  order['UnitId'], order['InitialWeight'], order['FinalWeight'],
                  order['CheckoutWeight'], order['LoadingDate'], 
                  order['LoadingTime'], order['Status'], order['Remarks'],
                  order['OrderId'])
        result = self.execute_query(query, params, fetch=False)
        if result and result[0]['affected_rows'] > 0:
            logger.info(f"Updated order: {order['OrderId']}")
            return True, "Order updated successfully"
        logger.error(f"Failed to update order: {order['OrderId']}")
        return False, "Failed to update order"

    def delete_order(self, order_id: int) -> bool:
        query = """
            UPDATE inventory.[Order] 
            SET IsDeleted = 1, DeletedDate = GETDATE() 
            WHERE OrderId = ?
        """
        result = self.execute_query(query, (order_id,), fetch=False)
        if result and result[0]['affected_rows'] > 0:
            logger.info(f"Deleted order with ID: {order_id}")
            return True
        logger.error(f"Failed to delete order with ID: {order_id}")
        return False

    def search_orders(self, search_term: str) -> List[Dict[str, Any]]:
        query = """
            SELECT o.OrderId, o.SellerId, o.BuyerId, o.ProductId, o.DriverId, o.VehicleId,
                   o.LoadingArmId, o.StorageTankId, o.WeighbridgeId, o.PlannedQuantity,
                   o.ActualQuantity, o.UnitId, o.InitialWeight, o.FinalWeight,
                   o.CheckoutWeight, o.LoadingDate, o.LoadingTime, o.Status, o.Remarks,
                   s.PartyName as SellerName, b.PartyName as BuyerName, p.ProductName,
                   d.DriverName, d.LicensePlateNumber, la.LoadingArmName, st.StorageTankName,
                   w.WeighbridgeName, u.UnitName
            FROM inventory.ActiveOrder o
            LEFT JOIN inventory.ActiveParty s ON o.SellerId = s.PartyId
            LEFT JOIN inventory.ActiveParty b ON o.BuyerId = b.PartyId
            LEFT JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
            LEFT JOIN inventory.ActiveDriverVehicle d ON o.DriverId = d.DriverId
            LEFT JOIN inventory.ActiveLoadingArm la ON o.LoadingArmId = la.LoadingArmId
            LEFT JOIN inventory.ActiveStorageTank st ON o.StorageTankId = st.StorageTankId
            LEFT JOIN inventory.ActiveWeighbridge w ON o.WeighbridgeId = w.WeighbridgeId
            LEFT JOIN inventory.ActiveUnit u ON o.UnitId = u.UnitId
            WHERE CAST(o.OrderId AS NVARCHAR(50)) LIKE ? 
               OR s.PartyName LIKE ? 
               OR b.PartyName LIKE ? 
               OR p.ProductName LIKE ?
        """
        search_param = f"%{search_term}%"
        results = self.execute_query(query, (search_param, search_param, search_param, search_param))
        if results is not None:
            self.orders = results
            self.data_updated.emit()
        else:
            logger.error("Failed to search orders")
            self.error_occurred.emit("Failed to search orders")
        return self.orders

    def get_all_parties(self) -> List[Dict[str, Any]]:
        query = "SELECT PartyId, PartyName FROM inventory.ActiveParty ORDER BY PartyName"
        return self.execute_query(query) or []

    def get_all_products(self) -> List[Dict[str, Any]]:
        query = "SELECT ProductId, ProductName FROM inventory.ActiveProduct ORDER BY ProductName"
        return self.execute_query(query) or []

    def get_all_drivers(self) -> List[Dict[str, Any]]:
        query = "SELECT DriverId, DriverName FROM inventory.ActiveDriverVehicle ORDER BY DriverName"
        return self.execute_query(query) or []

    def get_all_vehicles(self) -> List[Dict[str, Any]]:
        query = "SELECT DriverId, LicensePlateNumber FROM inventory.ActiveDriverVehicle ORDER BY LicensePlateNumber"
        return self.execute_query(query) or []

    def get_all_loading_arms(self) -> List[Dict[str, Any]]:
        query = "SELECT LoadingArmId, LoadingArmName FROM inventory.ActiveLoadingArm ORDER BY LoadingArmName"
        return self.execute_query(query) or []

    def get_all_storage_tanks(self) -> List[Dict[str, Any]]:
        query = "SELECT StorageTankId, StorageTankName FROM inventory.ActiveStorageTank ORDER BY StorageTankName"
        return self.execute_query(query) or []

    def get_all_weighbridges(self) -> List[Dict[str, Any]]:
        query = "SELECT WeighbridgeId, WeighbridgeName FROM inventory.ActiveWeighbridge ORDER BY WeighbridgeName"
        return self.execute_query(query) or []

    def get_all_units(self) -> List[Dict[str, Any]]:
        query = "SELECT UnitId, UnitName FROM inventory.ActiveUnit ORDER BY UnitName"
        return self.execute_query(query) or []

order_module = OrderModule()