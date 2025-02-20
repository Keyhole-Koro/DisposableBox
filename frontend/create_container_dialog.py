from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QLineEdit, QComboBox, QCheckBox, QPushButton, QLabel, QHBoxLayout, QWidget, QFileDialog, QTextEdit, QMessageBox
import docker

class CreateContainerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Create New Container")
        self.setModal(True)
        self.client = docker.from_env()
        
        # Define image versions
        self.image_versions = {
            "Ubuntu": ["22.04", "20.04", "18.04", "latest"],
            "Debian": ["12", "11", "10", "latest"],
            "Alpine": ["3.19", "3.18", "3.17", "latest"],
            "CentOS": ["7", "latest"],
            "Fedora": ["39", "38", "latest"],
            "Python": ["3.12", "3.11", "3.10", "latest"],
            "Node.js": ["20", "18", "16", "latest"],
            "Nginx": ["1.24", "1.22", "latest"],
            "Redis": ["7.2", "7.0", "latest"],
            "PostgreSQL": ["16", "15", "14", "latest"],
            "MySQL": ["8.2", "8.0", "latest"],
            "MongoDB": ["7.0", "6.0", "latest"]
        }
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Container Name
        name_group = QGroupBox("Container Name")
        name_layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter container name (optional)")
        name_layout.addWidget(self.name_input)
        name_group.setLayout(name_layout)
        main_layout.addWidget(name_group)
        
        # Image Selection Group
        image_group = QGroupBox("Docker Image")
        image_layout = QVBoxLayout()
        
        # Image type selection
        type_widget = QWidget()
        type_layout = QHBoxLayout(type_widget)
        type_layout.addWidget(QLabel("Image Type:"))
        self.image_type = QComboBox()
        self.image_type.addItems(self.image_versions.keys())
        self.image_type.currentTextChanged.connect(self.update_versions)
        type_layout.addWidget(self.image_type)
        image_layout.addWidget(type_widget)
        
        # Version selection
        version_widget = QWidget()
        version_layout = QHBoxLayout(version_widget)
        version_layout.addWidget(QLabel("Version:"))
        self.version_combo = QComboBox()
        version_layout.addWidget(self.version_combo)
        image_layout.addWidget(version_widget)
        
        # Image preview
        preview_widget = QWidget()
        preview_layout = QHBoxLayout(preview_widget)
        preview_layout.addWidget(QLabel("Selected Image:"))
        self.preview_label = QLabel()
        preview_layout.addWidget(self.preview_label)
        image_layout.addWidget(preview_widget)
        
        image_group.setLayout(image_layout)
        main_layout.addWidget(image_group)
        
        # Custom image option
        custom_group = QGroupBox("Custom Image")
        custom_layout = QVBoxLayout()
        self.custom_check = QCheckBox("Use custom image")
        self.custom_check.stateChanged.connect(self.toggle_custom)
        custom_layout.addWidget(self.custom_check)
        
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter custom image (e.g., python:3.9-slim)")
        self.custom_input.setEnabled(False)
        custom_layout.addWidget(self.custom_input)
        custom_group.setLayout(custom_layout)
        main_layout.addWidget(custom_group)
        
        # Add snapshot selection
        snapshot_group = QGroupBox("Use Snapshot")
        snapshot_layout = QVBoxLayout()
        
        self.snapshot_check = QCheckBox("Create from snapshot")
        self.snapshot_check.stateChanged.connect(self.toggle_snapshot)
        snapshot_layout.addWidget(self.snapshot_check)
        
        self.snapshot_combo = QComboBox()
        self.snapshot_combo.setEnabled(False)
        self.refresh_snapshots()
        snapshot_layout.addWidget(self.snapshot_combo)
        
        snapshot_group.setLayout(snapshot_layout)
        main_layout.addWidget(snapshot_group)
        
        # Dockerfile option
        dockerfile_group = QGroupBox("Dockerfile")
        dockerfile_layout = QVBoxLayout()
        self.dockerfile_check = QCheckBox("Use Dockerfile")
        self.dockerfile_check.stateChanged.connect(self.toggle_dockerfile)
        dockerfile_layout.addWidget(self.dockerfile_check)
        
        self.dockerfile_input = QLineEdit()
        self.dockerfile_input.setPlaceholderText("Select Dockerfile")
        self.dockerfile_input.setEnabled(False)
        dockerfile_layout.addWidget(self.dockerfile_input)
        
        self.dockerfile_btn = QPushButton("Browse")
        self.dockerfile_btn.setEnabled(False)
        self.dockerfile_btn.clicked.connect(self.browse_dockerfile)
        dockerfile_layout.addWidget(self.dockerfile_btn)
        
        self.dockerfile_text = QTextEdit()
        self.dockerfile_text.setPlaceholderText("Or enter Dockerfile content here")
        self.dockerfile_text.setEnabled(False)
        dockerfile_layout.addWidget(self.dockerfile_text)
        
        dockerfile_group.setLayout(dockerfile_layout)
        main_layout.addWidget(dockerfile_group)
        
        # Buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addWidget(button_widget)
        
        # Initialize version combo
        self.update_versions(self.image_type.currentText())
        
        self.setMinimumWidth(400)

    def update_versions(self, image_type):
        self.version_combo.clear()
        if image_type in self.image_versions:
            self.version_combo.addItems(self.image_versions[image_type])
            self.update_preview()

    def update_preview(self):
        if not self.custom_check.isChecked():
            image_type = self.image_type.currentText().lower()
            version = self.version_combo.currentText()
            
            # Special case for Node.js
            if image_type == "node.js":
                image_type = "node"
            
            self.preview_label.setText(f"{image_type}:{version}")
        else:
            self.preview_label.setText(self.custom_input.text())

    def toggle_custom(self, state):
        self.custom_input.setEnabled(state)
        self.image_type.setEnabled(not state)
        self.version_combo.setEnabled(not state)
        if state:
            self.preview_label.setText(self.custom_input.text())
        else:
            self.update_preview()

    def refresh_snapshots(self):
        self.snapshot_combo.clear()
        for container_id, snapshot in self.parent.snapshots.items():
            try:
                container = self.parent.client.containers.get(container_id)
                self.snapshot_combo.addItem(
                    f"{container.name} ({snapshot.short_id})",
                    userData=snapshot.id
                )
            except:
                continue

    def toggle_snapshot(self, state):
        self.snapshot_combo.setEnabled(state)
        self.image_type.setEnabled(not state)
        self.version_combo.setEnabled(not state)
        self.custom_check.setEnabled(not state)
        self.custom_input.setEnabled(not state and self.custom_check.isChecked())

    def toggle_dockerfile(self, state):
        self.dockerfile_input.setEnabled(state)
        self.dockerfile_btn.setEnabled(state)
        self.dockerfile_text.setEnabled(state)
        self.image_type.setEnabled(not state)
        self.version_combo.setEnabled(not state)
        self.custom_check.setEnabled(not state)
        self.custom_input.setEnabled(not state and self.custom_check.isChecked())
        self.snapshot_check.setEnabled(not state)
        self.snapshot_combo.setEnabled(not state and self.snapshot_check.isChecked())

    def browse_dockerfile(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Dockerfile", "", "Dockerfile (*.dockerfile);;All Files (*)", options=options)
        if file_path:
            self.dockerfile_input.setText(file_path)
            with open(file_path, 'r') as file:
                self.dockerfile_text.setPlainText(file.read())

    def get_container_info(self):
        name = self.name_input.text() if self.name_input.text() else None
        
        if self.dockerfile_check.isChecked():
            dockerfile_path = self.dockerfile_input.text()
            dockerfile_content = self.dockerfile_text.toPlainText()
            return name, dockerfile_path, dockerfile_content, True
        
        if self.snapshot_check.isChecked():
            image = self.snapshot_combo.currentData()
        elif self.custom_check.isChecked() and self.custom_input.text():
            image = self.custom_input.text()
        else:
            image_type = self.image_type.currentText().lower()
            if image_type == "node.js":
                image_type = "node"
            version = self.version_combo.currentText()
            image = f"{image_type}:{version}"
        
        return name, image, None, False

    def refresh_container_cards(self):
        # Clear existing cards
        for i in reversed(range(self.container_cards.count())):
            widget = self.container_cards.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        # Add container cards
        for container in self.client.containers.list(all=True):
            card_widget = QWidget()
            card_layout = QHBoxLayout(card_widget)
            
            name_label = QLabel(container.name)
            card_layout.addWidget(name_label)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedWidth(60)
            edit_btn.clicked.connect(lambda _, c=container: self.edit_container(c))
            card_layout.addWidget(edit_btn)
            
            stop_btn = QPushButton("Stop")
            stop_btn.setFixedWidth(60)
            stop_btn.setStyleSheet("background-color: yellow;")
            stop_btn.clicked.connect(lambda _, c=container: self.stop_container(c.name))
            card_layout.addWidget(stop_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedWidth(60)
            delete_btn.setStyleSheet("background-color: red; color: white;")
            delete_btn.clicked.connect(lambda _, c=container: self.delete_container(c.name))
            card_layout.addWidget(delete_btn)
            
            self.container_cards.addWidget(card_widget)
            self.container_cards.update()

    def edit_container(self, container):
        # Logic to edit container
        pass

    def delete_container(self, container_name=None):
        if container_name is None:
            container_name = self.name_input.text()
        if container_name:
            try:
                container = self.client.containers.get(container_name)
                container.remove(force=True)
                QMessageBox.information(self, "Success", f"Container '{container_name}' deleted successfully.")
                self.refresh_container_cards()
            except docker.errors.NotFound:
                QMessageBox.warning(self, "Error", f"Container '{container_name}' not found.")
            except docker.errors.APIError as e:
                QMessageBox.critical(self, "Error", f"Failed to delete container '{container_name}': {e}")
        else:
            QMessageBox.warning(self, "Error", "Please enter the container name to delete.")

    def stop_container(self, container_name=None):
        if container_name is None:
            container_name = self.name_input.text()
        if container_name:
            try:
                container = self.client.containers.get(container_name)
                container.stop()
                QMessageBox.information(self, "Success", f"Container '{container_name}' stopped successfully.")
                self.refresh_container_cards()
            except docker.errors.NotFound:
                QMessageBox.warning(self, "Error", f"Container '{container_name}' not found.")
            except docker.errors.APIError as e:
                QMessageBox.critical(self, "Error", f"Failed to stop container '{container_name}': {e}")
        else:
            QMessageBox.warning(self, "Error", "Please enter the container name to stop.")
