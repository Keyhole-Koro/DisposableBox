import sys
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame, QGroupBox, QLineEdit, QComboBox, QDialog, QCheckBox, QLayout, QTreeWidget, QTreeWidgetItem, QToolBar, QAction, QWidget
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal, QPropertyAnimation, QPoint, QEasingCurve, QRect, QDateTime
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QPixmap
import docker
from fastapi import FastAPI
from datetime import datetime
from typing import Optional
from PyQt5 import QtWidgets
from PyQt5.QtCore import qDebug

from settings import Settings
from async_worker import AsyncWorker
from iso_manager import ISOManager
from notification import NotificationManager
from log_panel import LogPanel
from container_card import ContainerCard
from create_container_dialog import CreateContainerDialog
from qflow_layout import QFlowLayout

# Modern style sheet
STYLE_SHEET = """
QMainWindow, QDialog {
    background-color: #f5f6fa;
}
# ...existing code...
"""

# Backend setup
app = FastAPI()
docker_client = docker.DockerClient(base_url='tcp://localhost:2375')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docker Container Manager")
        self.workers = []
        self.client = docker.from_env()
        
        # Initialize debug tools
        self.setup_debug()
        
        self.setup_ui()
        
        # Set minimum window size
        self.setMinimumSize(1200, 800)

    def setup_debug(self):
        # Create debug window
        #self.debug_window = DebugWindow(self)
        
        # Add debug toolbar
        debug_toolbar = QToolBar("Debug")
        self.addToolBar(Qt.RightToolBarArea, debug_toolbar)
        
        # Debug actions
        #toggle_debug = QAction("Debug Window", self)
        #toggle_debug.setCheckable(True)
        #toggle_debug.triggered.connect(self.toggle_debug_window)
        #debug_toolbar.addAction(toggle_debug)
        
        #toggle_borders = QAction("Show Borders", self)
        #toggle_borders.setCheckable(True)
        #toggle_borders.triggered.connect(self.toggle_debug_borders)
        #debug_toolbar.addAction(toggle_borders)
        
        self.debug_borders = False

    def toggle_debug_window(self):
        if self.debug_window.isVisible():
            self.debug_window.hide()
        else:
            self.debug_window.show()
            self.debug_window.populate_tree(self)

    def toggle_debug_borders(self):
        self.debug_borders = not self.debug_borders
        if self.debug_borders:
            self.apply_debug_borders(self)
        else:
            self.remove_debug_borders(self)

    def apply_debug_borders(self, widget):
        # Add colored borders to all widgets
        for child in widget.findChildren(QWidget):
            current_style = child.styleSheet()
            child.setStyleSheet(f"{current_style}; border: 1px solid red;")

    def remove_debug_borders(self, widget):
        # Remove debug borders
        for child in widget.findChildren(QWidget):
            style = child.styleSheet()
            style = style.replace("; border: 1px solid red;", "")
            child.setStyleSheet(style)

    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Left panel (Container list)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # Header with create button
        header_layout = QHBoxLayout()
        header_label = QLabel("Containers")
        header_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #212529;
        """)
        header_layout.addWidget(header_label)
        
        create_btn = QPushButton("New Container")
        create_btn.setIcon(QIcon(":/icons/add.png"))
        create_btn.clicked.connect(self.create_container)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        header_layout.addWidget(create_btn)
        left_layout.addLayout(header_layout)
        
        # Container scroll area
        self.container_scroll = QScrollArea()
        self.container_scroll.setWidgetResizable(True)
        self.container_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.container_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #f8f9fa;
                border: none;
                border-radius: 15px;
            }
        """)
        
        # Container widget with flow layout
        self.container_widget = QWidget()
        self.container_layout = QFlowLayout(self.container_widget)
        self.container_layout.setSpacing(20)  # Increased spacing between cards
        self.container_scroll.setWidget(self.container_widget)
        
        left_layout.addWidget(self.container_scroll)
        layout.addWidget(left_panel)
        
        # Right panel (Log panel)
        self.log_panel = LogPanel()
        layout.addWidget(self.log_panel)
        
        # Set size ratio between panels
        layout.setStretch(0, 2)  # Container list takes 2/3
        layout.setStretch(1, 1)  # Log panel takes 1/3
        
        # Initial container refresh
        self.refresh_containers()

    def create_container(self):
        try:
            print("Opening create container dialog...")
            dialog = CreateContainerDialog(self)
            dialog.setMinimumWidth(500)  # Set minimum dialog width
            
            if dialog.exec_() == QDialog.Accepted:
                name, image = dialog.get_container_info()
                print(f"Creating container with name: {name}, image: {image}")
                
                self.log_panel.add_log(
                    "Container Creation",
                    f"Pulling image: {image}",
                    "In Progress"
                )
                
                try:
                    # Pull the image
                    print(f"Pulling image: {image}")
                    self.client.images.pull(image)
                    
                    # Generate container name if not provided
                    if not name:
                        base_name = image.split(':')[0].split('/')[-1]
                        existing_names = [c.name for c in self.client.containers.list(all=True)]
                        index = 1
                        while f"{base_name}{index}" in existing_names:
                            index += 1
                        name = f"{base_name}{index}"
                    
                    print(f"Creating container with name: {name}")
                    
                    # Create the container
                    container = self.client.containers.create(
                        image=image,
                        name=name,
                        tty=True,
                        stdin_open=True,
                        detach=True
                    )
                    
                    print(f"Container created successfully: {container.id}")
                    
                    self.log_panel.add_log(
                        "Container Creation",
                        f"Created container: {name}",
                        "Success"
                    )
                    
                    self.refresh_containers()
                    
                except Exception as e:
                    error_msg = f"Error creating container: {str(e)}"
                    print(error_msg)
                    self.log_panel.add_log(
                        "Container Creation",
                        error_msg,
                        "Error"
                    )
                    
        except Exception as e:
            error_msg = f"Error in create_container: {str(e)}"
            print(error_msg)
            self.log_panel.add_log(
                "Container Creation",
                error_msg,
                "Error"
            )

    def refresh_containers(self):
        try:
            print("Refreshing container list...")
            # Clear existing containers from layout
            while self.container_layout.count():
                child = self.container_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Add containers to grid
            containers = self.client.containers.list(all=True)
            for container in containers:
                print(f"Adding container to grid: {container.name} ({container.id})")
                card = ContainerCard(container, self)
                self.container_layout.addWidget(card)

        except Exception as e:
            error_msg = f"Error refreshing containers: {str(e)}"
            print(error_msg)
            self.log_panel.add_log(
                "Refresh",
                error_msg,
                "Error"
            )

    def closeEvent(self, event):
        # Clean up workers when closing
        for worker in self.workers:
            worker.quit()
        super().closeEvent(event)

def run_app():
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    
    app = QApplication(sys.argv)
    
    # Set fusion style for better debugging
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_app()