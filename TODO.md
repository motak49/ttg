# TODO List for Refactoring Project

## Overview
このチェックリストは、最新の提案に基づくタスクをまとめたものです。各項目が完了したら `[x]` にしてください。

## Checklist
- [x] タイマー間隔を FPS に合わせて設定（概念設計完了）
- [x] `common/config.py` 作成・定数定義
- [x] OxGame のタイマー初期化置換 (`self.timer.start(TIMER_INTERVAL_MS)`)
- [x] 他モジュールのタイマー使用箇所更新
- [x] ログファイル欠損時デフォルト書き込み実装
- [x] `common/validation.py` 追加・設定チェック関数実装
- [x] アプリ起動時にバリデーション呼び出し組み込み
- [x] デバッグログ統一（logger ラッパー作成）
- [x] 必要ならテストケース追加 (`tests/test_config.py`, `tests/test_validation.py`)
- [x] コードクリーンアップ（未使用インポート、フォーマット整形）
- [x] ドキュメント更新 (README.md, CHECKLIST.md)
