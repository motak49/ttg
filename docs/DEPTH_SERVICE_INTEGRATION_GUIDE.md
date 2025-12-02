# DepthService他ゲーム統合ガイド

## 概要

このドキュメントは、プロジェクト内の他のゲーム/ビューアに対して `DepthMeasurementService` と `DepthStorageService` を統合するための標準的なパターンと実装例を提供します。

---

## 統合パターン（3ステップ）

### ステップ 1: インポート追加

ゲームモジュール（e.g., `frontend/xxx_game.py` または `frontend/xxx_viewer.py`）の先頭に以下を追加：

```python
from common.depth_service import DepthMeasurementService, DepthConfig as DepthServiceConfig
from common.depth_storage import DepthStorageService  # 必要に応じて
```

### ステップ 2: サービス初期化

`__init__` メソッド内で以下を実行：

```python
def __init__(self, camera_manager: CameraManager, ...):
    # 既存のコンポーネント初期化
    self.camera_manager = camera_manager
    # ... 他のコンポーネント ...
    
    # DepthService 設定（推奨デフォルト値）
    depth_config = DepthServiceConfig(
        min_valid_depth_m=0.5,           # 最小有効深度
        max_valid_depth_m=5.0,           # 最大有効深度
        interpolation_radius=10          # 補間探索半径(ピクセル)
    )
    
    # DepthMeasurementService 初期化
    self.depth_measurement_service = DepthMeasurementService(
        camera_manager,
        depth_config
    )
    
    # オプション: DepthStorageService（深度ログ保存が必要な場合）
    self.depth_storage_service = DepthStorageService()  # ScreenDepthLogs/depth_log.json を自動使用
```

**重要**: `camera_manager` は既に初期化済みである必要があります。

### ステップ 3: ゲームループ内での使用

ゲームループ（通常は `_update_frame()` または `update_frame()` メソッド）内で：

```python
def update_frame(self) -> None:
    """フレーム更新メソッド"""
    try:
        # フレーム取得
        frame = self.camera_manager.get_frame()
        if not isinstance(frame, np.ndarray):
            return
        
        # ボール位置を検出
        ball_pos = self.ball_tracker.get_last_detected_position()
        if ball_pos is not None:
            ball_x, ball_y = ball_pos
            
            # ボール位置での深度を測定
            depth_m = self.depth_measurement_service.measure_at_rgb_coords(ball_x, ball_y)
            
            # 信頼度スコアを取得（オプション）
            confidence = self.depth_measurement_service.get_confidence_score(ball_x, ball_y)
            
            # 深度が有効な場合の処理
            if depth_m > 0:
                # ゲームロジック内で深度を使用
                # 例: 当たり判定、スコア計算など
                print(f"深度: {depth_m:.2f}m (信頼度: {confidence:.2f})")
                
                # オプション: 深度を保存
                self.depth_storage_service.save(
                    depth_m, 
                    source="game_measurement",
                    confidence=confidence
                )
    
    except Exception as e:
        print(f"フレーム更新エラー: {e}")
```

---

## API リファレンス

### DepthMeasurementService

#### `measure_at_rgb_coords(x: int, y: int) → float`

**説明**: RGB画像座標で深度を測定

**パラメータ**:
- `x`: RGB画像のX座標（0-1280）
- `y`: RGB画像のY座標（0-800）

**戻り値**: 深度（メートル単位）。無効な場合は -1.0 を返す

**例**:
```python
depth_m = service.measure_at_rgb_coords(640, 400)
if depth_m > 0:
    print(f"Depth: {depth_m:.2f} meters")
```

#### `measure_at_region(x1: int, y1: int, x2: int, y2: int, mode: str = 'mean') → float`

**説明**: 矩形領域内の深度統計値を取得

**パラメータ**:
- `x1, y1, x2, y2`: RGB画像上の矩形座標
- `mode`: 統計モード（"mean", "median", "max", "min"）

**戻り値**: 領域内の統計値（メートル単位）

**例**:
```python
# ボール周辺10px×10pxの平均深度
region_depth = service.measure_at_region(
    x1=640-5, y1=400-5, 
    x2=640+5, y2=400+5,
    mode='mean'
)
```

#### `get_confidence_score(x: int, y: int) → float`

**説明**: 深度測定の信頼度スコアを計算

**パラメータ**:
- `x, y`: RGB画像座標

**戻り値**: 信頼度スコア（0.0～1.0）
- 1.0: 非常に信頼性が高い
- 0.5: 中程度
- 0.0: 信頼性が低い

**例**:
```python
confidence = service.get_confidence_score(640, 400)
if confidence > 0.8:
    print("High confidence measurement")
```

#### `is_valid_depth(depth_m: float) → bool`

**説明**: 深度が有効範囲内かを確認

**パラメータ**:
- `depth_m`: 深度（メートル単位）

**戻り値**: True（有効範囲内）/ False（範囲外）

**例**:
```python
if service.is_valid_depth(depth_m):
    # 深度を使用したゲームロジック
    process_game_with_depth(depth_m)
```

#### `get_statistics() → dict`

**説明**: サービスの使用統計情報を取得

**戻り値**: 以下のキーを含む辞書
```python
{
    'total_measurements': int,      # 総測定回数
    'cache_hits': int,              # キャッシュ使用回数
    'cache_hit_rate': float,        # キャッシュ使用率（0.0-1.0）
    'last_valid_depth_m': float     # 最後の有効深度
}
```

