from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy, QPushButton, QInputDialog, QMessageBox
from PyQt5.QtGui import QFontMetrics, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
import docker
import subprocess
import time
import sys

class ElidedLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("padding-left: 10px;")  # Add padding to the left
    
    def resizeEvent(self, event):
        fm = QFontMetrics(self.font())
        elided_text = fm.elidedText(self.text(), Qt.ElideRight, self.width() - 20)  # Adjust width for padding
        self.setText(elided_text)
        super().resizeEvent(event)

class ContainerCard(QFrame):
    def __init__(self, container, main_window):
        super().__init__()
        self.container = container
        self.main_window = main_window
        
        # Set fixed size for larger square appearance
        self.setFixedSize(250, 300)
        
        # Modern styling with square design
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 15px 10px;
                margin: 15px;
            }
            QFrame:hover {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
            }
            QLabel#nameLabel, QLabel#idLabel, QLabel#imageLabel, QLabel#statusLabel {
                qproperty-alignment: AlignCenter;
                background-color: transparent;
            }
            QLabel#nameLabel {
                text-indent: 0;
                font-size: 16px;
                font-weight: bold;
                padding: 20px 10px;
            }
            QLabel#idLabel {
                color: #6c757d;
                font-size: 13px;
            }
            QLabel#imageLabel {
                color: #495057;
                font-size: 13px;
            }
            QLabel#statusLabel {
                color: white;
                border-radius: 12px;
                padding: 16px 20px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
        
        self.setup_ui()

    def setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Container name (truncated if too long)
        name_label = ElidedLabel(self.container.name)
        name_label.setObjectName("nameLabel")
        layout.addWidget(name_label)
        
        # Container ID
        id_label = QLabel(f"ID: {self.container.short_id}")
        id_label.setObjectName("idLabel")
        layout.addWidget(id_label)
        
        # Status with colored background
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel(self.container.status.upper())
        self.status_label.setObjectName("statusLabel")
        status_color = "#28a745" if self.container.status == "running" else "#dc3545"
        self.status_label.setStyleSheet(f"""
            QLabel#statusLabel {{
                background-color: {status_color};
            }}
        """)
        status_layout.addStretch()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addWidget(status_container)
        
        # Image name (truncated if too long)
        image_name = self.container.image.tags[0] if self.container.image.tags else 'none'
        image_label = ElidedLabel(image_name)
        image_label.setObjectName("imageLabel")
        layout.addWidget(image_label)
        
        # Buttons for actions
        self.button_layout = QHBoxLayout()
                
        self.action_btn = QPushButton("Stop" if self.container.status == "running" else "Start")
        self.action_btn.setFixedHeight(30)
        self.action_btn.setFixedWidth(60)
        self.action_btn.clicked.connect(self.toggle_container_state)
        self.button_layout.addWidget(self.action_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_container)
        self.button_layout.addWidget(self.delete_btn)
        
        self.snapshot_btn = QPushButton("Snapshot")
        self.snapshot_btn.clicked.connect(self.snapshot_container)
        self.button_layout.addWidget(self.snapshot_btn)
        
        layout.addLayout(self.button_layout)
        
        # Add stretch at the bottom
        layout.addStretch()

        # Hide buttons initially
        self.set_edit_mode(False)

    def set_edit_mode(self, edit_mode):
        self.delete_btn.setVisible(edit_mode)
        self.snapshot_btn.setVisible(edit_mode)
        self.action_btn.setVisible(not edit_mode)
        self.button_layout.setSpacing(10 if edit_mode else 0)
        self.button_layout.setContentsMargins(0, 0, 0, 0 if edit_mode else 10)

    def toggle_container_state(self):
        self.action_btn.setEnabled(False)  # Disable the button while updating state
        self.action_btn.setStyleSheet("background-color: #003166;")  # Change color to indicate loading

        self.thread = QThread()
        self.worker = ContainerStateWorker(self.container.id)
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.worker.status_updated.connect(self.update_status)
        self.worker.log_message.connect(self.log_message)
        
        self.thread.start()

    def update_status(self, status):
        status_color = "#28a745" if status == "running" else "#dc3545"

        self.status_label.setText(status.upper())
        self.status_label.setStyleSheet(f"""
            QLabel#statusLabel {{
                background-color: {status_color};
            }}
        """)
        self.action_btn.setText("Stop" if status == "running" else "Start")
        self.action_btn.setEnabled(True)  # Re-enable the button after updating state
        self.action_btn.setStyleSheet("background-color: #007bff;")  # Change color to indicate loading

        self.action_btn.repaint()  # Explicitly repaint the button to ensure the text is updated

    def log_message(self, title, message, level):
        self.main_window.log_panel.add_log(title, message, level)

    def delete_container(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.container.id)
            container.remove(force=True)
            self.main_window.log_panel.add_log(
                "Container Deletion",
                f"Deleted container: {container.name}",
                "Success"
            )
            self.main_window.refresh_containers()
        except Exception as e:
            error_msg = f"Error deleting container: {str(e)}"
            print(error_msg)
            self.main_window.log_panel.add_log(
                "Container Deletion",
                error_msg,
                "Error"
            )

    def snapshot_container(self):
        try:
            image_name, ok = QInputDialog.getText(self, 'Snapshot', 'Enter new image name:')
            if ok and image_name:
                client = docker.from_env()
                container = client.containers.get(self.container.id)
                snapshot = container.commit(repository=image_name)
                self.main_window.snapshots[snapshot.id] = snapshot
                self.main_window.log_panel.add_log(
                    "Snapshot",
                    f"Created snapshot for container: {container.name} as image: {image_name}",
                    "Success"
                )
        except Exception as e:
            error_msg = f"Error creating snapshot: {str(e)}"
            print(error_msg)
            self.main_window.log_panel.add_log(
                "Snapshot",
                error_msg,
                "Error"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.handle_click()

    def handle_click(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.container.id)
            
            if container.status != "running":
                # Start the container
                print(f"Starting container {container.name} ({container.id})")
                container.start()
                
                # Wait for container to be running
                def check_status():
                    container.reload()
                    return container.status == "running"
                
                # Wait up to 5 seconds for container to start
                start_time = time.time()
                while time.time() - start_time < 5:
                    if check_status():
                        break
                    time.sleep(0.5)
                
                if container.status == "running":
                    self.main_window.log_panel.add_log(
                        "Container Start",
                        f"Started container: {container.name}",
                        "Success"
                    )
                else:
                    raise Exception("Container failed to start")
            
            # Open terminal
            self.open_terminal()
            
        except Exception as e:
            print(f"Error handling container click: {str(e)}")
            self.main_window.log_panel.add_log(
                "Container Action",
                f"Error: {str(e)}",
                "Error"
            )

    def open_terminal(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.container.id)
            
            if container.status == "running":
                # Detect available shell
                shell = self.detect_shell(container)
                print(f"Using shell: {shell}")
                
                if sys.platform == "win32":
                    cmd = f'start cmd.exe /k docker exec -it {container.id} {shell}'
                else:
                    cmd = f'x-terminal-emulator -e docker exec -it {container.id} {shell}'
                
                subprocess.Popen(cmd, shell=True)
                
                self.main_window.log_panel.add_log(
                    "Terminal",
                    f"Opened terminal for container: {container.name}",
                    "Success"
                )
            else:
                raise Exception("Container must be running to open terminal")
                
        except Exception as e:
            print(f"Error opening terminal: {str(e)}")
            self.main_window.log_panel.add_log(
                "Terminal",
                f"Failed to open terminal: {str(e)}",
                "Error"
            )

    def detect_shell(self, container):
        try:
            # Try to execute 'which' command for different shells
            for shell in ['/bin/bash', '/bin/sh', '/bin/ash']:
                result = container.exec_run(f'test -f {shell}')
                if result.exit_code == 0:
                    print(f"Found shell: {shell}")
                    return shell
            
            # If no shell found, default to /bin/sh
            print("No specific shell found, defaulting to /bin/sh")
            return '/bin/sh'
            
        except Exception as e:
            print(f"Error detecting shell: {str(e)}, defaulting to /bin/sh")
            return '/bin/sh'

class ContainerStateWorker(QObject):
    finished = pyqtSignal()
    status_updated = pyqtSignal(str)
    log_message = pyqtSignal(str, str, str)

    def __init__(self, container_id):
        super().__init__()
        self.container_id = container_id

    def run(self):
        try:
            client = docker.from_env()
            container = client.containers.get(self.container_id)
            
            if container.status == "running":
                self.log_message.emit("Stopping Container", f"Stopping container: {container.name} is in progress.", "Info")
                container.stop()
                self.log_message.emit("Container Stopped", f"Stopped container: {container.name}", "Success")
                self.status_updated.emit("exited")
            else:
                self.log_message.emit("Starting Container", f"Starting container: {container.name} is in progress.", "Info")
                container.start()
                self.log_message.emit("Container Started", f"Started container: {container.name}", "Success")
                self.status_updated.emit("running")
        except Exception as e:
            error_msg = f"Error toggling container state: {str(e)}"
            print(error_msg)
            self.log_message.emit("Container State Toggle", error_msg, "Error")
        finally:
            self.finished.emit()
