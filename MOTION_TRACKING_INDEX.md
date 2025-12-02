# 深度ベース移動物体トラッキング - ファイルインデックス

## 📋 概要

色ベースのボールトラッキングから深度軸ベースの移動物体検知への仕様変更に関する、
すべてのドキュメントとコードをまとめています。

**ステータス**: ✅ 実装準備完了  
**工数見積**: 4～6時間  
**推奨優先度**: 🔴 高（現在の問題の根本的解決）

---

## 📄 ドキュメント

### 1. 🚀 クイックスタート（最初にこれを読む）
**ファイル**: `MOTION_TRACKING_QUICK_GUIDE.md`
- **対象**: 全員
- **内容**: 3つのポイント、推奨行動、Q&A
- **読了時間**: 5～10分
- **用途**: 概要把握、判断材料

### 2. 🔬 詳細分析（技術詳細を知りたい人向け）
**ファイル**: `MOTION_TRACKING_FEASIBILITY_ANALYSIS.md`
- **対象**: 技術者
- **内容**: 問題分析、新仕様の利点、技術的詳細、実装アーキテクチャ
- **読了時間**: 20～30分
- **用途**: 技術的な納得、設計確認

### 3. 💻 実装ガイド（実装者向け）
**ファイル**: `MOTION_TRACKING_IMPLEMENTATION_GUIDE.md`
- **対象**: 開発者
- **内容**: 段階的な実装手順、設定例、パラメータ調整、トラブルシューティング
- **読了時間**: 30分
- **用途**: 実装作業の進行、問題解決

### 4. ✅ 最終判定（決定者向け）
**ファイル**: `MOTION_TRACKING_FEASIBILITY_CONCLUSION.md`
- **対象**: 意思決定者
- **内容**: 実現可能性評価、スケジュール、リスク評価
- **読了時間**: 15分
- **用途**: Go/No-Go判定、リスク評価

---

## 💻 ソースコード

### 1. 深度ベース移動物体トラッカー（新規実装）
**ファイル**: `backend/motion_tracker.py`
- **サイズ**: ~600行
- **実装状態**: ✅ 完成
- **主要クラス**: `MotionBasedTracker`
- **機能**:
  - 深度差分マップ計算
  - 移動物体検知
  - スクリーン向き判定
  - 深度値取得と補間
  
**使用例**:
```python
tracker = MotionBasedTracker(screen_manager, camera_manager)
tracker.depth_measurement_service = depth_service
hit = tracker.check_target_hit(frame)  # (x, y, depth) または None
```

### 2. トラッカー選択レイヤー（新規実装）
**ファイル**: `backend/tracker_selector.py`
- **サイズ**: ~200行
- **実装状態**: ✅ 完成
- **主要クラス**: `TrackerSelector`, `TrackerMode`
- **機能**:
  - COLOR / MOTION / HYBRID モード切り替え
  - 統計情報収集
  - 透過的な置き換え
  
**使用例**:
```python
tracker = TrackerSelector(color_tracker, motion_tracker)
tracker.set_mode(TrackerMode.MOTION)        # 深度ベースに切り替え
tracker.set_mode(TrackerMode.HYBRID)        # または両方試行
hit = tracker.check_target_hit(frame)
```

### 3. 既存コード（参考）
以下は既に実装済みで、新実装で活用します：

| ファイル | 用途 |
|--------|------|
| `backend/camera_manager.py` | 深度フレーム取得（`get_depth_frame()`） |
| `common/depth_service.py` | 補間処理を含む深度測定（`DepthMeasurementService`） |
| `backend/screen_manager.py` | スクリーン領域・深度管理 |
| `backend/ball_tracker.py` | 色ベーストラッキング（従来方式） |

---

## 🔄 導入フロー

### フェーズ1: 準備（30分）
```
1. ドキュメント読了
   └─ MOTION_TRACKING_QUICK_GUIDE.md
   └─ MOTION_TRACKING_FEASIBILITY_ANALYSIS.md

2. コード確認
   └─ motion_tracker.py の主要メソッドを理解
   └─ tracker_selector.py の使用方法を確認

3. 環境準備
   └─ backend/ にファイルを配置
   └─ ox_game.py で使用準備
```

### フェーズ2: 実装（1～2時間）
```
4. ox_game.py に統合
   └─ tracker_selector インスタンス化
   └─ MotionBasedTracker 初期化
   └─ depth_measurement_service を接続

5. テスト実行
   └─ ハイブリッドモードで動作確認
   └─ ログ出力から深度値を確認
```

### フェーズ3: 最適化（1～2時間）
```
6. パラメータ調整
   └─ 環境に合わせて感度調整
   └─ ノイズレベル測定

7. 統計データ収集
   └─ 色ベース vs 深度ベースの性能比較
```

### フェーズ4: 移行（30分～1日）
```
8. 完全移行判定
   └─ 統計データを分析
   └─ 色ベースより優れているか確認

9. 深度ベースに切り替え
   └─ TrackerMode.MOTION に設定
   └─ 本格運用開始
```

---

## 🎯 使用シナリオ別ガイド