**例**:
```python
stats = service.get_statistics()
print(f"Measurements: {stats['total_measurements']}")
print(f"Cache hit rate: {stats['cache_hit_rate']*100:.1f}%")
```

### DepthStorageService

#### `save(depth_m: float, source: str = 'manual', confidence: float = 1.0) → bool`

**説明**: 深度をJSON形式で保存

**パラメータ**:
- `depth_m`: 深度（メートル単位）
- `source`: データソース（"manual", "game_measurement"など）
- `confidence`: 信頼度スコア（0.0-1.0）

**戻り値**: 保存成功時 True、失敗時 False

**例**:
```python
success = service.save(
    depth_m=2.15,
    source="ox_game_measurement",
    confidence=0.92
)
```

#### `load() → Optional[float]`

**説明**: 保存された深度を読み込み

**戻り値**: 深度（メートル単位）、ファイルなし時は None

**例**:
```python
saved_depth = service.load()
if saved_depth is not None:
    print(f"Saved depth: {saved_depth:.2f}m")
```

#### `load_full_metadata() → Optional[dict]`

**説明**: メタデータを含む完全なJSON情報を取得

**戻り値**: 以下の構造を持つ辞書、またはファイルなし時は None
```python
{
    'screen_depth': float,      # 深度（メートル単位）
    'timestamp': str,           # ISO形式タイムスタンプ
    'source': str,              # データソース
    'confidence': float         # 信頼度スコア
}
```

**例**:
```python
metadata = service.load_full_metadata()
if metadata:
    print(f"Depth: {metadata['screen_depth']:.2f}m")
    print(f"Measured at: {metadata['timestamp']}")
    print(f"Confidence: {metadata['confidence']:.2f}")
```

---

## 実装例

### 例1: シンプルなボール検出ゲーム

```python
class SimpleGame(QMainWindow):
    def __init__(self, camera_manager, screen_manager, ball_tracker):
        super().__init__()
        self.camera_manager = camera_manager
        self.ball_tracker = ball_tracker
        
        # DepthService 初期化
        depth_config = DepthServiceConfig(
            min_valid_depth_m=0.3,
            max_valid_depth_m=10.0,
            interpolation_radius=15
        )
        self.depth_service = DepthMeasurementService(camera_manager, depth_config)
        
        # UI設定
        self.setup_ui()
    
    def update_frame(self):
        frame = self.camera_manager.get_frame()
        ball_pos = self.ball_tracker.get_last_detected_position()
        
        if ball_pos:
            ball_x, ball_y = ball_pos
            depth = self.depth_service.measure_at_rgb_coords(ball_x, ball_y)
            
            # ゲームロジック
            if depth > 1.0:  # 1.0m より奥のボール
                self.on_ball_far()
            elif depth < 0.5:  # 0.5m より手前のボール
                self.on_ball_close()
```

### 例2: 深度ログを記録するゲーム

```python
class LoggingGame(QMainWindow):
    def __init__(self, camera_manager, screen_manager, ball_tracker):
        super().__init__()
        self.camera_manager = camera_manager
        self.ball_tracker = ball_tracker
        
        # サービス初期化
        self.depth_measurement = DepthMeasurementService(
            camera_manager,
            DepthServiceConfig()
        )
        self.depth_storage = DepthStorageService()
    
    def on_collision(self):
        """当たり時に深度を記録"""
        ball_pos = self.ball_tracker.get_last_detected_position()
        if ball_pos:
            x, y = ball_pos
            depth = self.depth_measurement.measure_at_rgb_coords(x, y)
            confidence = self.depth_measurement.get_confidence_score(x, y)
            
            # ファイルに記録
            self.depth_storage.save(depth, "collision", confidence)
```

---

## トラブルシューティング

### 深度が -1.0 を返す

**原因**: 
- 座標がフレーム範囲外
- 深度フレームが無効

**解決**:
```python
depth = service.measure_at_rgb_coords(x, y)
if depth > 0:
    # 深度を使用
else:
    # キャッシュまたはデフォルト値を使用
    cached_depth = service.get_statistics()['last_valid_depth_m']
```

### 信頼度スコアが常に低い

**原因**: 
- ボール位置周辺で深度が一貫していない
- インターポレーション設定が厳しい

**解決**:
```python
depth_config = DepthServiceConfig(
    interpolation_radius=15  # より広い探索半径
)
```

### パフォーマンス低下

**原因**: 
- 毎フレーム大量の測定
- `measure_at_region` で大きな領域を指定

**解決**:
```python
# フレームスキップを使用
if frame_count % 2 == 0:  # 2フレームごとに測定
    depth = service.measure_at_rgb_coords(x, y)
```

---

## ベストプラクティス

1. **サービスの再初期化を避ける**: `__init__` で1度だけ初期化
2. **例外処理を追加**: `try-except` でラップ
3. **統計情報をログ**: デバッグ時に `get_statistics()` を活用
4. **信頼度をチェック**: `confidence > 0.7` 以上で判定
5. **テストを作成**: 各ゲームの統合テストを追加

---

## 次のステップ

- 他のゲーム（トリック・スタント系など）に統合
- 深度ベースのゲームロジック拡張（難易度調整など）
- リアルタイム統計情報をUI表示
- キャリブレーション機能の追加

