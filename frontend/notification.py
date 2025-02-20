from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect, QTimer, QEasingCurve, QObject
from PyQt5.QtGui import QColor

class NotificationWidget(QWidget):
    closed = pyqtSignal()
    
    def __init__(self, title: str, message: str, type: str = "info", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setupUi(title, message, type)
        
    def setupUi(self, title, message, type):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container
        container = QFrame(self)
        container.setObjectName("notificationContainer")
        container_layout = QVBoxLayout(container)
        
        # Style based on type
        colors = {
            "info": "#0984e3",
            "success": "#00b894",
            "error": "#d63031",
            "warning": "#fdcb6e"
        }
        
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }
        
        container.setStyleSheet(f"""
            QFrame#notificationContainer {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e1e1e1;
            }}
        """)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Icon and title
        icon_label = QLabel(icons.get(type, icons['info']))
        icon_label.setStyleSheet(f"""
            font-size: 16px;
            padding: 5px;
            color: {colors.get(type, colors['info'])};
        """)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2d3436;
        """)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #636e72;
                font-size: 18px;
                padding: 0 5px;
            }
            QPushButton:hover {
                color: #2d3436;
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        container_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #e1e1e1;")
        container_layout.addWidget(separator)
        
        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            color: #636e72;
            font-size: 13px;
            padding: 5px;
        """)
        container_layout.addWidget(message_label)
        
        layout.addWidget(container)
        
        # Apply shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 60))
        container.setGraphicsEffect(shadow)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

class NotificationManager(QObject):
    def __init__(self):
        super().__init__()
        self.notifications = []
        self.margin = 20
        
    def show_notification(self, title: str, message: str, type: str = "info"):
        notification = NotificationWidget(title, message, type)
        notification.closed.connect(lambda: self.remove_notification(notification))
        self.notifications.append(notification)
        
        # Set initial position (outside screen)
        screen = QApplication.primaryScreen().availableGeometry()
        notification_width = 300
        notification_height = 100
        
        y = self.margin + (len(self.notifications) - 1) * (notification_height + 10)
        notification.setGeometry(-notification_width, y, notification_width, notification_height)
        notification.show()
        
        # Animate in
        anim = QPropertyAnimation(notification, b"geometry")
        anim.setDuration(300)
        anim.setStartValue(notification.geometry())
        anim.setEndValue(QRect(self.margin, y, notification_width, notification_height))
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        
        # Auto close after 5 seconds
        QTimer.singleShot(5000, lambda: self.close_notification(notification))
    
    def close_notification(self, notification):
        if notification in self.notifications:
            # Animate out
            anim = QPropertyAnimation(notification, b"geometry")
            anim.setDuration(300)
            anim.setStartValue(notification.geometry())
            anim.setEndValue(QRect(-notification.width(), notification.y(),
                                 notification.width(), notification.height()))
            anim.setEasingCurve(QEasingCurve.InCubic)
            anim.finished.connect(notification.close)
            anim.start()
    
    def remove_notification(self, notification):
        if notification in self.notifications:
            self.notifications.remove(notification)
            self.update_positions()
    
    def update_positions(self):
        for i, notification in enumerate(self.notifications):
            y = self.margin + i * (notification.height() + 10)
            
            anim = QPropertyAnimation(notification, b"geometry")
            anim.setDuration(300)
            anim.setStartValue(notification.geometry())
            anim.setEndValue(QRect(self.margin, y,
                                 notification.width(), notification.height()))
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
