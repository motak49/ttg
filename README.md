# Touch The Golf - プロジェクト計画書

## プロジェクト概要
このプロジェクトは、USB接続カメラでゴルフボールが前面スクリーンに当たった位置を判定し、様々なゲームロジックに活用するためのアプリケーションです。

## プロジェクト構成
```
D:\VSCode\ttg
├── backend/
│   ├── __init__.py
│   ├── camera_manager.py
│   ├── screen_manager.py
│   ├── ball_tracker.py
│   └── interfaces.py
├── frontend/
│   ├── __init__.py
│   ├── main_window.py
│   ├── game_area.py
│   └── game_logic.py
├── common/
│   ├── __init__.py
│   ├── logger.py
│   └── utils.py
├── tests/
│   ├── test_backend_logic.py
│   ├── test_camera_manager.py
│   └── test_ball_tracker.py
├── requirements.txt
└── main.py
```

## 主な機能

### Backend (カメラとトラッキング関連)
1. **camera_manager.py**:
   - DepthAIを使用したカメラ接続管理
   - カメラ画像の取得と処理

2. **screen_manager.py**:
   - スクリーン領域の設定と管理（SetScreenArea）
   - スクリーン距離の測定と設定（SetScreenDepth）

3. **ball_tracker.py**:
   - 赤系ボールのトラッキング（SetTrackBall）
   - ボールの座標と深度を取得（GetHitArea）

4. **interfaces.py**:
   - カメラ、ボールトラッカー、スクリーンマネージャーの抽象インターフェース
   - UI とバックエンドの結合度を低減

### Frontend (UI関連)
1. **main_window.py**:
   - アプリケーションのメインウィンドウ
   - "Backend"と"Frontend"機能へのアクセス

2. **game_area.py**:
   - 3x3のブロック表示領域
   - 各ブロックにBorderLine（線の太さ40px）を表示
   - ボールが到達した座標を判定し、隣接するブロックを獲得

3. **game_logic.py**:
   - ゲームモードの管理
   - 各ゲームモード（Tick and Cross Game, Quiz Gameなど）の実装

### 共通ロジック
1. **logger.py**:
   - ScreenAreaLogs、TrackBallLogs、ScreenDepthLogsのログ出力
   - LogFolderが無ければ作成し、LogFileを作成

2. **utils.py**:
   - 共通のユーティリティ関数

## 依存パッケージ
requirements.txtには以下を含める：
```
opencv-python-headless==4.10.0.84
depthai==2.30.0
PyQt6==6.7.1
```

## 必要最低限機能
- カメラが起動出来るか。
- カメラから映像データを取得出来るか。
- FPSは60固定となっているか。
- 4点クリックでエリアを指定出来るか。
- 前面スクリーンまでの距離を測定出来るか。
- 赤、ピンクのゴルフボールを検知出来るか。
- ゴルフボールが前面スクリーンに当たった場所を測定出来るか。
- ゴルフボールが前面スクリーンに当たった場所を座標として返すことが出来るか。

## 開発手順
1. 仮想環境のセットアップ
2. 必要なパッケージのインストール
3. Backend機能の実装
4. Frontend機能の実装
5. 共通ロジックの実装
6. 統合とテスト

## テストカバレッジ
プロジェクトには以下のテストが含まれています：
- `tests/test_backend_logic.py`: スクリーン領域・深度の保存・読み込みテスト
- `tests/test_camera_manager.py`: カメラマネージャーのユニットテスト
- `tests/test_ball_tracker.py`: ボールトラッカーのユニットテスト

## CI/CD パイプライン
プロジェクトには GitHub Actions を使用した自動化された CI パイプラインが設定されています。このパイプラインは以下のチェックを実行します：
- ファイル形式のチェック（flake8）
- 型チェック（mypy --strict）
- テスト実行（pytest）
- カバレッジレポート生成

## 完了判断基準
このプロジェクトは以下の基準を満たすことで完了と判断します：

### ソースコードの実装確認
- [x] backend/camera_manager.py: DepthAIカメラ接続と画像取得機能が実装
- [x] backend/screen_manager.py: スクリーン領域設定・距離測定機能が実装
- [x] backend/ball_tracker.py: ボールトラッキング・座標取得機能が実装
- [x] backend/interfaces.py: インターフェース定義が実装
- [x] frontend/main_window.py: メインウィンドウとUI構成が実装
- [x] frontend/game_area.py: 3x3ゲーム領域とBorderLine表示が実装
- [x] frontend/game_logic.py: ゲームモード管理機能が実装
- [x] common/logger.py: ログ出力機能が実装
- [x] common/utils.py: 共通ユーティリティ関数が実装

### 機能確認
- [x] カメラ起動確認テストが完了
- [x] 映像データ取得テストが完了
- [x] 4点クリックによるエリア指定テストが完了
- [x] スクリーン距離測定テストが完了
- [x] 赤・ピンクボール検知テストが完了
- [x] ボール座標測定テストが完了
- [x] 座標返却機能テストが完了

### 統合確認
- [x] BackendとFrontendの統合が完了
- [x] 全体機能テストが完了
- [x] アプリケーション実行確認が完了