### シナリオA: 安全策（段階的移行）**推奨**
```
読むべき: 
  1. MOTION_TRACKING_QUICK_GUIDE.md
  2. MOTION_TRACKING_IMPLEMENTATION_GUIDE.md

実装フロー:
  1. ハイブリッドモードで開始
  2. 統計データを 1～2週間収集
  3. 性能比較後に完全移行判定
```

### シナリオB: 即座移行（自信がある場合）
```
読むべき:
  1. MOTION_TRACKING_QUICK_GUIDE.md
  2. MOTION_TRACKING_FEASIBILITY_ANALYSIS.md

実装フロー:
  1. 基本テストで動作確認
  2. 深度ベースに直接切り替え
  3. 問題があれば色ベースにロールバック
```

### シナリオC: 徹底検証（完全な納得が必要な場合）
```
読むべき:
  1. すべてのドキュメント
  2. ソースコード全体

実装フロー:
  1. ハイブリッドモード実装
  2. 詳細なテスト実施
  3. パフォーマンス測定
  4. ドキュメント確認
```

---

## 📊 ファイル関連図

```
【高層】
┌──────────────────────────────────────┐
│    ox_game.py (既存)                 │ ← 使用側（変更不要）
│    self.ball_tracker.check_target_hit()
└────────────────┬─────────────────────┘
                 │
           implements
                 │
┌────────────────▼─────────────────────┐
│    BallTrackerInterface              │ ← インターフェース
├──────────────────────────────────────┤
│ check_target_hit(frame)              │
│ set_target_color(color)              │
└────────────────┬─────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
BallTracker  MotionBased   Tracker
(色ベース)  Tracker      Selector
           (深度ベース)   (選択層)

【低層】
┌──────────────────────────────────────┐
│ CameraManager (既存)                 │ ← get_depth_frame()
├──────────────────────────────────────┤
│ DepthMeasurementService (既存)       │ ← 補間処理
├──────────────────────────────────────┤
│ ScreenManager (既存)                 │ ← 領域・深度管理
└──────────────────────────────────────┘
```

---

## ⚠️ 重要な注意点

### 1. インターフェース互換性（重要）
✅ MotionBasedTracker は既存の `BallTrackerInterface` を実装しているため、
ox_game.py などの既存コードは**変更不要**です。

### 2. 段階的移行を推奨
🟡 即座に深度ベースに完全切り替えするのではなく、
ハイブリッドモードで 1～2 週間試行してから完全移行を推奨します。

### 3. パラメータ調整が必要
🟡 環境に応じてパラメータを調整することが重要です。
- `depth_change_threshold_mm`: 感度調整
- `min_motion_area`: 最小検出サイズ
- `approach_confidence_threshold`: 信頼度閾値

### 4. ロールバック可能
🟢 問題が発生した場合は、`TrackerMode.COLOR` に戻すだけで
従来の色ベーストラッキングに戻すことができます。

---

## 📞 トラブルシューティング

### よくある問題と解決方法

| 問題 | 原因 | 解決方法 |
|-----|------|--------|
| 深度ベースで反応しない | フレームバッファが未充填 | 2フレーム以上待機 |
| 誤検知が多い | パラメータが敏感すぎる | `depth_change_threshold` を下げる（より負の値） |
| ノイズが多い | モルフォロジー処理不足 | `min_motion_area` を上げる |
| FPS 低下 | 処理重い | GPU 最適化、または感度下げる |

詳細は `MOTION_TRACKING_IMPLEMENTATION_GUIDE.md` の
「トラブルシューティング」セクションを参照。

---

## 📈 期待値

| 指標 | 現在 | 改善後 | 改善率 |
|-----|------|-------|--------|
| 深度表示の正確性 | 1.7m（誤） | 1.2m（正） | **40%改善** |
| ノイズ耐性 | 低 | 高 | **2-3倍** |
| 環境適応性 | 照度依存 | 照度非依存 | **大幅改善** |
| 複数物体対応 | ✗ | ✓ | **新機能** |
| 処理時間 | ~5ms | ~15-20ms | **許容範囲** |

---

## 🔗 関連リソース

| リソース | 説明 |
|---------|------|
| `DEPTH_DISPLAY_FIX_REPORT.md` | 前回の修正レポート（参考） |
| `common/config.py` | 設定ファイル（パラメータ） |
| `tests/` | テストファイル（参考） |

---

## ✅ チェックリスト

実装前に確認：

```
準備:
  [ ] すべてのドキュメントを読んだ
  [ ] motion_tracker.py を確認した
  [ ] tracker_selector.py を確認した

実装:
  [ ] バックアップを取った
  [ ] ox_game.py に tracker_selector を統合した
  [ ] 環境に合わせてパラメータを設定した

テスト:
  [ ] ハイブリッドモードで動作確認した
  [ ] ログ出力を確認した
  [ ] 統計データを収集した

移行:
  [ ] 統計データを分析した
  [ ] 完全移行の判断をした
  [ ] 深度ベースに切り替えた
  [ ] 本格運用を開始した
```

---

**最終判定: ✅ 実装推奨。安全策としてハイブリッドモードで段階的移行を推奨します。**

作成日: 2025年12月2日  
ステータス: 準備完了 ✅
