# weighbridge.py

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QDate
from .server import server_module
from .modbus import modbus_module
from typing import List, Dict, Any, Optional
import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WeighbridgeModule(QObject):
    """
    Manages weighbridge operations and data handling.
    """
    realtime_data_updated = Signal(list)
    error_occurred = Signal(str)
    weighing_updated = Signal(dict)
    current_weight_updated = Signal(int, float)

    def __init__(self):
        super().__init__()
        self.weighbridges = []
        self.connection = None
        self.refresh_timer = QTimer()
        server_module.connection_status_changed.connect(self.on_connection_status_changed)
        self.current_weights = {}
        self.active_weighings = {}
        self.modbus_module = modbus_module
        self.modbus_module.current_weight_updated.connect(self.on_current_weight_updated)

    @Slot(bool, str)
    def on_connection_status_changed(self, is_connected: bool, message: str):
        """
        Handle changes in database connection status.
        """
        if is_connected:
            self.connect_to_database()
        else:
            self.disconnect_from_database()

    def connect_to_database(self):
        """
        Establish a connection to the database.
        """
        try:
            self.connection = server_module.get_module_connection(self.__class__.__name__)
            if self.connection:
                logger.info(f"{self.__class__.__name__} connected to database")
                self.fetch_weighbridges()
            else:
                raise ConnectionError("Failed to connect to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self.error_occurred.emit(f"Database connection error: {str(e)}")
            self.connection = None

    def disconnect_from_database(self):
        """
        Close the database connection.
        """
        if self.connection:
            try:
                self.connection.close()
                logger.info("WeighbridgeModule disconnected from database")
            except Exception as e:
                logger.error(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.weighbridges = []

    def execute_query(self, query: str, params: tuple = (), fetch: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a SQL query and return the results.
        """
        if not self.connection:
            raise ConnectionError("No active database connection")

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
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            if self.connection:
                self.connection.rollback()
            raise

    def fetch_weighbridges(self):
        """
        Fetch weighbridge data from the database.
        """
        query = """
        SELECT 
            WeighbridgeId, WeighbridgeCode, WeighbridgeName, IsActive
        FROM inventory.ActiveWeighbridge
        ORDER BY WeighbridgeId
        """
        try:
            results = self.execute_query(query)
            if results is not None:
                self.weighbridges = [
                    {
                        'id': row.get('WeighbridgeId'),
                        'name': row.get('WeighbridgeName', ''),
                        'code': row.get('WeighbridgeCode', ''),
                        'is_active': row.get('IsActive', False),
                        'current_weight': 0,
                        'tare_weight': None,
                        'gross_weight': None
                    }
                    for row in results
                ]
            else:
                self.weighbridges = []
            self.realtime_data_updated.emit(self.weighbridges)
        except Exception as e:
            logger.error(f"Failed to fetch weighbridge data: {e}")
            self.error_occurred.emit(f"Failed to fetch weighbridge data: {str(e)}")

    @Slot(int, float)
    def on_current_weight_updated(self, weighbridge_id: int, weight: float):
        """
        Handle updates to the current weight of a weighbridge.
        """
        for weighbridge in self.weighbridges:
            if weighbridge['id'] == weighbridge_id:
                weighbridge['current_weight'] = weight
                break
        self.current_weights[weighbridge_id] = weight
        self.current_weight_updated.emit(weighbridge_id, weight)
        self.update_active_weighing(weighbridge_id, weight)
        self.realtime_data_updated.emit(self.weighbridges)

    def update_active_weighing(self, weighbridge_id: int, weight: float):
        """
        Update the weight for an active weighing process.
        """
        if weighbridge_id in self.active_weighings:
            weighing = self.active_weighings[weighbridge_id]
            weighing['current_weight'] = weight
            self.weighing_updated.emit(weighing)

    def get_drivers(self) -> List[Dict[str, Any]]:
        query = """
        SELECT DISTINCT DriverId, DriverName, LicensePlateNumber
        FROM inventory.ActiveDriverVehicle
        """
        result = self.execute_query(query)
        if result is None:
            logger.error("Failed to fetch drivers")
            return []
        return result

    def get_products(self) -> List[Dict[str, Any]]:
        query = "SELECT ProductId, ProductName FROM inventory.ActiveProduct"
        return self.execute_query(query) or []

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        query = """
        SELECT o.OrderId, o.ProductId, p.ProductName, o.Status,
            COALESCE(o.PlannedQuantity, 0) AS PlannedQuantity
        FROM inventory.ActiveOrder o
        JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
        WHERE o.Status IN ('Pending', 'Ready', 'InProgress')
        ORDER BY o.OrderId DESC
        """
        logger.info(f"Executing query: {query}")
        results = self.execute_query(query)
        if results is None:
            logger.error("Failed to fetch orders")
            return []
        
        logger.info(f"Fetched {len(results)} orders")
        for order in results:
            logger.info(f"Order: {order}")
        
        # Log order status distribution
        status_query = """
        SELECT Status, COUNT(*) as count
        FROM inventory.ActiveOrder
        GROUP BY Status
        """
        status_results = self.execute_query(status_query)
        logger.info("Order status distribution:")
        if status_results is not None:
            for status in status_results:
                logger.info(f"  {status['Status']}: {status['count']}")
        
        return results

    def start_new_weighing(self, weighbridge_id: int, order_id: int, driver_id: int, vehicle_license: str):
        if not self.connection:
            logger.error("No active database connection")
            self.error_occurred.emit("No active database connection. Please reconnect to the database.")
            return False

        try:
            with self.connection.cursor() as cursor:
                # Check if the order exists and is available for weighing
                check_query = """
                SELECT OrderId, ProductId, Status, PlannedQuantity
                FROM inventory.ActiveOrder
                WHERE OrderId = ? AND Status IN ('Pending', 'Ready', 'InProgress')
                """
                cursor.execute(check_query, (order_id,))
                order_info = cursor.fetchone()

                if not order_info:
                    logger.error(f"Order {order_id} not found or not available for weighing")
                    self.error_occurred.emit(f"Order {order_id} not found or not available for weighing")
                    return False

                # Update the order with weighing information
                update_query = """
                UPDATE inventory.[Order]
                SET WeighbridgeId = ?, DriverId = ?, Status = 'InProgress', LoadingDate = GETDATE()
                WHERE OrderId = ?
                """
                cursor.execute(update_query, (weighbridge_id, driver_id, order_id))

                if cursor.rowcount == 1:
                    self.active_weighings[weighbridge_id] = {
                        'order_id': order_id,
                        'weighbridge_id': weighbridge_id,
                        'driver_id': driver_id,
                        'vehicle_license': vehicle_license,
                        'product_id': order_info.ProductId,
                        'planned_quantity': order_info.PlannedQuantity,
                        'status': 'InProgress',
                        'current_weight': self.current_weights.get(weighbridge_id, 0)
                    }
                    self.connection.commit()
                    self.weighing_updated.emit(self.active_weighings[weighbridge_id])
                    logger.info(f"Weighing started for Order ID: {order_id}")
                    return True
                else:
                    self.connection.rollback()
                    logger.error(f"Failed to update Order {order_id} for weighing")
                    self.error_occurred.emit(f"Failed to update Order {order_id} for weighing")
                    return False

        except Exception as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"Error starting weighing for Order {order_id}: {str(e)}")
            self.error_occurred.emit(f"Failed to start weighing for Order {order_id}: {str(e)}")
            return False

    def set_tare_weight(self, weighbridge_id: int):
        if weighbridge_id not in self.active_weighings:
            logger.error(f"No active weighing for weighbridge {weighbridge_id}")
            self.error_occurred.emit(f"No active weighing for weighbridge {weighbridge_id}")
            return False

        current_weight = self.current_weights.get(weighbridge_id)
        if current_weight is None:
            logger.error(f"No current weight reading available for weighbridge {weighbridge_id}")
            self.error_occurred.emit(f"No current weight reading available for weighbridge {weighbridge_id}")
            return False

        self.active_weighings[weighbridge_id]['tare_weight'] = current_weight
        self.weighing_updated.emit(self.active_weighings[weighbridge_id])
        
        for weighbridge in self.weighbridges:
            if weighbridge['id'] == weighbridge_id:
                weighbridge['tare_weight'] = current_weight
                break
        
        logger.info(f"Tare weight set for weighbridge {weighbridge_id}: {current_weight}")
        self.realtime_data_updated.emit(self.weighbridges)
        return True

    def set_gross_weight(self, weighbridge_id: int):
        if weighbridge_id not in self.active_weighings:
            logger.error(f"No active weighing for weighbridge {weighbridge_id}")
            self.error_occurred.emit(f"No active weighing for weighbridge {weighbridge_id}")
            return False

        current_weight = self.current_weights.get(weighbridge_id)
        if current_weight is None:
            logger.error(f"No current weight reading available for weighbridge {weighbridge_id}")
            self.error_occurred.emit(f"No current weight reading available for weighbridge {weighbridge_id}")
            return False

        weighing = self.active_weighings[weighbridge_id]
        weighing['gross_weight'] = current_weight
        weighing['net_weight'] = current_weight - weighing['tare_weight']
        weighing['status'] = 'Completed'

        # Store the completed weighing in the database
        if self.store_completed_weighing(weighing):
            self.weighing_updated.emit(weighing)
            del self.active_weighings[weighbridge_id]
            
            for weighbridge in self.weighbridges:
                if weighbridge['id'] == weighbridge_id:
                    weighbridge['gross_weight'] = current_weight
                    break
            
            logger.info(f"Gross weight set for weighbridge {weighbridge_id}: {current_weight}")
            self.realtime_data_updated.emit(self.weighbridges)
            return True
        else:
            logger.error(f"Failed to store completed weighing for weighbridge {weighbridge_id}")
            self.error_occurred.emit(f"Failed to store completed weighing for weighbridge {weighbridge_id}")
            return False

    def store_completed_weighing(self, weighing):
        """
        Store the completed weighing data in the database.
        """
        query = """
        UPDATE inventory.[Order] 
        SET WeighbridgeId = ?, 
            DriverId = ?, 
            InitialWeight = ?, 
            FinalWeight = ?, 
            ActualQuantity = ?,
            Status = 'Completed', 
            LoadingDate = CAST(GETDATE() AS DATE), 
            LoadingTime = CAST(GETDATE() AS TIME)
        WHERE OrderId = ?
        """
        params = (
            weighing['weighbridge_id'],
            weighing['driver_id'],
            weighing['tare_weight'],
            weighing['gross_weight'],
            weighing['net_weight'],
            weighing['order_id']
        )
        try:
            result = self.execute_query(query, params=params, fetch=False)
            if result and result[0]['affected_rows'] == 1:
                logger.info(f"Successfully updated Order {weighing['order_id']} with completed weighing data")
                return True
            else:
                raise ValueError(f"Failed to update Order {weighing['order_id']} with completed weighing data")
        except Exception as e:
            logger.error(f"Error storing completed weighing: {e}")
            raise

    def cancel_weighing(self, weighbridge_id: int):
        if weighbridge_id not in self.active_weighings:
            self.error_occurred.emit("No active weighing to cancel")
            return False

        del self.active_weighings[weighbridge_id]
        
        for weighbridge in self.weighbridges:
            if weighbridge['id'] == weighbridge_id:
                weighbridge['tare_weight'] = None
                weighbridge['gross_weight'] = None
                break
        
        self.realtime_data_updated.emit(self.weighbridges)
        return True

    def get_historical_weighbridge_data(self, start_date: QDate, end_date: QDate, product_filter: str = "", weighbridge_filter: str = ""):
        start_date_py = start_date.toPython()
        end_date_py = end_date.toPython()
        query = """
        SELECT 
            w.WeighbridgeId,
            w.WeighbridgeCode, 
            w.WeighbridgeName,
            w.GrossWeight,
            w.TareWeight,
            w.NetWeight,
            w.LastReadingDateTime,
            d.DriverName, 
            d.LicensePlateNumber,
            p.ProductName
        FROM inventory.ActiveWeighbridge w
        LEFT JOIN inventory.ActiveDriverVehicle d ON w.DriverId = d.DriverId
        LEFT JOIN inventory.ActiveProduct p ON w.ProductId = p.ProductId
        WHERE w.LastReadingDateTime BETWEEN ? AND ?
        AND (? = '' OR p.ProductName LIKE ?)
        AND (? = '' OR w.WeighbridgeName LIKE ?)
        ORDER BY w.LastReadingDateTime DESC
        """
        product_param = f"%{product_filter}%" if product_filter else ""
        weighbridge_param = f"%{weighbridge_filter}%" if weighbridge_filter else ""
        
        # Use the converted datetime.date objects
        params = (start_date_py, end_date_py, product_filter, product_param, weighbridge_filter, weighbridge_param)
        
        logger.info(f"Executing historical weighbridge data query with params: {params}")
        results = self.execute_query(query, params=params)
        
        if results is None:
            logger.error("Failed to fetch historical weighbridge data")
            return []
        
        logger.info(f"Fetched {len(results)} historical weighbridge records")
        return results

    def get_weighbridge_details(self, weighbridge_id: int) -> Optional[Dict[str, Any]]:
        query = """
        SELECT w.*, d.DriverName, d.LicensePlateNumber
        FROM inventory.ActiveWeighbridge w
        LEFT JOIN inventory.ActiveDriverVehicle d ON w.DriverId = d.DriverId
        WHERE w.WeighbridgeId = ?
        """
        result = self.execute_query(query, params=(weighbridge_id,))
        return result[0] if result and len(result) > 0 else None

    def get_weighing_records(self, start_date: QDate, end_date: QDate, product_filter: str = "", weighbridge_filter: str = ""):
        start_date_py = start_date.toPython()
        end_date_py = end_date.toPython()
        query = """
        SELECT 
            o.OrderId,
            o.LoadingDate,
            o.LoadingTime,
            w.WeighbridgeName,
            d.DriverName,
            d.LicensePlateNumber,
            p.ProductName,
            o.InitialWeight,
            o.FinalWeight,
            o.CheckoutWeight,
            o.Status
        FROM inventory.ActiveOrder o
        JOIN inventory.ActiveWeighbridge w ON o.WeighbridgeId = w.WeighbridgeId
        JOIN inventory.ActiveDriverVehicle d ON o.DriverId = d.DriverId
        JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
        WHERE o.LoadingDate BETWEEN ? AND ?
        AND o.WeighbridgeId IS NOT NULL
        AND (? = '' OR p.ProductName LIKE ?)
        AND (? = '' OR w.WeighbridgeName LIKE ?)
        ORDER BY o.LoadingDate DESC, o.LoadingTime DESC
        """
        product_param = f"%{product_filter}%" if product_filter else ""
        weighbridge_param = f"%{weighbridge_filter}%" if weighbridge_filter else ""
        params = (start_date_py, end_date_py, product_filter, product_param, weighbridge_filter, weighbridge_param)
        
        logger.info(f"Executing weighing records query with params: {params}")
        results = self.execute_query(query, params=params)
        
        if results is None:
            logger.error("Failed to fetch weighing records")
            return []
        
        logger.info(f"Fetched {len(results)} weighing records")
        return results

    def get_weighing_details(self, order_id: int) -> Optional[Dict[str, Any]]:
        query = """
        SELECT 
            o.*,
            w.WeighbridgeName,
            d.DriverName,
            d.LicensePlateNumber,
            p.ProductName
        FROM inventory.ActiveOrder o
        JOIN inventory.ActiveWeighbridge w ON o.WeighbridgeId = w.WeighbridgeId
        JOIN inventory.ActiveDriverVehicle d ON o.DriverId = d.DriverId
        JOIN inventory.ActiveProduct p ON o.ProductId = p.ProductId
        WHERE o.OrderId = ?
        """
        result = self.execute_query(query, params=(order_id,))
        return result[0] if result and len(result) > 0 else None

weighbridge_module = WeighbridgeModule()
