from PySide6.QtCore import QObject, Signal, Slot
from modules.product.server import server_module
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PartyModule(QObject):
    data_updated = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.parties: List[Dict[str, Any]] = []
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
                self.fetch_parties()
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
                logger.info("PartyModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.parties = []

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

    def fetch_parties(self):
        query = """
        SELECT p.PartyId, p.PartyName, p.ContactPerson, p.ContactNumber, p.Email, p.Address, p.CreatedDate, pra.PartyRoleId
        FROM inventory.ActiveParty p
        JOIN inventory.ActivePartyRoleAssignment pra ON p.PartyId = pra.PartyId
        """
        results = self.execute_query(query)
        if results is not None:
            return results
        else:
            logger.error("Failed to fetch parties")
            self.error_occurred.emit("Failed to fetch parties")
            return []

    def get_party(self, party_id: int) -> Optional[Dict[str, Any]]:
        query = """
        SELECT p.PartyId, p.PartyName, p.ContactPerson, p.ContactNumber, p.Email, p.Address, p.CreatedDate, pra.PartyRoleId
        FROM inventory.ActiveParty p
        JOIN inventory.ActivePartyRoleAssignment pra ON p.PartyId = pra.PartyId
        WHERE p.PartyId = ?
        """
        results = self.execute_query(query, params=(party_id,))
        return results[0] if results else None

    def add_party(self, party: Dict[str, Any]) -> bool:
        try:
            query1 = """
            INSERT INTO inventory.Party (PartyName, ContactPerson, ContactNumber, Email, Address)
            OUTPUT INSERTED.PartyId
            VALUES (?, ?, ?, ?, ?)
            """
            params1 = (party['PartyName'], party['ContactPerson'], party['ContactNumber'], party['Email'], party['Address'])
            result = self.execute_query(query1, params1)
            
            if result and len(result) > 0 and 'PartyId' in result[0]:
                party_id = result[0]['PartyId']
                
                query2 = """
                INSERT INTO inventory.PartyRoleAssignment (PartyId, PartyRoleId, AssignedDate)
                VALUES (?, ?, GETDATE())
                """
                self.execute_query(query2, params=(party_id, party['PartyRoleId']), fetch=False)
                
                logger.info(f"Added new party: {party['PartyName']}")
                return True
            logger.error("Failed to add party: No PartyId returned")
            return False
        except Exception as e:
            logger.error(f"Error adding party: {e}")
            return False

    def update_party(self, party: Dict[str, Any]) -> bool:
        try:
            query1 = """
            UPDATE inventory.Party
            SET PartyName = ?, ContactPerson = ?, ContactNumber = ?, 
                Email = ?, Address = ?
            WHERE PartyId = ?
            """
            params1 = (party['PartyName'], party['ContactPerson'], party['ContactNumber'], 
                       party['Email'], party['Address'], party['PartyId'])
            self.execute_query(query1, params1, fetch=False)
            
            query2 = """
            UPDATE inventory.PartyRoleAssignment
            SET PartyRoleId = ?
            WHERE PartyId = ?
            """
            self.execute_query(query2, params=(party['PartyRoleId'], party['PartyId']), fetch=False)
            
            logger.info(f"Updated party: {party['PartyName']}")
            return True
        except Exception as e:
            logger.error(f"Error updating party: {e}")
            return False

    def delete_party(self, party_id: int) -> bool:
        query = """
        UPDATE inventory.Party
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE PartyId = ?
        """
        result = self.execute_query(query, params=(party_id,), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to delete party with ID {party_id}")
            return False
        return True

    def search_parties(self, search_term: str):
        query = """
        SELECT p.PartyId, p.PartyName, p.ContactPerson, p.ContactNumber, p.Email, p.Address, p.CreatedDate, pra.PartyRoleId
        FROM inventory.ActiveParty p
        JOIN inventory.ActivePartyRoleAssignment pra ON p.PartyId = pra.PartyId
        WHERE p.PartyName LIKE ? OR p.ContactPerson LIKE ?
        """
        search_param = f"%{search_term}%"
        results = self.execute_query(query, params=(search_param, search_param))
        if results is not None:
            self.parties = results
            self.data_updated.emit()
        else:
            logger.error("Failed to search parties")
            self.error_occurred.emit("Failed to search parties")

    def get_party_roles(self) -> List[Dict[str, Any]]:
        query = "SELECT PartyRoleId, RoleName FROM inventory.ActivePartyRole"
        return self.execute_query(query) or []

party_module = PartyModule()