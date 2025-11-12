## 目的
このファイルはリポジトリ内で自動化された AI コーディング補助（Copilot / 自動エージェント）が
素早く作業に入れるよう、プロジェクト固有の「知っておくべき事実」をまとめた短いガイドです。

## ビッグパicture（全体構成）
- backend/: カメラ・トラッキング・スクリーン管理を担当
  - 主要ファイル: `backend/backend_core.py`, `backend/ball_tracker.py`, `backend/camera_manager.py`, `backend/screen_manager.py`, `backend/interfaces.py`
- frontend/: PyQt6 ベースの UI とゲームロジック
  - 主要ファイル: `frontend/main_window.py`, `frontend/game_area.py`, `frontend/game_logic.py`
- common/: 定数、ログ、ユーティリティ
  - 主要ファイル: `common/config.py`, `common/logger.py`, `common/utils.py`
- 永続化／ログフォルダ:
  - `ScreenAreaLogs/area_log.json` (スクリーン領域)
  - `ScreenDepthLogs/depth_log.json` (スクリーン深度)
  - `TrackBallLogs/tracked_ball_config.json` (トラッキング設定)

設計上の意図: カメラ周り（DepthAI 依存）やスクリーン設定は backend に集約され、UI はインターフェース経由でこれらを利用します。

## 重要な動作フロー（短く）
1. カメラ起動: `backend/camera_manager.py` がカメラフレームを供給
2. トラッキング: `backend/ball_tracker.py` がフレームからボールを検出（色帯域は "赤" / "ピンク"）
3. 衝突判定: `BallTracker.check_target_hit()` が `ScreenManager` のポリゴン情報を参照しヒット判定
4. ゲーム反映: ヒット座標は `frontend/game_logic.py` の `tick_cross_game` 等で 3x3 グリッドに変換され処理される

## プロジェクト固有の規約と注意点
- 色指定は日本語文字列（"赤" / "ピンク"）が使われます。例: `BallTracker.set_target_color("赤")`。
- グリッド変換は現状フレームサイズ固定（800x600）で計算（`frontend/game_logic.py::_coords_to_grid`）。UI 側から幅/高さを渡す拡張が想定される。
- 永続化はプロジェクトルート直下の Logs フォルダに JSON で書き込む設計。テストでは一時ディレクトリを使うかこれらファイルを上書きする点に注意。
- 設定ファイルパスのハードコード例: `TrackBallLogs/tracked_ball_config.json`（相対パス）。運用時は base_path を確認すること。

## 開発・実行ワークフロー（すぐ使えるコマンド）
（Windows PowerShell での例）
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 単体テスト
python -m pytest -q
# 実アプリ起動（UI）
python main.py
```

## テストと CI のヒント
- リポジトリには pytest ベースのユニットテストが存在します（`tests/` と `frontend`内のテスト）。ハードウェア依存（DepthAI, カメラ）を持つコードはモックまたはスタブ化してテストするのが既存方針。
- README.md に CI 説明あり（flake8, mypy --strict, pytest）。ローカルで同等チェックを実行すると PR の差戻しを減らせます。

## 典型的な小さなタスクでの具体例
- 1) BallTracker の HSV 範囲を調整する:
  - 編集箇所: `backend/ball_tracker.py` の `set_target_color` で lower/upper を変更
  - 保存場所: 変更は `TrackBallLogs/tracked_ball_config.json` に反映される
- 2) スクリーン領域フォーマットを変更する:
  - 編集箇所: `backend/backend_core.py` の `set_screen_area` と `load_screen_area` を同時に更新して互換性を保つ

## 出来ること / 禁止事項
- 期待される行動: 既存ファイルとログの位置を踏まえた小さな変更、テストの追加、単純なバグ修正。
- 避ける行動: ハードウェア（カメラ）にアクセスする長時間の実行やクラウド呼び出しを自動で実行しないこと。代わりにモックを使う。

## 参考ファイル（最優先で読むべき順）
1. `README.md` — プロジェクト目的と高レベル手順
2. `backend/backend_core.py` — スクリーン領域・深度の永続化ロジック
3. `backend/ball_tracker.py` — ボール検出・ヒット判定の実装（色指定、軌道角度判定など）
4. `frontend/game_logic.py` — ヒット座標→ゲーム状態への反映
5. `common/config.py` — FPS・タイマー関連の定数

## フィードバックのお願い
このファイルは最小限の事実ベースガイドです。不明確な点（実行コマンド、CI の細部、テストフロー）や追加して欲しい例があれば教えてください。更新してマージします。
