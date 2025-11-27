"""
depthai 3.1.0 の新しいパイプラインモデル確認
XLinkOut/XLinkIn の代替実装を探す
"""
import depthai as dai

print("=== Pipeline connection model in 3.1.0 ===\n")

# 基本的なパイプライン
pipeline = dai.Pipeline()

# ColorCamera
color = pipeline.create(dai.node.ColorCamera)
color.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
color.setFps(30)

# パイプライン全体のメソッド
print("Pipeline 全体メソッド:")
pipeline_methods = [m for m in dir(pipeline) if not m.startswith('_')]
for m in sorted(pipeline_methods):
    if any(x in m.lower() for x in ['node', 'getid', 'connect', 'link', 'output', 'input', 'queue', 'stream']):
        print(f"  - {m}")

# ColorCamera の出力
print("\nColorCamera 出力ピン:")
print(f"  - video: {hasattr(color, 'video')}")
print(f"  - preview: {hasattr(color, 'preview')}")
print(f"  - still: {hasattr(color, 'still')}")
print(f"  - isp: {hasattr(color, 'isp')}")

# ColorCamera の出力型確認
if hasattr(color, 'video'):
    video_pin = color.video
    print(f"\nColorCamera.video type: {type(video_pin)}")
    print(f"ColorCamera.video methods:")
    pin_methods = [m for m in dir(video_pin) if not m.startswith('_') and callable(getattr(video_pin, m))]
    for m in sorted(pin_methods)[:15]:
        print(f"    - {m}")

# HostNode の確認
print("\n=== HostNode ===")
try:
    # HostNode は Pipeline 内のノードではなく、スタンドアロン
    print("Checking for HostNode in dai namespace...")
    if hasattr(dai, 'HostNode'):
        print("dai.HostNode exists")
    else:
        print("dai.HostNode does not exist in 3.1.0")
except Exception as e:
    print(f"Cannot access HostNode: {e}")

# Device とのパイプライン
print("\n=== Device Pipeline Model ===")
print("Device.__init__ signature:")
import inspect
sig = inspect.signature(dai.Device.__init__)
params = list(sig.parameters.keys())
print(f"  Parameters: {params}")

# デバイスの出力キュー関連
print("\nDevice queue methods:")
device_methods = [m for m in dir(dai.Device) if 'queue' in m.lower() or 'output' in m.lower()]
for m in sorted(device_methods):
    print(f"  - {m}")
