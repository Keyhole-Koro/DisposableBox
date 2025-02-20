from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QTextEdit
from PyQt5.QtCore import Qt, QDateTime

class LogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Activity Log")
        header.setStyleSheet("""
            font-weight: bold;
            padding: 5px;
            background-color: #f0f0f0;
            border-bottom: 1px solid #ddd;
        """)
        layout.addWidget(header)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        layout.addWidget(self.log_area)

    def add_log(self, title, message, status="Info"):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        
        # Set color based on status
        color = {
            "Success": "#28a745",
            "Error": "#dc3545",
            "Warning": "#ffc107",
            "Info": "#17a2b8",
            "In Progress": "#007bff"
        }.get(status, "#212529")

        # Format the log entry
        log_entry = f'<p style="margin: 2px 0;"><span style="color: #666;">[{timestamp}]</span> ' \
                   f'<span style="color: {color};"><b>{title}</b></span>: {message}</p>'
        
        # Add to log area
        self.log_area.append(log_entry)
        
        # Scroll to bottom
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
