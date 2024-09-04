from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QHeaderView, QDateEdit, QTimeEdit,
                               QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QComboBox, QFrame, QFileDialog, QScrollArea,
                               QSizePolicy)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QTimer
from PySide6.QtGui import QTextDocument, QTextCursor, QIcon, QColor, QPainter, QTextTableFormat
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from .historical import HistoricalModule
from ui.ui_styles import apply_styles, Styles, Colors, Fonts
from modules.logger_config import get_logger
import xlwt

logger = get_logger('historical_ui')

class HistoricalWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.historical_module = HistoricalModule()
        apply_styles(self)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.create_ribbon()
        layout.addWidget(self.ribbon)

        self.create_filter_bar()
        layout.addWidget(self.filter_bar)

        self.historical_table = QTableWidget()
        self.create_historical_table()
        layout.addWidget(self.historical_table)

        # Initial data load
        QTimer.singleShot(100, self.load_all_historical_data)

    def create_ribbon(self):
        self.ribbon = QFrame()
        
        ribbon_layout = QHBoxLayout(self.ribbon)
        ribbon_layout.setSpacing(5)
        ribbon_layout.setContentsMargins(5, 5, 5, 5)

        buttons = [
            ("Search", self.search_historical_data, "search.png"),
            ("Export", self.export_to_excel, "export.png"),
            ("Print", self.print_or_save_pdf, "print.png"),
            ("Refresh", self.load_all_historical_data, "refresh.png")
        ]

        for text, slot, icon in buttons:
            button = QPushButton(QIcon(f"icons/{icon}"), text)
            
            button.clicked.connect(slot)
            ribbon_layout.addWidget(button)

        ribbon_layout.addStretch(1)

    def create_filter_bar(self):
        self.filter_bar = QFrame()
        
        filter_layout = QVBoxLayout(self.filter_bar)
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(5, 5, 5, 5)

        first_row = QHBoxLayout()
        second_row = QHBoxLayout()

        self.start_date = QDateEdit(QDate.currentDate())
        self.start_time = QTimeEdit(QTime(0, 0))
        self.end_date = QDateEdit(QDate.currentDate())
        self.end_time = QTimeEdit(QTime(23, 59))
        self.loading_arm_combo = QComboBox()

        for label_text, widget in [
            ("Start Date:", self.start_date),
            ("Start Time:", self.start_time),
            ("End Date:", self.end_date),
            ("End Time:", self.end_time),
            ("Loading Arm:", self.loading_arm_combo)
        ]:
            label = QLabel(label_text)
            
            first_row.addWidget(label)
            
            first_row.addWidget(widget)

        self.product_combo = QComboBox()
        self.seller_combo = QComboBox()
        self.buyer_combo = QComboBox()
        self.license_plate = QLineEdit()
        self.driver_combo = QComboBox()

        for label_text, widget in [
            ("Product:", self.product_combo),
            ("Seller:", self.seller_combo),
            ("Buyer:", self.buyer_combo),
            ("License Plate:", self.license_plate),
            ("Driver:", self.driver_combo)
        ]:
            label = QLabel(label_text)
            
            second_row.addWidget(label)
            
            second_row.addWidget(widget)

        filter_layout.addLayout(first_row)
        filter_layout.addLayout(second_row)

    def create_historical_table(self):
        
        headers = ["Transaction Date", "Product", "Seller", "Buyer", "Quantity", "Unit", 
                   "Driver", "Vehicle", "Initial Weight", "Final Weight", "Loading Arm",
                   "Order ID", "Created Date", "Initial Weight", "Final Weight"]
        self.historical_table.setColumnCount(len(headers))
        self.historical_table.setHorizontalHeaderLabels(headers)
        
        header = self.historical_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self.historical_table.verticalHeader().setVisible(False)
        self.historical_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.historical_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.historical_table.setSortingEnabled(True)
        self.historical_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.historical_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def load_all_historical_data(self):
        try:
            historical_data = self.historical_module.get_all_historical_data()
            self.populate_historical_table(historical_data)
            self.populate_dropdowns()
        except Exception as e:
            logger.error(f"Failed to load historical data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load historical data: {str(e)}")

    def populate_historical_table(self, historical_data):
        logger.info(f"Populating table with {len(historical_data)} rows")
        self.historical_table.setSortingEnabled(False)
        self.historical_table.setRowCount(len(historical_data))
        for row, data in enumerate(historical_data):
            for col, key in enumerate([
                'TransactionDate', 'ProductName', 'SellerName', 'BuyerName', 'Quantity', 'UnitName',
                'DriverName', 'LicensePlateNumber', 'InitialWeight', 'FinalWeight', 'LoadingArmName',
                'OrderId', 'CreatedDate', 'InitialWeight', 'FinalWeight'
            ]):
                self.historical_table.setItem(row, col, QTableWidgetItem(str(data.get(key, ''))))
        
        logger.info(f"Populated {self.historical_table.rowCount()} rows in the table")
        self.historical_table.resizeRowsToContents()
        self.historical_table.setSortingEnabled(True)

    def populate_dropdowns(self):
        dropdowns = {
            self.loading_arm_combo: 10,
            self.product_combo: 1,
            self.seller_combo: 2,
            self.buyer_combo: 3,
            self.driver_combo: 6
        }

        for combo, col in dropdowns.items():
            items = set(self.historical_table.item(row, col).text() for row in range(self.historical_table.rowCount()))
            combo.clear()
            combo.addItem("All")
            combo.addItems(sorted(items))

    def search_historical_data(self):
        from datetime import datetime
        
        start_datetime = datetime.strptime(f"{self.start_date.date().toString('yyyy-MM-dd')} {self.start_time.time().toString('HH:mm:ss')}", "%Y-%m-%d %H:%M:%S")
        end_datetime = datetime.strptime(f"{self.end_date.date().toString('yyyy-MM-dd')} {self.end_time.time().toString('HH:mm:ss')}", "%Y-%m-%d %H:%M:%S")
        
        filters = {
            'loading_arm': self.loading_arm_combo.currentText(),
            'product': self.product_combo.currentText(),
            'seller': self.seller_combo.currentText(),
            'buyer': self.buyer_combo.currentText(),
            'license_plate': self.license_plate.text().strip(),
            'driver': self.driver_combo.currentText()
        }
        filters = {k: (None if v == "All" else v) for k, v in filters.items()}
        filters['license_plate'] = filters['license_plate'] or None
        
        logger.info(f"Searching with parameters: start_datetime={start_datetime}, "
                    f"end_datetime={end_datetime}, {filters}")
        
        try:
            historical_data = self.historical_module.search_historical_data(
                start_datetime, end_datetime, **filters
            )

            logger.info(f"Received {len(historical_data)} results from search")

            if historical_data:
                self.populate_historical_table(historical_data)
            else:
                logger.warning("No historical data found matching the search criteria.")
                QMessageBox.information(self, "Search Results", "No historical data found matching the search criteria.")
        except Exception as e:
            logger.error(f"An error occurred while searching: {str(e)}")
            QMessageBox.critical(self, "Search Error", f"An error occurred while searching: {str(e)}")

    def export_to_excel(self):
        if self.historical_table.rowCount() == 0:
            QMessageBox.warning(self, "Export Error", "No data to export.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xls)")
        if file_name:
            if not file_name.endswith('.xls'):
                file_name += '.xls'

            try:
                workbook = xlwt.Workbook()
                sheet = workbook.add_sheet("Historical Data")

                headers = [self.historical_table.horizontalHeaderItem(i).text() for i in range(self.historical_table.columnCount())]
                for col, header in enumerate(headers):
                    sheet.write(0, col, header)

                for row in range(self.historical_table.rowCount()):
                    for col in range(self.historical_table.columnCount()):
                        item = self.historical_table.item(row, col)
                        if item is not None:
                            sheet.write(row + 1, col, item.text())

                workbook.save(file_name)
                QMessageBox.information(self, "Export Successful", f"Data exported to {file_name}")
            except Exception as e:
                logger.error(f"Failed to export data: {str(e)}")
                QMessageBox.warning(self, "Export Error", f"Failed to export data: {str(e)}")

    def print_or_save_pdf(self):
        if self.historical_table.rowCount() == 0:
            QMessageBox.warning(self, "Print Error", "No data to print.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self.print_table(printer)

    def print_table(self, printer):
        document = QTextDocument()
        cursor = QTextCursor(document)
        
        table_format = QTextTableFormat()
        table_format.setBorder(0.5)
        table_format.setBorderStyle(QTextTableFormat.BorderStyle.BorderStyle_Solid)
        table_format.setCellPadding(2)
        table_format.setHeaderRowCount(1)
        
        table = cursor.insertTable(self.historical_table.rowCount() + 1, self.historical_table.columnCount(), table_format)

        header_format = cursor.charFormat()
        header_format.setBackground(QColor(Colors.TABLE_HEADER))
        header_format.setForeground(QColor(Qt.GlobalColor.white))
        header_format.setFontWeight(700)  # Bold

        for column in range(self.historical_table.columnCount()):
            cursor.insertText(self.historical_table.horizontalHeaderItem(column).text())
            cursor.setCharFormat(header_format)
            cursor.movePosition(QTextCursor.MoveOperation.NextCell)

        cursor.setCharFormat(QTextCursor.charFormat(cursor))

        for row in range(self.historical_table.rowCount()):
            for column in range(self.historical_table.columnCount()):
                item = self.historical_table.item(row, column)
                if item is not None:
                    cursor.insertText(item.text())
                cursor.movePosition(QTextCursor.MoveOperation.NextCell)

        document.setPageSize(printer.pageRect().size())

        painter = QPainter(printer)
        document.drawContents(painter)
        painter.end()

        if printer.outputFormat() == QPrinter.OutputFormat.PdfFormat:
            QMessageBox.information(self, "Save Successful", f"Data saved as PDF: {printer.outputFileName()}")
        else:
            QMessageBox.information(self, "Print Successful", "Data sent to printer.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.historical_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.historical_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.historical_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

