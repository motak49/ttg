"""
深度ストレージサービス（DepthStorageService）

ScreenDepthLogs/depth_log.json への深度値の永続化と読み込みを担当するサービス。

【JSON形式】
{
  "screen_depth": 1.750,           # 深度値（メートル）
  "timestamp": "2025-12-02T...",   # ISO8601形式のタイムスタンプ
  "source": "user_measurement",    # データ源（user_measurement, auto_calibration, etc.）
  "confidence": 0.95               # 信頼度スコア（0.0～1.0）
}

【ファイルパス】
- デフォルト: ScreenDepthLogs/depth_log.json
- 相対パス: プロジェクトルート基準
"""

import json
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime


class DepthStorageService:
    """
    深度値の永続化・読み込みサービス
    
    機能:
    - 深度値を JSON で保存
    - 保存したファイルから読み込み
    - ファイルのクリア・削除
    - 自動ディレクトリ作成
    """
    
    # デフォルトの保存ファイルパス
    DEFAULT_STORAGE_PATH = "ScreenDepthLogs/depth_log.json"
    
    def __init__(self, file_path: Optional[str] = None):
        """
        初期化
        
        Args:
            file_path: 保存先ファイルパス
                      （Noneの場合は DEFAULT_STORAGE_PATH）
        """
        self.file_path = Path(file_path or self.DEFAULT_STORAGE_PATH)
        
        # ★ディレクトリがなければ自動作成
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.info(
            f"[DepthStorageService.__init__] "
            f"ストレージパス: {self.file_path.absolute()}"
        )
    
    def save(
        self, 
        depth_m: float, 
        source: str = "user_measurement",
        confidence: float = 1.0
    ) -> bool:
        """
        深度値をJSONファイルに保存
        
        Args:
            depth_m: 深度値（メートル）
            source: データ源（デフォルト: "user_measurement"）
            confidence: 信頼度スコア（0.0～1.0、デフォルト: 1.0）
            
        Returns:
            bool: 成功時 True、失敗時 False
        """
        try:
            # ★Step 1: 入力値を検証
            if depth_m < 0:
                logging.error(
                    f"[DepthStorageService.save] "
                    f"無効な深度値: {depth_m}"
                )
                return False
            
            # ★Step 2: 信頼度を制限（0.0～1.0）
            confidence = max(0.0, min(1.0, confidence))
            
            # ★Step 3: 保存データを構築
            data: dict[str, Any] = {
                "screen_depth": round(depth_m, 3),  # 小数第3位までに丸め
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "confidence": round(confidence, 2)
            }
            
            # ★Step 4: JSONファイルに書き込み
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(
                f"[DepthStorageService.save] ✓ 保存成功 "
                f"深度={depth_m:.3f}m, 信頼度={confidence:.2f} "
                f"ファイル: {self.file_path}"
            )
            return True
        
        except IOError as e:
            logging.error(
                f"[DepthStorageService.save] ✗ ファイル書き込み失敗: {e}"
            )
            return False
        except Exception as e:
            logging.error(
                f"[DepthStorageService.save] ✗ 予期しないエラー: {e}"
            )
            return False
    
    def load(self) -> Optional[float]:
        """
        保存ファイルから深度値を読み込み
        
        Returns:
            float: 保存された深度値（メートル）
            None: ファイルなし、読み込み失敗、形式エラー時
        """
        try:
            # ★Step 1: ファイルの存在確認
            if not self.file_path.exists():
                logging.info(
                    f"[DepthStorageService.load] "
                    f"ファイルが存在しません: {self.file_path}"
                )
                return None
            
            # ★Step 2: JSONファイルを読み込み
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # ★Step 3: 必須フィールドを取得
            if "screen_depth" not in data:
                logging.error(
                    f"[DepthStorageService.load] "
                    f"'screen_depth' フィールドが見つかりません"
                )
                return None
            
            depth_m = float(data["screen_depth"])
            
            # ★Step 4: データを検証
            if depth_m < 0:
                logging.error(
                    f"[DepthStorageService.load] "
                    f"無効な深度値: {depth_m}"
                )
                return None
            
            # ★追加情報をログに含める（デバッグ用）
            timestamp = data.get("timestamp", "N/A")
            source = data.get("source", "N/A")
            confidence = data.get("confidence", "N/A")
            
            logging.info(
                f"[DepthStorageService.load] ✓ 読み込み成功 "
                f"深度={depth_m:.3f}m, "
                f"ソース={source}, 信頼度={confidence}, "
                f"タイムスタンプ={timestamp}"
            )
            return depth_m
        
        except FileNotFoundError:
            logging.warning(
                f"[DepthStorageService.load] ファイルが見つかりません"
            )
            return None
        except json.JSONDecodeError as e:
            logging.error(
                f"[DepthStorageService.load] ✗ JSON解析エラー: {e}"
            )
            return None
        except (KeyError, ValueError, TypeError) as e:
            logging.error(
                f"[DepthStorageService.load] ✗ データ形式エラー: {e}"
            )
            return None
        except Exception as e:
            logging.error(
                f"[DepthStorageService.load] ✗ 予期しないエラー: {e}"
            )
            return None
    
    def clear(self) -> bool:
        """
        保存ファイルを削除
        
        Returns:
            bool: 成功時 True、失敗時 False
        """
        try:
            if not self.file_path.exists():
                logging.info(
                    f"[DepthStorageService.clear] "
                    f"ファイルは既に削除されています"
                )
                return True
            
            self.file_path.unlink()
            
            logging.info(
                f"[DepthStorageService.clear] ✓ ファイル削除成功: "
                f"{self.file_path}"
            )
            return True
        
        except OSError as e:
            logging.error(
                f"[DepthStorageService.clear] ✗ ファイル削除失敗: {e}"
            )
            return False
        except Exception as e:
            logging.error(
                f"[DepthStorageService.clear] ✗ 予期しないエラー: {e}"
            )
            return False
    
    def load_full_metadata(self) -> Optional[dict[str, Any]]:
        """
        保存ファイル全体（メタデータ含む）を読み込み
        
        デバッグ・ログ表示用
        
        Returns:
            dict: JSON全体（ファイルなし時は None）
        """
        try:
            if not self.file_path.exists():
                return None
            
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            logging.debug(
                f"[DepthStorageService.load_full_metadata] "
                f"メタデータ読み込み成功"
            )
            return data
        
        except Exception as e:
            logging.error(
                f"[DepthStorageService.load_full_metadata] ✗ エラー: {e}"
            )
            return None
    
    def get_file_path(self) -> Path:
        """
        保存先ファイルパスを取得
        
        Returns:
            Path: ファイルパス
        """
        return self.file_path
    
    def get_file_exists(self) -> bool:
        """
        ファイルが存在するかチェック
        
        Returns:
            bool: 存在時 True
        """
        return self.file_path.exists()
