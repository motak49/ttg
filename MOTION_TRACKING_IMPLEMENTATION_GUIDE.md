# 深度ベース移動物体トラッキング実装ガイド

## 概要

色ベースのボールトラッキングから、深度軸ベースの移動物体検知への仕様変更を段階的に実施するためのガイドです。

**主要な利点:**
- ✅ 照度変動に強い（深度信号は環境光に影響されない）
- ✅ 色依存がない（何色の物体でも検知可能）
- ✅ 背景自動分離（動いていない背景は検知されない）
- ✅ 複数物体対応可能
- ✅ 深度値の直接測定（実時間性高い）

---

## ファイル構成

```
backend/
├── ball_tracker.py              (既存：色ベース)
├── motion_tracker.py            (新規：深度ベース)
├── tracker_selector.py          (新規：モード選択レイヤー)
└── interfaces.py                (既存：インターフェース）

frontend/
├── ox_game.py                   (既存：利用側, 修正不要）
└── ...
```

---

## 実装ステップ

### ステップ1: 新トラッカーの統合（1時間）

**ファイル**: `main.py`, `ox_game.py`

```python
# main.py または ox_game.py の初期化部分で

from backend.motion_tracker import MotionBasedTracker
from backend.tracker_selector import TrackerSelector, TrackerMode

# 既存のカメラマネージャー、スクリーンマネージャーから初期化
camera_manager = CameraManager()
screen_manager = ScreenManager()

# 既存の色ベーストラッカー
from backend.ball_tracker import BallTracker
color_tracker = BallTracker(screen_manager, ...)

# 新しい深度ベーストラッカー
motion_tracker = MotionBasedTracker(screen_manager, camera_manager)
motion_tracker.depth_measurement_service = depth_measurement_service

# セレクター初期化（デフォルト：深度ベース）
tracker_selector = TrackerSelector(
    color_tracker,
    motion_tracker,
    default_mode=TrackerMode.MOTION  # ← ここで選択
)

# ox_game.py で使用
self.ball_tracker = tracker_selector  # または個別に設定
```

### ステップ2: トラッキングモードの選択（設定ファイル化）

**ファイル**: `common/config.py`

```python
# 追加
TRACKER_MODE = "motion"  # "color", "motion", "hybrid"

# または環境変数で
import os
TRACKER_MODE = os.getenv("TRACKER_MODE", "motion")
```

### ステップ3: パラメータ調整（実運用に合わせる）

**ファイル**: `motion_tracker.py` の初期化パラメータ

```python
tracker = MotionBasedTracker(screen_manager, camera_manager)

# 環境に応じた調整
tracker.set_depth_change_threshold(-50.0)      # mm（負の値、より敏感に）
tracker.set_min_motion_area(30)                # ピクセル（小さい物体も検知）

# または UI から動的に調整
tracker.depth_change_threshold_mm = -100.0     # より大きな移動のみ検知
tracker.approach_confidence_threshold = 0.6     # スクリーン向き信頼度上げる
```

---

## 使用シナリオ

### シナリオ1: 深度ベースに完全移行（推奨）

```python
tracker = TrackerSelector(color_tracker, motion_tracker)
tracker.set_mode(TrackerMode.MOTION)

# ox_game で
hit = tracker.check_target_hit(frame)
```

**状況**: 
- 新しいシステムで十分に動作検証できた
- 色トラッキングの問題が顕著
- 深度フレームが安定している

---

### シナリオ2: ハイブリッドモード（安全策）

```python
tracker = TrackerSelector(color_tracker, motion_tracker)
tracker.set_mode(TrackerMode.HYBRID)

# 結果:
# - 深度ベース成功 → 深度ベース採用（優先）
# - 色ベース成功、深度失敗 → 色ベース採用（フォールバック）
# - 両方成功 → 深度ベース採用
```

**状況**:
- 移行期間で両方を試したい
- 色トラッキングがまだ必要
- 信頼性を最大化したい

---

### シナリオ3: A/B テスト

```python
# config.py
AB_TEST_MODE = True  # True = テスト中
TRACKER_MODE_PRIMARY = "motion"
TRACKER_MODE_FALLBACK = "color"

# tracker_selector.py で統計取得
stats = tracker.get_statistics()
# {
#     'color_hit_count': 45,
#     'motion_hit_count': 52,
#     'hybrid_switch_count': 7
# }
```

**状況**:
- 両方の性能を定量的に比較したい
- 環境ごとの最適モードを決定したい

---

## トラッキング動作フロー

### 色ベース（従来）

```
RGB フレーム
    ↓
HSV 色抽出（赤を探す）
    ↓
ボール検出 (x, y)
    ↓
その座標の深度値取得 ← ★ ノイズの影響大
    ↓
スクリーン深度と比較 ← ★ ずれやすい
    ↓
ヒット判定
```

### 深度ベース（新）

```
RGB フレーム
    ↓
深度フレーム（t-1）と (t) を取得
    ↓
各ピクセルで深度差分計算
    ↓
物体が近づいている領域を検知
    ↓
領域から移動物体を抽出
    ↓
スクリーン向き判定（信頼度スコア）
    ↓
その位置の正確な深度値取得 ← ★ DepthMeasurementService で補間
    ↓
スクリーン深度と比較 ← ★ より正確
    ↓
ヒット判定
```

