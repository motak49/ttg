"""
ターゲット編集ダイアログ
- 一覧表示（サムネイル付き）
- 選択画像の削除
- 現在使用中のターゲット設定
"""

import os

from PyQt6.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

from backend.target_manager import TargetManager


class MovingTargetEditDialog(QDialog):
    """ターゲット画像の編集・削除・選択ダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ターゲット編集")
        self.resize(500, 400)

        # ターゲット管理インスタンス
        self.target_manager = TargetManager()

        # UI コンポーネント
        self.list_widget = QListWidget()
        self.delete_btn = QPushButton("削除")
        self.set_active_btn = QPushButton("現在のターゲットに設定")
        self.close_btn = QPushButton("閉じる")

        # シグナル接続
        self.delete_btn.clicked.connect(self.delete_selected)
        self.set_active_btn.clicked.connect(self.set_active_selected)
        self.close_btn.clicked.connect(self.reject)

        # レイアウト構築
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.set_active_btn)
        btn_layout.addWidget(self.close_btn)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.list_widget)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

        # 初期データロード
        self.populate_list()

    def populate_list(self):
        """登録済みターゲットを一覧表示（サムネイル付き）"""
        self.list_widget.clear()
        active_name = self.target_manager.get_active_target()

        for target in self.target_manager.list_targets():
            name = target["name"]
            item_text = f"{name}"
            if active_name == name:
                item_text += " (active)"

            item = QListWidgetItem(item_text)

            # サムネイルをアイコンとして設定
            img_path = os.path.join("assets", "targets", name)
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                item.setIcon(QIcon(pixmap))

            self.list_widget.addItem(item)

    def delete_selected(self):
        """選択された画像を削除"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "削除する画像を選択してください。")
            return

        for item in selected_items:
            # 「 (active)」が付いている場合は除去して実際のファイル名にする
            name = item.text().replace(" (active)", "")
            success = self.target_manager.delete_image(name)
            if success:
                self.list_widget.takeItem(self.list_widget.row(item))

        # 削除後、一覧とアクティブ表示を更新
        self.populate_list()

    def set_active_selected(self):
        """選択された画像を現在のターゲットとして設定"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "設定する画像を選択してください。")
            return

        name = selected_items[0].text().replace(" (active)", "")
        self.target_manager.set_active_target(name)
        QMessageBox.information(
            self,
            "完了",
            f"{name} を現在のターゲットに設定しました。",
        )
        # アクティブ表示を更新
        self.populate_list()
