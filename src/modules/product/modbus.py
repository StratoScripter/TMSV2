# modbus.py

from PySide6.QtCore import QObject, Signal, Slot, QThread
from .server import server_module
from collections import OrderedDict
from threading import Lock
import logging
import time
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

class ModbusReaderThread(QThread):
    data_read = Signal(dict)

    def __init__(self, modbus_module):
        super().__init__()
        self.modbus_module = modbus_module
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.modbus_module.read_all_slaves()
                self.data_read.emit(data)
            except Exception as e:
                logger.error(f"Error in ModbusReaderThread: {str(e)}")
            time.sleep(0.1)  # Adjust this value to control read frequency

    def stop(self):
        self.running = False

class ModbusModule(QObject):
    data_updated = Signal(dict)
    error_occurred = Signal(str)
    modbus_connected = Signal(bool)
    database_connected = Signal(bool)
    current_weight_updated = Signal(int, float) 

    def __init__(self):
        super().__init__()
        self.slaves = []
        self.register_mappings = {}
        self.last_values = OrderedDict()
        self.last_values_lock = Lock()
        self.modbus_client = None
        self.is_modbus_connected = False
        self.connection = None
        server_module.connection_status_changed.connect(self.on_connection_status_changed)
        self.port = None
        self.reader_thread = None



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
                self.database_connected.emit(True)
                self.fetch_slaves()
                self.fetch_register_mappings()
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
                logger.info("ModbusModule disconnected from database")
            except Exception as e:
                logger.exception(f"Error disconnecting from database: {e}")
            finally:
                self.connection = None
                self.slaves = []
                self.register_mappings = {}
                self.database_connected.emit(False)

    @property
    def is_connected(self):
        return self.connection is not None and self.is_modbus_connected
    
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

    def fetch_slaves(self):
        query = "SELECT * FROM inventory.ActiveModbus ORDER BY SlaveAddress"
        results = self.execute_query(query)
        if results is not None:
            self.slaves = results
            logger.info(f"Fetched {len(self.slaves)} slave devices")
            self.data_updated.emit(self.last_values)
        else:
            logger.error("Failed to fetch slaves")
            self.error_occurred.emit("Failed to fetch slaves")

    def fetch_register_mappings(self):
        query = """
        SELECT rm.*, m.SlaveName, 
               CASE 
                   WHEN rm.MappedTable = 'StorageTank' THEN st.StorageTankName
                   WHEN rm.MappedTable = 'LoadingArm' THEN la.LoadingArmName
                   WHEN rm.MappedTable = 'Weighbridge' THEN wb.WeighbridgeName
               END AS EntityName
        FROM inventory.ActiveRegisterMapping rm
        JOIN inventory.ActiveModbus m ON rm.SlaveAddress = m.SlaveAddress
        LEFT JOIN inventory.ActiveStorageTank st ON rm.MappedTable = 'StorageTank' AND rm.MappedEntityId = st.StorageTankId
        LEFT JOIN inventory.ActiveLoadingArm la ON rm.MappedTable = 'LoadingArm' AND rm.MappedEntityId = la.LoadingArmId
        LEFT JOIN inventory.ActiveWeighbridge wb ON rm.MappedTable = 'Weighbridge' AND rm.MappedEntityId = wb.WeighbridgeId
        ORDER BY rm.SlaveAddress, rm.RegisterAddress
        """
        results = self.execute_query(query)
        if results is not None:
            self.register_mappings = {}
            for mapping in results:
                slave_address = mapping['SlaveAddress']
                if slave_address not in self.register_mappings:
                    self.register_mappings[slave_address] = []
                self.register_mappings[slave_address].append(mapping)
            logger.info(f"Fetched register mappings for {len(self.register_mappings)} slave devices")
            self.data_updated.emit(self.last_values)
        else:
            logger.error("Failed to fetch register mappings")
            self.error_occurred.emit("Failed to fetch register mappings")

    def set_connection_params(self, port: str, baudrate: int, parity: str = 'N', stopbits: int = 1, bytesize: int = 8, timeout: float = 1):
        self.port = port
        self.modbus_client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout
        )
        logger.info(f"Set Modbus connection parameters: port={port}, baudrate={baudrate}, parity={parity}, stopbits={stopbits}, bytesize={bytesize}, timeout={timeout}")

    def connect_modbus(self):
        if self.modbus_client is None:
            raise ValueError("Connection parameters not set. Call set_connection_params first.")
        logger.info(f"Attempting to connect to Modbus on port {self.port}")
        if not self.modbus_client.connect():
            logger.error(f"Failed to connect to the Modbus serial port {self.port}")
            self.is_modbus_connected = False
            self.modbus_connected.emit(False)
            raise Exception("Failed to connect to the Modbus serial port")
        logger.info(f"Successfully connected to Modbus on port {self.port}")
        self.is_modbus_connected = True
        self.modbus_connected.emit(True)
        self.start_continuous_reading()

    def disconnect_modbus(self):
        self.stop_continuous_reading()
        if self.modbus_client:
            logger.info(f"Disconnecting from Modbus on port {self.port}")
            self.modbus_client.close()
            self.is_modbus_connected = False
            self.modbus_connected.emit(False)
            logger.info("Disconnected from Modbus serial port")

    def read_register(self, slave_address: int, mapping: Dict[str, Any]) -> Optional[float]:
        try:
            function_code = mapping['FunctionCode']
            address = mapping['RegisterAddress']
            count = 1  # Assuming we're reading one register at a time

            logger.info(f"Reading register {address} from slave {slave_address} using function code {function_code}")

            if self.modbus_client is None:
                raise ValueError("Modbus client not initialized. Call set_connection_params first.")

            if function_code == 1:
                result = self.modbus_client.read_coils(address, count, slave=slave_address)
            elif function_code == 2:
                result = self.modbus_client.read_discrete_inputs(address, count, slave=slave_address)
            elif function_code == 3:
                result = self.modbus_client.read_holding_registers(address, count, slave=slave_address)
            elif function_code == 4:
                result = self.modbus_client.read_input_registers(address, count, slave=slave_address)
            else:
                logger.error(f"Unsupported function code: {function_code}")
                return None

            if not result.isError():
                raw_value = result.registers[0] if hasattr(result, 'registers') else result.bits[0]
                scaled_value = raw_value * mapping['ScaleFactor'] + mapping['Offset']
                
                self.last_values[(slave_address, mapping['MappingId'])] = scaled_value
                
                if mapping['MappedTable'] == 'Weighbridge' and mapping['MappedColumn'] == 'CurrentWeight':
                    weighbridge_id = mapping['MappedEntityId']
                    self.current_weight_updated.emit(weighbridge_id, scaled_value)
                else:
                    self.update_database_value(mapping['MappingId'], scaled_value)
                
                logger.info(f"Successfully read value {scaled_value} from register {address} of slave {slave_address}")
                return scaled_value
            else:
                logger.error(f"Error reading register {address} from slave {slave_address}: {result}")
                return None
        except ModbusException as e:
            logger.error(f"Modbus exception when reading register {address} from slave {slave_address}: {e}")
            self.error_occurred.emit(f"Modbus read error: {str(e)}")
            return None

    def update_database_value(self, mapping_id: int, value: float):
        try:
            self.execute_stored_procedure('UpdateMappedModbusValue', (mapping_id, value))
            logger.info(f"Updated database for mapping {mapping_id} with value {value}")
        except Exception as e:
            logger.error(f"Error updating database for mapping {mapping_id}: {e}")
            self.error_occurred.emit(f"Database update error: {str(e)}")

    def read_device_data(self, device: Dict[str, Any]) -> Optional[Dict[int, float]]:
        try:
            logger.info(f"Reading data from device {device['SlaveName']} (Address: {device['SlaveAddress']})")
            data = {}
            for mapping in self.register_mappings.get(device['SlaveAddress'], []):
                result = self.read_register(device['SlaveAddress'], mapping)
                if result is not None:
                    data[mapping['MappingId']] = result
            logger.info(f"Successfully read {len(data)} registers from device {device['SlaveName']}")
            return data
        except Exception as e:
            logger.error(f"Error reading from device {device['SlaveName']}: {e}")
            return None

    def read_all_slaves(self):
        if not self.is_modbus_connected:
            raise Exception("Modbus not connected. Cannot read slaves.")
        
        logger.info(f"Starting to read data from {len(self.slaves)} devices")
        new_data = {}
        for device in self.slaves:
            logger.info(f"Attempting to read from device: {device}")
            data = self.read_device_data(device)
            if data:
                logger.info(f"Read data: {data}")
                new_data.update(data)
            else:
                logger.warning(f"No data read from device {device['SlaveName']}")
        logger.info("Finished reading data from all devices")
        return new_data

    def start_continuous_reading(self):
        if self.reader_thread is None or not self.reader_thread.isRunning():
            self.reader_thread = ModbusReaderThread(self)
            self.reader_thread.data_read.connect(self.on_data_read)
            self.reader_thread.start()

    def stop_continuous_reading(self):
        if self.reader_thread and self.reader_thread.isRunning():
            self.reader_thread.stop()
            self.reader_thread.wait()
            self.reader_thread = None

    @Slot(dict)
    def on_data_read(self, data):
        self.data_updated.emit(data)

    def get_slave_details(self, slave_address: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM inventory.ActiveModbus WHERE SlaveAddress = ?"
        results = self.execute_query(query, params=(slave_address,))
        return results[0] if results else None

    def get_register_mapping_details(self, mapping_id: int) -> Optional[Dict[str, Any]]:
        query = """
        SELECT rm.*, m.SlaveName, 
               CASE 
                   WHEN rm.MappedTable = 'StorageTank' THEN st.StorageTankName
                   WHEN rm.MappedTable = 'LoadingArm' THEN la.LoadingArmName
                   WHEN rm.MappedTable = 'Weighbridge' THEN wb.WeighbridgeName
               END AS EntityName
        FROM inventory.ActiveRegisterMapping rm
        JOIN inventory.ActiveModbus m ON rm.SlaveAddress = m.SlaveAddress
        LEFT JOIN inventory.ActiveStorageTank st ON rm.MappedTable = 'StorageTank' AND rm.MappedEntityId = st.StorageTankId
        LEFT JOIN inventory.ActiveLoadingArm la ON rm.MappedTable = 'LoadingArm' AND rm.MappedEntityId = la.LoadingArmId
        LEFT JOIN inventory.ActiveWeighbridge wb ON rm.MappedTable = 'Weighbridge' AND rm.MappedEntityId = wb.WeighbridgeId
        WHERE rm.MappingId = ?
        """
        results = self.execute_query(query, params=(mapping_id,))
        return results[0] if results else None

    def add_slave(self, slave_address: int, slave_name: str, baudrate: int, port: str, 
                  is_active: bool, databits: int, parity: str, stopbits: int) -> bool:
        query = """
        INSERT INTO inventory.Modbus 
        (SlaveAddress, SlaveName, Baudrate, Port, IsActive, Databits, Parity, StopBits)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (slave_address, slave_name, baudrate, port, is_active, databits, parity, stopbits)
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error("Failed to add slave")
            return False
        self.fetch_slaves()
        return True

    def update_slave(self, slave_address: int, slave_name: str, baudrate: int, port: str, 
                     is_active: bool, databits: int, parity: str, stopbits: int) -> bool:
        query = """
        UPDATE inventory.Modbus
        SET SlaveName=?, Baudrate=?, Port=?, IsActive=?, Databits=?, Parity=?, StopBits=?, ModifiedDate=GETDATE()
        WHERE SlaveAddress=?
        """
        params = (slave_name, baudrate, port, is_active, databits, parity, stopbits, slave_address)
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to update slave with address {slave_address}")
            return False
        self.fetch_slaves()
        return True

    def delete_slave(self, slave_address: int) -> bool:
        query = """
        UPDATE inventory.Modbus
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE SlaveAddress = ?
        """
        result = self.execute_query(query, params=(slave_address,), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to delete slave with address {slave_address}")
            return False
        self.fetch_slaves()
        return True

    def add_register_mapping(self, slave_address: int, register_address: int, register_type: str,
                             function_code: int, mapped_table: str, mapped_column: str,
                             mapped_entity_id: int, scale_factor: float, offset: float,
                             store_historical: bool, is_read_only: bool) -> bool:
        query = """
        INSERT INTO inventory.RegisterMapping 
        (SlaveAddress, RegisterAddress, RegisterType, FunctionCode, MappedTable, MappedColumn, 
        MappedEntityId, ScaleFactor, Offset, StoreHistorical, IsReadOnly)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (slave_address, register_address, register_type, function_code, mapped_table,
                  mapped_column, mapped_entity_id, scale_factor, offset, store_historical, is_read_only)
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error("Failed to add register mapping")
            return False
        self.fetch_register_mappings()
        return True

    def update_register_mapping(self, mapping_id: int, slave_address: int, register_address: int,
                                register_type: str, function_code: int, mapped_table: str,
                                mapped_column: str, mapped_entity_id: int, scale_factor: float,
                                offset: float, store_historical: bool, is_read_only: bool) -> bool:
        query = """
        UPDATE inventory.RegisterMapping
        SET SlaveAddress=?, RegisterAddress=?, RegisterType=?, FunctionCode=?, MappedTable=?, 
            MappedColumn=?, MappedEntityId=?, ScaleFactor=?, Offset=?, StoreHistorical=?, 
            IsReadOnly=?, ModifiedDate=GETDATE()
        WHERE MappingId=?
        """
        params = (slave_address, register_address, register_type, function_code, mapped_table,
                  mapped_column, mapped_entity_id, scale_factor, offset, store_historical,
                  is_read_only, mapping_id)
        result = self.execute_query(query, params=params, fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to update register mapping with ID {mapping_id}")
            return False
        self.fetch_register_mappings()
        return True

    def delete_register_mapping(self, mapping_id: int) -> bool:
        query = """
        UPDATE inventory.RegisterMapping
        SET IsDeleted = 1, DeletedDate = GETDATE()
        WHERE MappingId = ?
        """
        result = self.execute_query(query, params=(mapping_id,), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to delete register mapping with ID {mapping_id}")
            return False
        self.fetch_register_mappings()
        return True

    def get_available_tables(self) -> List[str]:
        return ['StorageTank', 'LoadingArm', 'Weighbridge']

    def get_table_columns(self, table_name: str) -> List[str]:
        query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"
        results = self.execute_query(query)
        return [row['COLUMN_NAME'] for row in results] if results else []

    def get_table_entities(self, table_name: str) -> List[Dict[str, Any]]:
        id_column = f"{table_name}Id"
        name_column = f"{table_name}Name"
        query = f"SELECT {id_column}, {name_column} FROM inventory.Active{table_name}"
        return self.execute_query(query) or []

    def execute_stored_procedure(self, procedure_name: str, params: tuple):
        try:
            if self.connection is None:
                raise ValueError("Connection not established. Call connect_to_database first.")
            with self.connection.cursor() as cursor:
                cursor.execute(f"EXEC inventory.{procedure_name} {','.join(['?' for _ in params])}", params)
                self.connection.commit()
        except Exception as e:
            logger.error(f"Error executing stored procedure {procedure_name}: {e}")
            if self.connection is not None:
                self.connection.rollback()

    def update_communication_status(self, slave_address: int, is_connected: bool) -> bool:
        query = """
        UPDATE inventory.Modbus
        SET IsActive = ?, ModifiedDate = GETDATE()
        WHERE SlaveAddress = ?
        """
        result = self.execute_query(query, params=(is_connected, slave_address), fetch=False)
        if result is None or result[0]['affected_rows'] == 0:
            logger.error(f"Failed to update communication status for slave {slave_address}")
            return False
        self.fetch_slaves()
        return True

    def get_communication_status(self, slave_address: int) -> Optional[bool]:
        query = "SELECT IsActive FROM inventory.ActiveModbus WHERE SlaveAddress = ?"
        results = self.execute_query(query, params=(slave_address,))
        return results[0]['IsActive'] if results else None

# Create an instance of the ModbusModule
modbus_module = ModbusModule()