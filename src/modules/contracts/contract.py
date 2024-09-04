from PySide6.QtCore import QObject, Signal, Slot
from modules.product.server import server_module
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class ContractModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.contracts: List[Dict[str, Any]] = []
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
                self.fetch_contracts()
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
                logger.info("ContractModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.contracts = []

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

    def fetch_contracts(self):
        query = """
            SELECT c.ContractId, c.SellerId, c.BuyerId, p.ProductName, 
                   c.PlannedQuantity, u.UnitName, c.StartDate, c.EndDate, 
                   c.SignDate, c.Signer, c.Status, c.Remarks
            FROM inventory.ActiveContract c
            LEFT JOIN inventory.ActiveProduct p ON c.ProductId = p.ProductId
            LEFT JOIN inventory.ActiveUnit u ON c.UnitId = u.UnitId
        """
        results = self.execute_query(query)
        if results is not None:
            self.contracts = results
            self.data_updated.emit()
        else:
            logger.error("Failed to fetch contracts")
            self.error_occurred.emit("Failed to fetch contracts")
    
    def get_all_contracts(self) -> List[Dict[str, Any]]:
        try:
            query = """
                SELECT c.ContractId, s.PartyName as Seller, b.PartyName as Buyer, 
                       p.ProductName, c.PlannedQuantity, u.UnitName, c.StartDate, 
                       c.EndDate, c.SignDate, c.Signer, c.Status, c.Remarks
                FROM inventory.Contract c
                JOIN inventory.Party s ON c.SellerId = s.PartyId
                JOIN inventory.Party b ON c.BuyerId = b.PartyId
                JOIN inventory.Product p ON c.ProductId = p.ProductId
                JOIN inventory.Unit u ON c.UnitId = u.UnitId
                WHERE c.IsDeleted = 0
                ORDER BY c.ContractId
            """
            contracts = self.execute_query(query)
            if contracts is not None:
                logger.info(f"ContractModule - Get All Contracts - Success: Retrieved {len(contracts)} contracts")
            else:
                logger.error("ContractModule - Get All Contracts - Failed: Contracts is None")
                self.error_occurred.emit("Failed to retrieve contracts")
            return contracts or []
        except Exception as e:
            logger.error(f"Error fetching contracts: {e}")
            self.error_occurred.emit(f"Failed to retrieve contracts: {str(e)}")
            return []

    def get_all_parties(self) -> List[Dict[str, Any]]:
        query = "SELECT PartyId, PartyName FROM inventory.ActiveParty ORDER BY PartyName"
        return self.execute_query(query) or []

    def get_all_products(self) -> List[Dict[str, Any]]:
        query = "SELECT ProductId, ProductName FROM inventory.ActiveProduct ORDER BY ProductName"
        return self.execute_query(query) or []

    def get_all_units(self) -> List[Dict[str, Any]]:
        query = "SELECT UnitId, UnitName FROM inventory.ActiveUnit ORDER BY UnitName"
        return self.execute_query(query) or []

    def add_contract(self, contract: Dict[str, Any]) -> Tuple[bool, str, str]:
        query = """
            INSERT INTO inventory.Contract 
            (SellerId, BuyerId, ProductId, PlannedQuantity, UnitId, 
             StartDate, EndDate, SignDate, Signer, Status, Remarks, ModifiedDate, IsDeleted)
            OUTPUT INSERTED.ContractId
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 0)
        """
        params = (contract['SellerId'], contract['BuyerId'], contract['ProductId'],
                  contract['PlannedQuantity'], contract['UnitId'], contract['StartDate'],
                  contract['EndDate'], contract['SignDate'], contract['Signer'],
                  contract['Status'], contract['Remarks'])
        result = self.execute_query(query, params)
        if result and len(result) > 0 and 'ContractId' in result[0]:
            contract_id = result[0]['ContractId']
            logger.info(f"Added new contract with ID: {contract_id}")
            return True, str(contract_id), "Contract added successfully"
        logger.error("Failed to add contract: No ContractId returned")
        return False, "", "Failed to add contract"

    def get_contract(self, contract_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM inventory.ActiveContract WHERE ContractId = ?"
        result = self.execute_query(query, (contract_id,))
        return result[0] if result else None

    def update_contract(self, contract: Dict[str, Any]) -> Tuple[bool, str]:
        query = """
            UPDATE inventory.Contract 
            SET SellerId = ?, BuyerId = ?, ProductId = ?, 
                PlannedQuantity = ?, UnitId = ?, StartDate = ?, 
                EndDate = ?, SignDate = ?, Signer = ?, 
                Status = ?, Remarks = ?, ModifiedDate = GETDATE()
            WHERE ContractId = ? AND IsDeleted = 0
        """
        params = (contract['SellerId'], contract['BuyerId'], contract['ProductId'],
                  contract['PlannedQuantity'], contract['UnitId'], contract['StartDate'],
                  contract['EndDate'], contract['SignDate'], contract['Signer'],
                  contract['Status'], contract['Remarks'], contract['ContractId'])
        result = self.execute_query(query, params, fetch=False)
        if result and result[0]['affected_rows'] > 0:
            logger.info(f"Updated contract: {contract['ContractId']}")
            return True, "Contract updated successfully"
        logger.error(f"Failed to update contract: {contract['ContractId']}")
        return False, "Failed to update contract"

    def delete_contract(self, contract_id: int) -> bool:
        query = """
            UPDATE inventory.Contract 
            SET IsDeleted = 1, DeletedDate = GETDATE() 
            WHERE ContractId = ?
        """
        result = self.execute_query(query, (contract_id,), fetch=False)
        if result and result[0]['affected_rows'] > 0:
            logger.info(f"Deleted contract with ID: {contract_id}")
            return True
        logger.error(f"Failed to delete contract with ID: {contract_id}")
        return False

    def search_contracts(self, search_term: str) -> List[Dict[str, Any]]:
        query = """
            SELECT c.ContractId, s.PartyName as Seller, b.PartyName as Buyer, 
                   p.ProductName, c.PlannedQuantity, u.UnitName, c.StartDate, 
                   c.EndDate, c.SignDate, c.Signer, c.Status, c.Remarks
            FROM inventory.ActiveContract c
            JOIN inventory.ActiveParty s ON c.SellerId = s.PartyId
            JOIN inventory.ActiveParty b ON c.BuyerId = b.PartyId
            JOIN inventory.ActiveProduct p ON c.ProductId = p.ProductId
            JOIN inventory.ActiveUnit u ON c.UnitId = u.UnitId
            WHERE s.PartyName LIKE ? OR b.PartyName LIKE ? OR p.ProductName LIKE ?
        """
        search_param = f"%{search_term}%"
        results = self.execute_query(query, (search_param, search_param, search_param))
        if results is not None:
            self.contracts = results
            self.data_updated.emit()
        else:
            logger.error("Failed to search contracts")
            self.error_occurred.emit("Failed to search contracts")
        return self.contracts

contract_module = ContractModule()