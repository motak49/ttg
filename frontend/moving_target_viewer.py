"""
動くターゲットを表示するウィンドウ
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QTimer
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
from backend.moving_target_manager import MovingTargetManager
import cv2
from pathlib import Path
import os
from backend.target_manager import TargetManager

class MovingTargetViewer(QMainWindow):
    """動くターゲットを表示するウィンドウ"""
    
    def __init__(
        self,
        camera_manager: CameraManager,
        screen_manager: ScreenManager,
        ball_tracker: BallTracker
    ):
        super().__init__()
        self.setWindowTitle("動くターゲット表示")
        self.setGeometry(100, 100, 800, 600)
        
        # コンポーネントの保持
        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        self.ball_tracker = ball_tracker
        
        # 動くターゲット管理
        self.moving_target_manager = MovingTargetManager(screen_manager)
        
        # カメラフレーム表示用ラベル
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # レイアウト設定
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # タイマー設定（FPSに合わせて更新）
        from common.config import TARGET_FPS
        self.timer_interval = 1000 // TARGET_FPS  # ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(self.timer_interval)
        
        # 初期化
        self.is_initialized = False
        self.initialize()
    
    def initialize(self):
        """初期化処理"""
        try:
            # 移動範囲を読み込み
            if not self.moving_target_manager.load_bounds():
                QMessageBox.warning(self, "警告", "移動範囲の読み込みに失敗しました")
                return

            # アクティブターゲット取得
            target_manager = TargetManager()
            active_name = target_manager.get_active_target()

            if active_name:
                default_image = os.path.join("assets", "targets", active_name)
            else:
                # フォールバック: 既存のハードコード画像（存在すれば使用）またはスキップ
                fallback_path = "assets/targets/1876bdbb-9365-42aa-9277-54bad2a98411.png"
                default_image = fallback_path if os.path.exists(fallback_path) else None

            # デフォルト画像が取得できたらターゲット追加
            if default_image and Path(default_image).exists():
                self.moving_target_manager.add_target(default_image)
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    f"デフォルト画像が見つかりません: {default_image or 'None'}"
                )
                # ここでターゲット追加はスキップ
                print("デフォルト画像が見つからないため、ターゲットを追加しません。")
            
            print("動くターゲットビューアーが初期化されました")
            self.is_initialized = True
            
        except Exception as e:
            print(f"初期化エラー: {e}")
            QMessageBox.critical(self, "エラー", f"初期化に失敗しました: {e}")
    
    def update_frame(self) -> None:
        """フレームを更新"""
        if not self.is_initialized:
            return
            
        try:
            # カメラからフレームを取得
            frame = self.camera_manager.get_frame()
            if frame is None:
                print("カメラフレームの取得に失敗しました")
                return
                
            # 動くターゲットを更新
            self.moving_target_manager.update_all()
            
            # ボール位置を取得して衝突判定
            ball_pos = self.ball_tracker.get_last_detected_position()
            if ball_pos is not None:
                collisions = self.moving_target_manager.check_ball_collision(ball_pos)
                if collisions:
                    QMessageBox.information(self, "当たり！", "ボールがターゲットに当たった！")
            
            # フレームにターゲットを描画
            annotated_frame = self._draw_targets(frame)
            
            # 画像を表示
            self._display_frame(annotated_frame)
            
        except Exception as e:
            print(f"フレーム更新エラー: {e}")
    
    def _draw_targets(self, frame) -> QImage:
        """ターゲットをフレームに描画"""
        try:
            # 画像をQImageに変換
            height, width = frame.shape[:2]
            
            # RGBからBGRへ変換（OpenCVの形式）
            if len(frame.shape) == 3:
                bgr_frame = frame[:, :, ::-1]  # BGRに変換
            else:
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
            # NumPy配列をbytesに変換してQImageに渡す
            bytes_per_line = width * 3
            qimage = QImage(
                bgr_frame.tobytes(),
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_BGR888
            )
            
            # QPainterで描画
            painter = QPainter(qimage)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 動くターゲットを描画
            targets = self.moving_target_manager.get_targets()
            for target in targets:
                x, y = target.position
                # 画像ファイルから読み込み、リサイズして描画
                try:
                    # プロジェクトルートからの絶対パス取得
                    project_root = Path(__file__).resolve().parents[1]   # frontend の上位がプロジェクトルート
                    img_path = (project_root / target.image_path).as_posix()
                    
                    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        # ターゲット表示サイズ（例: 100x100px）
                        target_size = 100
                        resized_img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)
                        
                        # BGRからRGBに変換
                        if len(resized_img.shape) == 3:
                            rgb_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
                        else:
                            rgb_img = cv2.cvtColor(resized_img, cv2.COLOR_GRAY2RGB)
                        
                        # QImageに変換
                        bytes_per_line = target_size * 3
                        qimage_target = QImage(
                            rgb_img.tobytes(),
                            target_size,
                            target_size,
                            bytes_per_line,
                            QImage.Format.Format_RGB888
                        )
                        painter.drawImage(x, y, qimage_target)
                    else:
                        # 画像読み込み失敗時は矩形描画をフォールバック
                        print(f"画像読み込み失敗: {img_path}")  # 一度だけ警告
                        painter.setPen(QPen(QColor(255, 0, 0), 2))
                        painter.drawRect(x, y, 100, 100)
                except Exception as e:
                    print(f"画像描画エラー: {e}")
                    # エラー時は矩形描画をフォールバック
                    painter.setPen(QPen(QColor(255, 0, 0), 2))
                    painter.drawRect(x, y, 100, 100)
                
            painter.end()
            
            return qimage
            
        except Exception as e:
            print(f"描画エラー: {e}")
            return QImage()
    
    def _display_frame(self, qimage):
        """フレームをラベルに表示"""
        try:
            if not qimage.isNull():
                pixmap = QPixmap.fromImage(qimage)
                self.image_label.setPixmap(pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
        except Exception as e:
            print(f"表示エラー: {e}")
    
    def closeEvent(self, a0):
        """ウィンドウクローズ時の処理"""
        self.timer.stop()
        print("動くターゲットビューアーが閉じられました")
