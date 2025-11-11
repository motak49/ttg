# game_logic.py
"""
ゲームロジッククラス
"""

from typing import Any, Dict, Tuple, Optional


class GameLogic:
    """ゲームロジック管理クラス"""

    def __init__(self) -> None:
        # 現在のモード（"tick_cross" / "quiz" など）
        self.current_game_mode: Optional[str] = None
        # 任意のゲームステートを保持する dict
        self.game_states: Dict[str, Any] = {}
        # 3×3 の盤面を保持する dict {(row, col): player_id}
        self.board: Dict[Tuple[int, int], int] = {}

    # -------------------------------------------------
    # 基本的なゲーム制御 API
    # -------------------------------------------------
    def set_game_mode(self, mode: str) -> bool:
        """
        ゲームモードを設定する

        Args:
            mode (str): "tick_cross" か "quiz"

        Returns:
            bool: 設定成功時 True、失敗時 False
        """
        valid_modes = ["tick_cross", "quiz"]
        if mode not in valid_modes:
            print(f"無効なゲームモード: {mode}")
            return False

        self.current_game_mode = mode
        print(f"ゲームモードを {mode} に設定しました")
        return True

    def get_current_game_mode(self) -> Optional[str]:
        """現在のゲームモードを取得する"""
        return self.current_game_mode

    def start_game(self, mode: str) -> bool:
        """
        ゲーム開始（モード設定 + 初期ステート生成）

        Args:
            mode (str): 開始したいゲームモード

        Returns:
            bool: 成功時 True
        """
        if not self.set_game_mode(mode):
            return False

        # 基本的なゲーム状態を初期化
        self.game_states = {
            "mode": mode,
            "is_running": True,
            "score": 0,
            "time_left": 60,  # 秒単位の想定タイムリミット
        }

        print(f"{mode}モードでゲームを開始しました")
        return True

    def end_game(self) -> None:
        """ゲーム終了処理"""
        self.game_states["is_running"] = False
        print("ゲームを終了しました")

    def update_score(self, points: int) -> None:
        """
        スコア更新

        Args:
            points (int): 加算したいポイント数
        """
        if "score" in self.game_states:
            self.game_states["score"] += points
            print(
                f"スコアを {points} ポイント追加しました。現在のスコア: {self.game_states['score']}"
            )

    def get_game_state(self) -> Dict[str, Any]:
        """ゲーム全体状態（辞書）を取得"""
        return self.game_states

    # -------------------------------------------------
    # Tick & Cross ゲームロジック
    # -------------------------------------------------
    def tick_cross_game(self, hit_area: Tuple[int, int, float]) -> None:
        """
        ヒット座標を受け取り、盤面更新と勝利判定を行う

        Args:
            hit_area (Tuple[int, int, float]): (x, y, depth) のヒット情報
        """
        # 盤面インデックス取得
        row, col = self._coords_to_grid(hit_area)

        # プレイヤー ID はモードに応じて仮に 1 / 2 とする（実装側で変更可）
        player_id = 1 if self.current_game_mode == "tick_cross" else 2

        # 盤面更新（上書き可能）
        self.board[(row, col)] = player_id
        print(f"Tick & Cross: ({row}, {col}) にプレイヤー {player_id} が配置されました。")

        # 勝利判定
        if self._check_victory(player_id):
            print(f"Player {player_id} wins!")

    def quiz_game(self, hit_area: Tuple[int, int, float]) -> None:
        """
        Quiz ゲームの雛形（現時点では未実装）

        Args:
            hit_area (Tuple[int, int, float]): 将来的に使用予定
        """
        print(f"Quiz Game: ヒット座標 {hit_area}")

    # -------------------------------------------------
    # 内部ヘルパーメソッド
    # -------------------------------------------------
    def _coords_to_grid(self, hit_area: Tuple[int, int, float]) -> Tuple[int, int]:
        """ヒット座標 (x, y) を 3×3 グリッドの (row, col) に変換

        現在はフレームサイズを固定 800×600 として計算。
        必要に応じて UI 側から幅・高さを渡す設計へ拡張可能です。
        """
        x, y, _ = hit_area
        block_w = 800 // 3
        block_h = 600 // 3
        col = min(x // block_w, 2)
        row = min(y // block_h, 2)
        return row, col

    # 公開ラッパー（テスト用）
    def coords_to_grid(self, hit_area: Tuple[int, int, float]) -> Tuple[int, int]:
        """テストから呼び出し可能な座標変換メソッド"""
        return self._coords_to_grid(hit_area)

    def _check_victory(self, player_id: int) -> bool:
        """同一プレイヤーが行・列・対角に揃ったか判定"""
        # 行チェック
        for r in range(3):
            if all(self.board.get((r, c)) == player_id for c in range(3)):
                return True
        # 列チェック
        for c in range(3):
            if all(self.board.get((r, c)) == player_id for r in range(3)):
                return True
        # 対角（左上→右下）
        if all(self.board.get((i, i)) == player_id for i in range(3)):
            return True
        # 対角（右上→左下）
        if all(self.board.get((i, 2 - i)) == player_id for i in range(3)):
                return True
        return False

    # 公開ラッパー（テスト用）
    def check_victory(self, player_id: int) -> bool:
        """テストから呼び出し可能な勝利判定メソッド"""
        return self._check_victory(player_id)


# グローバルなゲームロジックインスタンス
game_logic = GameLogic()
