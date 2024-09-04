# report.py

from typing import List, Dict, Any, Optional
from datetime import date
from modules.logger_config import get_logger

logger = get_logger('Report')

class ReportModule:
    def __init__(self, server_module):
        self.server_module = server_module

    def initialize(self, server_info):
        if not self.server_module.connect_to_database(server_info):
            raise ConnectionError(f"Failed to connect to server: {server_info.name}")

    def log_activity(self, module: str, action: str, status: str):
        self.server_module.log_activity("ReportModule", action, status)

    def execute_query(self, query, params=None, fetch=True):
        try:
            result = self.server_module.execute_query(query, params, fetch)
            return result
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise

    def get_report_data(self, report_type: str, start_date: Optional[date], end_date: Optional[date]) -> List[Dict[str, Any]]:
        try:
            base_query = """
                SELECT 
                    p.ProductId,
                    p.ProductName,
                    o.OrderId,
                    o.PlannedQuantity,
                    o.ActualQuantity,
                    o.OrderDate,
                    o.Status,
                    u.UnitName,
                    seller.PartyName AS SellerName,
                    buyer.PartyName AS BuyerName
                FROM 
                    inventory.[Order] o
                    JOIN inventory.Product p ON o.ProductId = p.ProductId
                    JOIN inventory.Unit u ON o.UnitId = u.UnitId
                    JOIN inventory.Party seller ON o.SellerId = seller.PartyId
                    JOIN inventory.Party buyer ON o.BuyerId = buyer.PartyId
                WHERE 1=1
            """

            params = []

            if start_date:
                base_query += " AND o.OrderDate >= ?"
                params.append(start_date)
            if end_date:
                base_query += " AND o.OrderDate <= ?"
                params.append(end_date)

            if report_type == 'product':
                query = base_query + " ORDER BY p.ProductName, o.OrderDate"
            else:  # customer report
                query = base_query + " ORDER BY buyer.PartyName, p.ProductName, o.OrderDate"

            data = self.execute_query(query, params)
            logger.info(f"Retrieved {len(data)} rows from the database")
            self.log_activity("ReportModule", "Get Report Data", f"Success: Retrieved {len(data)} rows for {report_type} report")
            return data
        except Exception as e:
            logger.error(f"Error fetching report data: {e}")
            self.log_activity("Report Module", "Get Report Data", f"Failed: {str(e)}")
            return []

    def search_report_data(self, search_term: str) -> List[Dict[str, Any]]:
        try:
            query = """
                SELECT 
                    p.ProductId,
                    p.ProductName,
                    o.OrderId,
                    o.PlannedQuantity,
                    o.ActualQuantity,
                    o.OrderDate,
                    o.Status,
                    u.UnitName,
                    seller.PartyName AS SellerName,
                    buyer.PartyName AS BuyerName
                FROM 
                    inventory.[Order] o
                    JOIN inventory.Product p ON o.ProductId = p.ProductId
                    JOIN inventory.Unit u ON o.UnitId = u.UnitId
                    JOIN inventory.Party seller ON o.SellerId = seller.PartyId
                    JOIN inventory.Party buyer ON o.BuyerId = buyer.PartyId
                WHERE 
                    p.ProductName LIKE ? OR buyer.PartyName LIKE ? OR seller.PartyName LIKE ?
                ORDER BY o.OrderDate DESC
            """
            params = [f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"]
            data = self.execute_query(query, params)
            self.log_activity("ReportModule","Search Report Data", f"Success: Found {len(data)} results for term '{search_term}'")
            return data
        except Exception as e:
            logger.error(f"Error searching report data: {e}")
            self.log_activity("ReportModule","Search Report Data", f"Failed: {str(e)}")
            return []