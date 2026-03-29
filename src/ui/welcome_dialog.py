# welcome_dialog.py
import os
import sys
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QCheckBox, QLineEdit, QFileDialog,
                               QFrame, QMessageBox)
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtCore import Qt

class WelcomeDialog(QDialog):
    """首次启动欢迎对话框"""
    
    def __init__(self, parent=None, language_manager=None):
        super().__init__(parent)
        self.language_manager = language_manager
        self.install_path = os.path.dirname(os.path.dirname(__file__))
        self.create_shortcut = True
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(self.language_manager.get_text("welcome_title"))
        self.setFixedSize(500, 450)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 大图标
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'Clippot.png')
        if os.path.exists(icon_path):
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(scaled_pixmap)
            icon_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon_label)
        
        # 欢迎标题
        title_label = QLabel(self.language_manager.get_text("welcome_title"))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #333333; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 绿色软件说明
        desc_label = QLabel(self.language_manager.get_text("portable_software_desc"))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 13px; line-height: 1.6;")
        layout.addWidget(desc_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0; max-height: 1px;")
        layout.addWidget(separator)
        
        # 桌面快捷方式选项
        self.shortcut_check = QCheckBox(self.language_manager.get_text("create_desktop_shortcut"))
        self.shortcut_check.setChecked(True)
        layout.addWidget(self.shortcut_check)
        
        # 安装路径选择
        path_label = QLabel(self.language_manager.get_text("install_location"))
        path_label.setStyleSheet("color: #333333; font-size: 13px; font-weight: bold;")
        layout.addWidget(path_label)
        
        path_layout = QHBoxLayout()
        path_layout.setSpacing(10)
        
        self.path_edit = QLineEdit(self.install_path)
        self.path_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: #FFFFFF;
                color: #333333;
            }
            QLineEdit:focus {
                border-color: #4A90E2;
                outline: none;
            }
        """)
        path_layout.addWidget(self.path_edit)
        
        browse_button = QPushButton(self.language_manager.get_text("browse"))
        browse_button.setFixedWidth(80)
        browse_button.setFixedHeight(36)
        browse_button.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2A6496;
            }
        """)
        browse_button.clicked.connect(self.on_browse)
        path_layout.addWidget(browse_button)
        
        layout.addLayout(path_layout)
        
        layout.addStretch()
        
        # 开始使用按钮
        self.start_button = QPushButton(self.language_manager.get_text("start_using"))
        self.start_button.setFixedHeight(45)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2A6496;
            }
        """)
        self.start_button.clicked.connect(self.on_start)
        layout.addWidget(self.start_button)
        
    def on_browse(self):
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.Directory)
        folder_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        
        if folder_dialog.exec():
            selected_folder = folder_dialog.selectedFiles()[0]
            self.path_edit.setText(selected_folder)
            
    def on_start(self):
        self.install_path = self.path_edit.text().strip()
        self.create_shortcut = self.shortcut_check.isChecked()
        
        if not self.install_path:
            QMessageBox.warning(self, self.language_manager.get_text("warning"),
                               self.language_manager.get_text("please_select_path"))
            return
            
        self.accept()
        
    def get_settings(self):
        return {
            'install_path': self.install_path,
            'create_shortcut': self.create_shortcut
        }
