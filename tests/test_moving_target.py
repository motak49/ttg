"""
MovingTarget の単体テスト
"""

from backend.moving_target import MovingTarget

def test_update_position_and_velocity():
    """ターゲットの位置と速度が正しく更新されることを確認"""
    # 画像サイズは100x100、bounds を (0, 200, 0, 200) とする
    bounds = (0, 200, 0, 200)

    # 左端に向かって移動中のターゲットを作成
    target = MovingTarget(
        image_path="dummy.png",
        position=(5, 50),          # x が左端付近
        velocity=(-10, 0)           # 左へ進む
    )
    
    # 更新前位置と速度を記録
    old_pos = target.position
    old_vel = target.velocity
    
    # 更新
    target.update(bounds)
    
    # 位置と速度が変更されていることを確認
    assert target.position != old_pos
    assert target.velocity != old_vel

def test_reflection_at_bounds():
    """境界に到達した際の反射処理をテスト"""
    # 画像サイズは100x100、bounds を (0, 200, 0, 200) とする
    bounds = (0, 200, 0, 200)

    # 左端に向かって移動中のターゲットを作成
    target = MovingTarget(
        image_path="dummy.png",
        position=(5, 50),          # x が左端付近
        velocity=(-10, 0)           # 左へ進む
    )
    
    # 更新
    target.update(bounds)

    # X 方向は反転し、位置が境界内に収まること
    assert target.velocity[0] == 10   # 速度が正になる
    assert target.position[0] >= bounds[0]
