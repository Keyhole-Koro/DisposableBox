from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PyQt5.QtGui import QFontMetrics, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
import docker
import subprocess
import time
import sys  # Add this import

class ElidedLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignCenter)
    
    def resizeEvent(self, event):
        fm = QFontMetrics(self.font())
        elided_text = fm.elidedText(self.text(), Qt.ElideRight, self.width())
        self.setText(elided_text)
        super().resizeEvent(event)

class ContainerCard(QFrame):
    def __init__(self, container, main_window):
        super().__init__()
        self.container = container
        self.main_window = main_window
        
        # Set fixed size for larger square appearance
        self.setFixedSize(250, 250)
        
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
                font-size: 16px;
                font-weight: bold;
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
                padding: 13px 20px;
                font-size: 14px;
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
        
        status_label = QLabel(self.container.status.upper())
        status_label.setObjectName("statusLabel")
        status_color = "#28a745" if self.container.status == "running" else "#dc3545"
        status_label.setStyleSheet(f"""
            QLabel#statusLabel {{
                background-color: {status_color};
            }}
        """)
        status_layout.addStretch()
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        layout.addWidget(status_container)
        
        # Image name (truncated if too long)
        image_name = self.container.image.tags[0] if self.container.image.tags else 'none'
        image_label = ElidedLabel(image_name)
        image_label.setObjectName("imageLabel")
        layout.addWidget(image_label)
        
        # Add stretch at the bottom
        layout.addStretch()

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
