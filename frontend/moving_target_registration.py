"""
動くターゲット登録ダイアログ
"""

import os
from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QLabel, 
    QFileDialog,
    QMessageBox,
    QComboBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from backend.target_manager import TargetManager
from frontend.moving_target_edit_dialog import MovingTargetEditDialog

class MovingTargetRegistrationDialog(QDialog):
    """動くターゲット登録ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("動くターゲット登録")
        self.setModal(True)
        self.resize(400, 300)
        
        # ダイアログのレイアウト
        layout = QVBoxLayout()
        
        # 画像選択エリア
        self.image_label = QLabel("画像を選択してください")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(150)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        
        # ファイル選択ボタン
        self.select_btn = QPushButton("画像を選択")
        self.select_btn.clicked.connect(self.select_image)
        
        # 登録ボタン
        self.register_btn = QPushButton("登録")
        self.register_btn.clicked.connect(self.register_target)
        self.register_btn.setEnabled(False)  # 初期状態では無効
        
        # キャンセルボタン
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.reject)

        # 編集ボタン
        self.edit_btn = QPushButton("編集")
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        
        # レイアウトに追加
        layout.addWidget(self.image_label)
        layout.addWidget(self.select_btn)
        
        # 速度レベル選択用のラベルとコンボボックス
        speed_layout = QHBoxLayout()
        self.speed_label = QLabel("移動速度:")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1 (低速)", "2", "3 (標準)", "4", "5 (高速)"])
        self.speed_combo.setCurrentIndex(2)  # デフォルトは3（標準）
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.speed_combo)
        layout.addLayout(speed_layout)
        
        layout.addWidget(self.register_btn)
        layout.addWidget(self.edit_btn)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        # 選択された画像パス
        self.selected_image_path = None
        
        # ターゲットマネージャー
        self.target_manager = TargetManager()
    
    def select_image(self):
        """画像ファイルを選択"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "画像ファイルを選択",
            "",
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.register_btn.setEnabled(True)
            
            # 選択された画像をプレビュー表示
            pixmap = QPixmap(file_path)
            # 画像をラベルのサイズに合わせてリサイズ
            pixmap = pixmap.scaled(
                self.image_label.width() - 20,
                self.image_label.height() - 20,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
    
    def register_target(self):
        """ターゲットを登録"""
        if not self.selected_image_path:
            QMessageBox.warning(self, "警告", "画像を選択してください。")
            return

        # 選択された速度レベルを取得
        speed_level = self.speed_combo.currentIndex() + 1  # 0-based → 1-based

        try:
            # ターゲットマネージャーで画像を登録
            filename = self.target_manager.register_image(self.selected_image_path)
            
            QMessageBox.information(
                self, 
                "成功", 
                f"ターゲットが正常に登録されました。\nファイル名: {filename}"
            )
            
            # 登録成功後、ダイアログを閉じる
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "エラー", 
                f"ターゲットの登録に失敗しました。\n{str(e)}"
            )

    def open_edit_dialog(self):
        """編集ダイアログを開く"""
        dlg: MovingTargetEditDialog = MovingTargetEditDialog(self)
        dlg.exec()
