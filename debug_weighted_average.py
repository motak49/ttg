"""距離加重平均の動作確認"""
import numpy as np
from unittest.mock import Mock
from common.depth_service import DepthMeasurementService, DepthConfig
import logging

logging.basicConfig(level=logging.DEBUG)

# 深度フレーム生成
depth_frame = np.zeros((360, 640), dtype=np.uint16)
for dy in range(-10, 11):
    for dx in range(-10, 11):
        y, x = 180 + dy, 320 + dx
        if 0 <= y < 360 and 0 <= x < 640:
            dist = (dx**2 + dy**2)**0.5
            if dist <= 2:
                depth_frame[y, x] = 0
            elif dist <= 6:
                depth_frame[y, x] = 1200
            else:
                depth_frame[y, x] = 1700

# サービス作成
camera = Mock()
camera.get_depth_frame = Mock(return_value=depth_frame)
config = DepthConfig(
    min_valid_depth_m=0.5,
    max_valid_depth_m=5.0,
    interpolation_radius=10,
    reference_depth_m=2.0
)
service = DepthMeasurementService(camera, config)

# 補間実行
result = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=False)
print(f"\n最終結果: {result:.3f}m")

# 手動で距離加重平均を計算
values = []
for dy in range(-10, 11):
    for dx in range(-10, 11):
        nx, ny = 320 + dx, 180 + dy
        if 0 <= nx < 640 and 0 <= ny < 360:
            neighbor_depth = int(depth_frame[ny, nx])
            if 0 < neighbor_depth < 65535:
                distance = int((dx**2 + dy**2) ** 0.5)
                values.append((neighbor_depth, distance))

print(f"\n周辺画素情報:")
ball_count = sum(1 for d, _ in values if d == 1200)
bg_count = sum(1 for d, _ in values if d == 1700)
print(f"ボール画素（1200mm）: {ball_count}")
print(f"背景画素（1700mm）: {bg_count}")

# 距離加重平均
total_weight = 0.0
weighted_sum = 0.0
for depth_mm, distance in values:
    weight = 1.0 / (distance + 1.0)
    weighted_sum += depth_mm * weight
    total_weight += weight

weighted_avg = weighted_sum / total_weight if total_weight > 0 else 0
print(f"\n距離加重平均: {weighted_avg:.0f}mm = {weighted_avg/1000:.3f}m")

# ボール側の重み
ball_weight = sum(1.0/(d+1) for depth, d in values if depth == 1200)
bg_weight = sum(1.0/(d+1) for depth, d in values if depth == 1700)
print(f"\nボール側の総重み: {ball_weight:.2f}")
print(f"背景側の総重み: {bg_weight:.2f}")
print(f"重み比: ボール {ball_weight/(ball_weight+bg_weight)*100:.1f}% vs 背景 {bg_weight/(ball_weight+bg_weight)*100:.1f}%")
