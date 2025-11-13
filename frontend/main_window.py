# main_window.py
import sys
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtGui import QCloseEvent
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from frontend.game_area import GameArea
from frontend.ox_game import OxGame
from backend.ball_tracker import BallTracker

from frontend.track_target_viewer import TrackTargetViewer
from frontend.track_target_config import TrackTargetConfig
from frontend.depth_config import DepthConfig

# external_api は外部から BallTracker を取得できるようにするためだけに呼び出す
from backend import external_api
from common.validation import validate_and_create_defaults


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Touch The Golf")
        # 固定サイズにし、リサイズ不可
        self.setFixedSize(800, 600)

        # メインウィジェットとレイアウトの設定
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # ボタン配置用縦レイアウト
        button_layout = QVBoxLayout()

        # カメラ起動ボタン
        camera_start_btn = QPushButton("カメラ起動")
        camera_start_btn.clicked.connect(self.show_camera_start)  # type: ignore
        button_layout.addWidget(camera_start_btn)

        # 領域設定機能ボタン
        set_screen_area_btn = QPushButton("領域設定")
        set_screen_area_btn.clicked.connect(self.show_set_screen_area)  # type: ignore
        button_layout.addWidget(set_screen_area_btn)

        # 領域確認機能ボタン
        get_screen_area_btn = QPushButton("領域確認")
        get_screen_area_btn.clicked.connect(self.show_get_screen_area)  # type: ignore
        button_layout.addWidget(get_screen_area_btn)

        # 深度設定機能ボタン
        set_screen_depth_btn = QPushButton("深度設定")
        set_screen_depth_btn.clicked.connect(self.show_set_screen_depth_window)  # type: ignore
        button_layout.addWidget(set_screen_depth_btn)

        # 深度確認機能ボタン
        get_screen_depth_btn = QPushButton("深度確認")
        get_screen_depth_btn.clicked.connect(self.show_get_screen_depth)  # type: ignore
        button_layout.addWidget(get_screen_depth_btn)

        # トラッキング対象設定・確認ボタン
        track_target_config_btn = QPushButton("トラッキング対象設定・確認")
        track_target_config_btn.clicked.connect(self.show_track_target_config)  # type: ignore
        button_layout.addWidget(track_target_config_btn)

        # 横線（区切り）
        separator = QPushButton("")
        separator.setFixedHeight(10)
        separator.setEnabled(False)  # 非活性化
        button_layout.addWidget(separator)

        # OXゲーム 起動ボタン（他の機能と同じレイアウトに配置）
        ox_game_btn = QPushButton("OXゲーム")
        ox_game_btn.clicked.connect(self.start_ox_game)  # type: ignore
        button_layout.addWidget(ox_game_btn)

        layout.addLayout(button_layout)

        # バックエンドコンポーネントの初期化
        self.camera_manager = CameraManager()
        self.screen_manager = ScreenManager()
        self.ball_tracker = BallTracker(self.screen_manager)
        external_api.set_ball_tracker(self.ball_tracker)

        # キャリブレーションデータをロード
        try:
            import json
            with open("calibration_data.json", "r", encoding="utf-8") as f:
                calib_data = json.load(f)
            self.camera_manager.calibration_data = calib_data
        except Exception as e:
            print(f"キャリブレーションデータ読み込みエラー: {e}")

        # スタイル適用（任意）
        self._apply_styles()

    def _apply_styles(self) -> None:
        """共通スタイルシートを適用"""
        style = """
            QPushButton {
                font-size: 18px;
                padding: 12px;
                min-width: 200px;
                margin: 6px auto;
            }
            QMainWindow {
                background-color: #f5f5f5;
            }
        """
        self.setStyleSheet(style)

    # ----- スクリーン領域関連 -----
    def show_set_screen_area(self) -> None:
        """スクリーン領域設定機能"""
        if not self.camera_manager.is_initialized():
            QMessageBox.critical(
                self,
                "カメラエラー",
                "カメラが初期化されていません。まずアプリを再起動してください。",
            )
            return
        self.game_area_window = GameArea(self.camera_manager, self.screen_manager)
        self.game_area_window.show()

    def show_get_screen_area(self) -> None:
        """現在のスクリーン領域取得"""
        try:
            # ログデータを読み込んでから領域情報を取得
            self.screen_manager.load_log()
            points = self.screen_manager.get_screen_area_points()
            if points is not None:
                points_info = (
                    f"左上: ({points[0][0]}, {points[0][1]}), "
                    f"右上: ({points[1][0]}, {points[1][1]}), "
                    f"左下: ({points[2][0]}, {points[2][1]}), "
                    f"右下: ({points[3][0]}, {points[3][1]})"
                )
                QMessageBox.information(self, "領域確認", f"現在の領域: {points_info}")
            else:
                QMessageBox.information(self, "領域確認", "領域データが設定されていません。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"領域データの読み込みに失敗しました: {e}")

    # ----- スクリーン深度関連 -----
    def show_set_screen_depth(self) -> None:
        """スクリーン深度設定機能"""
        try:
            self.screen_manager.load_log()
            current_depth = int(self.screen_manager.get_screen_depth())
        except Exception as e:
            print(f"深度ログ読み込みエラー: {e}")
            current_depth = 0

        depth, ok = QInputDialog.getInt(
            self,
            "深度設定",
            "深度 (mm):",
            current_depth,
            0,
        )
        if ok:
            self.screen_manager.set_screen_depth(depth)
            QMessageBox.information(self, "深度設定", f"深度を {depth} mm に設定しました。")

    def show_get_screen_depth(self) -> None:
        """現在のスクリーン深度取得"""
        try:
            self.screen_manager.load_log()
            depth = self.screen_manager.get_screen_depth()
            QMessageBox.information(self, "深度確認", f"現在の深度: {depth} mm")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"スクリーンデータの読み込みに失敗しました: {e}")

    def show_set_screen_depth_window(self) -> None:
        """深度設定画面を開く"""
        if not self.camera_manager.is_initialized():
            QMessageBox.critical(
                self,
                "カメラエラー",
                "カメラが初期化されていません。まずアプリを再起動してください。",
            )
            return
        self.depth_config_window = DepthConfig(self.camera_manager, self.screen_manager)
        self.depth_config_window.show()

    # ----- トラッキング対象設定 -----
    def show_set_track_ball(self) -> None:
        """トラッキング対象設定（赤・ピンク）"""
        colors: List[str] = ["赤", "ピンク"]
        color, ok = QInputDialog.getItem(
            self,
            "トラッキング対象設定",
            "色を選択:",
            colors,
            0,
            False,
        )
        if ok:
            self.ball_tracker.set_target_color(color)
            # 設定をファイルに保存
            self.ball_tracker.save_config()
            QMessageBox.information(
                self,
                "トラッキング対象設定",
                f"{color} ボールを追跡対象に設定しました。",
            )

    def show_camera_start(self) -> None:
        """カメラ起動機能"""
        if not self.camera_manager.initialize_camera():
            QMessageBox.critical(
                self,
                "カメラエラー",
                "カメラの初期化に失敗しました。",
            )
            sys.exit(1)
        else:
            # カメラ接続のみ行い、画面表示は行わない
            QMessageBox.information(self, "カメラ起動", "カメラが正常に接続されました。")

    # -------------------------------------------------
    # OXゲーム起動ハンドラ
    # -------------------------------------------------
    def start_ox_game(self) -> None:
        """メインメニューから OX ゲーム（Tick & Cross）を開始する"""
        if not self.camera_manager.is_initialized():
            if not self.camera_manager.initialize_camera():
                QMessageBox.critical(
                    self, "カメラエラー", "カメラの初期化に失敗しました。"
                )
                return
        self.ox_game_window = OxGame(self.camera_manager, self.screen_manager, self.ball_tracker)
        self.ox_game_window.show()

    # -------------------------------------------------
    # ウィンドウクローズ時処理
    # -------------------------------------------------
    def closeEvent(self, a0: Optional[QCloseEvent] = None) -> None:
        """ウィンドウクローズ時にカメラを安全に解放し、例外をログへ出力します"""
        event = a0
        try:
            self.camera_manager.close_camera()
        except Exception as e:
            print(f"カメラ終了時エラー: {e}")
        if event is not None:
            event.accept()

    # -------------------------------------------------
    # トラッキング対象確認機能
    # -------------------------------------------------
    def show_track_target_view(self) -> None:
        """トラッキング対象を確認するウィンドウを開く"""
        if not self.camera_manager.is_initialized():
            QMessageBox.critical(
                self,
                "カメラエラー",
                "カメラが接続されていません。まずアプリを起動してください。",
            )
            return

        self.track_target_viewer = TrackTargetViewer(
            self.camera_manager, self.screen_manager, self.ball_tracker
        )
        self.track_target_viewer.show()

    # -------------------------------------------------
    # 新しいトラッキング対象設定・確認機能
    # -------------------------------------------------
    def show_track_target_config(self) -> None:
        """トラッキング対象を設定・確認するウィンドウを開く"""
        if not self.camera_manager.is_initialized():
            QMessageBox.critical(
                self,
                "カメラエラー",
                "カメラが接続されていません。まずアプリを起動してください。",
            )
            return

        self.track_target_config = TrackTargetConfig(
            self.camera_manager, self.screen_manager, self.ball_tracker
        )
        self.track_target_config.show()


def main() -> None:
    # バリデーションを実行
    validate_and_create_defaults()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
