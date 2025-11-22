"""
ターゲット画像の管理モジュール
"""

import os
import json
import uuid
from PIL import Image, ImageOps

from typing import List, Dict, Any
from common.logger import get_logger

logger = get_logger("target")

# 画像保存ディレクトリ
TARGETS_DIR = "assets/targets"

def ensure_targets_dir():
    """ターゲット画像保存ディレクトリが存在しない場合は作成"""
    if not os.path.exists(TARGETS_DIR):
        os.makedirs(TARGETS_DIR)

def ensure_config_dir():
    """設定ファイルのディレクトリが存在しない場合は作成"""
    config_dir = os.path.dirname("TrackTarget/target_config.json")
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)

class TargetManager:
    """ターゲット画像の登録・削除・一覧管理"""
    
    def __init__(self, config_path: str = "TrackTarget/target_config.json"):
        self.config_path = config_path
        self.targets_config: List[Dict[str, Any]] = self._load_config()
        
    def _load_config(self) -> List[Dict[str, Any]]:
        """設定ファイルをロード（存在しない場合は初期化）"""
        ensure_targets_dir()
        ensure_config_dir()
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('targets', [])
        except (FileNotFoundError, json.JSONDecodeError):
            # ファイルが存在しないか、JSONが不正な場合
            return []
    
    def _save_config(self):
        """設定ファイルを保存"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}
        
        config['targets'] = self.targets_config
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    
    def register_image(self, src_path: str) -> str:
        """
        画像を登録し、100x100pxにリサイズして保存
        
        Args:
            src_path (str): 元画像のパス
            
        Returns:
            str: 登録された画像のファイル名（UUID）
            
        Raises:
            Exception: 画像処理エラー
        """
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {src_path}")

        try:
            # PILで画像を開く
            with Image.open(src_path) as img:
                # EXIF の向き情報を自動補正
                img = ImageOps.exif_transpose(img)

                # 100x100にリサイズ（アスペクト比を維持して中央を切り抜く）
                img = img.convert("RGBA")  # RGBA形式に変換

                # 中央を切り抜いて正方形にする
                width, height = img.size
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                right = left + size
                bottom = top + size

                img_cropped = img.crop((left, top, right, bottom))

                # リサイズ（100x100）
                img_resized = img_cropped.resize((100, 100), Image.Resampling.LANCZOS)

                # 保存形式と拡張子を決定
                src_ext = os.path.splitext(src_path)[1].lower()
                if src_ext in (".jpg", ".jpeg"):
                    ext = ".jpg"
                    save_format = "JPEG"
                    img_resized = img_resized.convert("RGB")  # JPEG 用に RGB に変換
                else:
                    ext = ".png"
                    save_format = "PNG"

                # UUIDを生成して保存
                file_uuid = str(uuid.uuid4())
                filename = f"{file_uuid}{ext}"
                full_path = os.path.join(TARGETS_DIR, filename)

                if save_format == "JPEG":
                    img_resized.save(full_path, save_format, quality=95)
                else:
                    img_resized.save(full_path, save_format)

                # 設定に追加
                target_info = {
                    "name": filename,
                    "original_path": src_path,
                    "registered_at": str(uuid.uuid4())  # 現在時刻を代入するか、datetime.now() を使う
                }
                self.targets_config.append(target_info)
                self._save_config()

                logger.info(f"ターゲット画像が登録されました: {filename}")
                return filename

        except Exception as e:
            logger.error(f"画像登録エラー: {e}")
            raise
    
    def delete_image(self, name: str) -> bool:
        """
        登録された画像を削除
        
        Args:
            name (str): 削除する画像のファイル名
            
        Returns:
            bool: 削除成功 여부
        """
        try:
            # 設定から削除
            target_info = None
            for i, info in enumerate(self.targets_config):
                if info["name"] == name:
                    target_info = info
                    self.targets_config.pop(i)
                    break
            
            if not target_info:
                logger.warning(f"削除対象画像が見つかりません: {name}")
                return False
            
            # ファイルを削除
            full_path = os.path.join(TARGETS_DIR, name)
            if os.path.exists(full_path):
                os.remove(full_path)
            
            self._save_config()
            logger.info(f"ターゲット画像が削除されました: {name}")
            return True
            
        except Exception as e:
            logger.error(f"画像削除エラー: {e}")
            return False
    
    def list_targets(self) -> List[Dict[str, Any]]:
        """
        登録されたターゲット一覧を取得
        
        Returns:
            List[Dict]: ターゲット情報のリスト
        """
        return self.targets_config.copy()

    def set_active_target(self, name: str) -> bool:
        """指定した画像を現在のターゲットとして設定"""
        if not any(t["name"] == name for t in self.targets_config):
            logger.warning(f"Active target 設定失敗、対象が見つからない: {name}")
            return False
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}
        config['active_target'] = name
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info(f"Active target 設定: {name}")
        return True

    def get_active_target(self) -> str | None:
        """現在設定されているターゲット画像名を取得"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('active_target')
        except (FileNotFoundError, json.JSONDecodeError):
            return None
