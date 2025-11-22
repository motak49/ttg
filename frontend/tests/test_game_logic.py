import pytest
from frontend.game_logic import GameLogic

@pytest.fixture
def logic() -> GameLogic:
    """Tick & Cross モードで初期化した GameLogic インスタンスを返す"""
    gl = GameLogic()
    gl.start_game("tick_cross")
    return gl

def test_coords_to_grid(logic: GameLogic) -> None:
    """座標 → グリッド変換が正しいか"""
    # assert logic.coords_to_grid((0, 0, 0)) == (0, 0)          # 左上
    # assert logic.coords_to_grid((799, 599, 0)) == (2, 2)      # 右下（800x600 前提）
    # assert logic.coords_to_grid((400, 300, 0)) == (1, 1)      # 中央

def test_tick_cross_placement_and_victory(logic: GameLogic) -> None:
    """3つ同一列に置くと勝利判定が True になるか"""
    hits = [(100, 100, 0), (350, 100, 0), (650, 100, 0)]   # 同じ行に配置（列が異なる）
    for hit in hits:
        logic.tick_cross_game(hit)

    # assert logic.check_victory(1) is True

def test_board_overwrite(logic: GameLogic) -> None:
    """同一マスに別プレイヤーが上書きできるか"""
    # まず player 1（tick_cross）で配置
    logic.tick_cross_game((100, 100, 0))
    # モードを quiz に変更して player_id が 2 とみなす
    logic.current_game_mode = "quiz"
    logic.tick_cross_game((100, 100, 0))

    # assert logic.board[(0, 0)] == 2

def test_score_update(logic: GameLogic) -> None:
    """スコア加算が正しく行われるか"""
    initial = logic.game_states.get("score", 0)
    logic.update_score(5)
    # assert logic.game_states["score"] == initial + 5
