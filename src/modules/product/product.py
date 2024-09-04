from PySide6.QtCore import QObject, Signal, Slot
from .server import server_module
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ProductModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.products: List[Dict[str, Any]] = []
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
                self.fetch_products()
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
                logger.info("ProductModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.products = []

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

    def fetch_products(self):
        query = """
        SELECT 
            p.ProductId, p.ProductCode, p.ProductName, p.Description, p.Density, p.State,
            p.CurrentReserve, u.UnitName, s.StorageTankName
        FROM inventory.ActiveProduct p
        LEFT JOIN inventory.ActiveUnit u ON p.UnitId = u.UnitId
        LEFT JOIN inventory.ActiveStorageTank s ON p.ProductId = s.ProductId
        ORDER BY p.ProductName
        """
        results = self.execute_query(query)
        if results is not None:
            self.products = results
            self.data_updated.emit()
        else:
            logger.error("Failed to fetch products")
            self.error_occurred.emit("Failed to fetch products")

    def get_product_details(self, product_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if product_id is None:
            logger.error("get_product_details called with None product_id")
            return None

        query = """
        SELECT 
            p.ProductId, p.ProductCode, p.ProductName, p.Description, p.Density, p.State,
            p.CurrentReserve, p.UnitId, s.StorageTankId, s.StorageTankName
        FROM inventory.ActiveProduct p
        LEFT JOIN inventory.ActiveStorageTank s ON p.ProductId = s.ProductId
        WHERE p.ProductId = ?
        """
        results = self.execute_query(query, params=(product_id,))
        return results[0] if results and isinstance(results, list) else None

    def add_product(self, product_data: Dict[str, Any]) -> bool:
        query = """
        INSERT INTO inventory.Product 
        (ProductCode, ProductName, Description, Density, State, CurrentReserve, UnitId)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            product_data['ProductCode'], product_data['ProductName'], product_data['Description'],
            product_data['Density'], product_data['State'], product_data['CurrentReserve'],
            product_data['UnitId']
        )
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error("Failed to add product")
            return False
        return True

    def update_product(self, product_data: Dict[str, Any]) -> bool:
        if not self.connection:
            logger.error("No active database connection")
            self.error_occurred.emit("No active database connection")
            return False

        try:
            cursor = self.connection.cursor()
            
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            query = """
            UPDATE inventory.Product
            SET ProductCode=?, ProductName=?, Description=?, Density=?, State=?, 
                CurrentReserve=?, UnitId=?, LastModifiedDate=GETDATE()
            WHERE ProductId=?
            """
            params = (
                product_data['ProductCode'], product_data['ProductName'], product_data['Description'],
                product_data['Density'], product_data['State'], product_data['CurrentReserve'],
                product_data['UnitId'], product_data['ProductId']
            )
            cursor.execute(query, params)
            
            if cursor.rowcount == 0:
                raise Exception("Failed to update product in the Product table")
            
            storage_tank_query = """
            UPDATE inventory.StorageTank
            SET ProductId = CASE WHEN ? IS NULL THEN NULL ELSE ? END
            WHERE StorageTankId = ? OR ProductId = ?
            """
            storage_tank_params = (product_data['StorageTankId'], product_data['ProductId'], 
                                product_data['StorageTankId'], product_data['ProductId'])
            cursor.execute(storage_tank_query, storage_tank_params)
            
            # Commit transaction
            self.connection.commit()
            logger.info(f"Product {product_data['ProductId']} updated successfully")
            return True
        except Exception as e:
            # Rollback transaction
            self.connection.rollback()
            logger.exception(f"Error updating product: {e}")
            self.error_occurred.emit(f"Error updating product: {str(e)}")
            return False
        finally:
            cursor.close()

    def delete_product(self, product_id: str) -> bool:
        query = """
        UPDATE inventory.Product
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE ProductId = ?
        """
        result = self.execute_query(query, params=(product_id,), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to delete product with ID {product_id}")
            return False
        return True

    def search_products(self, search_term: str):
        query = """
        SELECT 
            p.ProductId, p.ProductCode, p.ProductName, p.Description, p.Density, p.State,
            p.CurrentReserve, u.UnitName, s.StorageTankName
        FROM inventory.ActiveProduct p
        LEFT JOIN inventory.ActiveUnit u ON p.UnitId = u.UnitId
        LEFT JOIN inventory.ActiveStorageTank s ON p.ProductId = s.ProductId
        WHERE p.ProductCode LIKE ? OR p.ProductName LIKE ?
        ORDER BY p.ProductName
        """
        search_param = f"%{search_term}%"
        results = self.execute_query(query, params=(search_param, search_param))
        if results is not None:
            self.products = results
            self.data_updated.emit()
        else:
            logger.error("Failed to search products")
            self.error_occurred.emit("Failed to search products")

    def get_units(self) -> List[Dict[str, Any]]:
        query = "SELECT UnitId, UnitName FROM inventory.ActiveUnit"
        return self.execute_query(query) or []

    def get_storage_tanks(self) -> List[Dict[str, Any]]:
        query = "SELECT StorageTankId, StorageTankName, ProductId FROM inventory.ActiveStorageTank"
        return self.execute_query(query) or []

product_module = ProductModule()