---

## 設定例（カスタマイズ）

### 高感度（小さい物体対応）

```python
tracker.set_depth_change_threshold(-30.0)   # より敏感に反応
tracker.set_min_motion_area(20)             # 小さい面積も検知
tracker.approach_confidence_threshold = 0.3  # 低い信頼度でも判定
```

### 低感度（ノイズ除外）

```python
tracker.set_depth_change_threshold(-150.0)   # 大きな移動のみ反応
tracker.set_min_motion_area(100)             # 大きい面積のみ
tracker.approach_confidence_threshold = 0.8  # 高い信頼度が必要
```

### バランス型（推奨デフォルト）

```python
tracker.set_depth_change_threshold(-50.0)    # 標準感度
tracker.set_min_motion_area(50)              # 標準範囲
tracker.approach_confidence_threshold = 0.5  # 標準信頼度
```

---

## デバッグ・ログ情報

### MotionBasedTracker のログレベル

```
[MotionBasedTracker] 初期化完了
[check_target_hit] ✓ ヒット検出 (400, 300) 深度: 1.22m
[_compute_depth_change_map] 移動ピクセル数: 1523
[_detect_moving_objects] 3個の候補検出
[_select_best_candidate] 最適候補選択 (400, 300), スコア: 0.876
```

### 統計情報（get_statistics）

```python
{
    'mode': 'motion',
    'color_hit_count': 45,
    'motion_hit_count': 52,
    'hybrid_switch_count': 0
}
```

---

## トラブルシューティング

### 問題1: 深度ベーストラッキングが反応しない

**原因と対策:**

| 原因 | 対策 |
|------|------|
| 深度フレーム取得失敗 | `camera_manager.get_depth_frame()` 確認 |
| 深度変化が小さい | `set_depth_change_threshold()` で敏感度上げる |
| 背景の動きを検知している | `set_min_motion_area()` で面積フィルタ上げる |
| ノイズが多い | `approach_confidence_threshold` 上げる |

### 問題2: 誤検知が多い（無関係な物体を検知）

**対策:**

```python
# パラメータ調整
tracker.set_depth_change_threshold(-100.0)   # より大きな移動のみ
tracker.depth_variance_threshold = 100.0     # 領域内の深度ばらつき制限
```

### 問題3: 色ベースにフォールバックしたい

**一時的な切り替え:**

```python
tracker.set_mode(TrackerMode.COLOR)
# または
tracker.set_mode(TrackerMode.HYBRID)
```

**スクリーン側でのフォールバック:**

```python
try:
    result = tracker_motion.check_target_hit(frame)
    if result is None and tracker_color:
        result = tracker_color.check_target_hit(frame)
except Exception as e:
    logging.warning(f"Motion tracking failed: {e}, fallback to color")
    result = tracker_color.check_target_hit(frame)
```

---

## パフォーマンス期待値

### FPS への影響

| トラッキングモード | 追加処理時間 | 説明 |
|-----------------|---------|------|
| **色ベース** | ~5ms | HSV 変換 + 輪郭検出 |
| **深度ベース** | ~15-20ms | 差分計算 + フィルタリング + 補間 |
| **ハイブリッド** | ~25ms | 両方を実行 |

**参考**: 120 FPS 時の 1フレーム処理時間 = ~8.3ms

**推奨**: 
- 120 FPS: 深度ベースは対応可能（GPU 最適化で可）
- 60 FPS: 深度ベースで十分余裕

---

## 統合チェックリスト

```
[ ] MotionBasedTracker クラスをプロジェクトに追加
[ ] TrackerSelector クラスをプロジェクトに追加
[ ] ox_game.py で motion_tracker を初期化
[ ] ox_game.py で tracker_selector を使用
[ ] 動作テストを実施
[ ] パラメータを環境に合わせて調整
[ ] ハイブリッドモードで 2 週間テスト
[ ] 統計情報を確認
[ ] 深度モードに完全切り替え
[ ] 色ベーストラッカーを廃止/アーカイブ
```

---

## 実装フェーズスケジュール

### Phase 1: 実装 & 統合（0.5～1 日）
- `motion_tracker.py` の検証
- `ox_game.py` への統合
- 基本動作確認

### Phase 2: テスト & 最適化（1～2 日）
- 各環境でのパラメータ調整
- ノイズ対策
- FPS 測定

### Phase 3: 移行（1～2 日）
- ハイブリッドモード運用
- 統計データ収集
- フィードバック反映

### Phase 4: 確定（～1 日）
- 深度モードへの完全移行判定
- 色ベーストラッカーのアーカイブ
- ドキュメント更新

---

## まとめ

深度ベース移動物体トラッキングへの移行により：

✅ **深度値の精度向上** - リアルタイム深度差分で直接判定  
✅ **環境適応性向上** - 照度変動に強い  
✅ **柔軟性向上** - 色に依存しない  
✅ **拡張性向上** - 複数物体対応可能  

**段階的な移行が推奨** - ハイブリッドモードで検証してから完全移行
