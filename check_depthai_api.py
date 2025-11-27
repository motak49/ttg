"""
depthai 3.1.0 API互換性チェック
"""
import depthai as dai

print("=== depthai API Check ===\n")

# 1. Pipeline.create() の確認
pipeline = dai.Pipeline()
print("✓ Pipeline.create() method exists:", hasattr(pipeline, 'create'))

# 2. 主要ノードの確認
print("✓ dai.node.ColorCamera exists:", hasattr(dai.node, 'ColorCamera'))
print("✓ dai.node.MonoCamera exists:", hasattr(dai.node, 'MonoCamera'))
print("✓ dai.node.StereoDepth exists:", hasattr(dai.node, 'StereoDepth'))
print("✓ dai.node.XLinkOut exists:", hasattr(dai.node, 'XLinkOut'))

# 3. Device() コンストラクタの確認
print("\n✓ dai.Device callable:", callable(dai.Device))

# 4. 列挙型の確認
print("\n=== Enum Check ===")
print("✓ dai.CameraBoardSocket exists:", hasattr(dai, 'CameraBoardSocket'))
print("✓ dai.ColorCameraProperties exists:", hasattr(dai, 'ColorCameraProperties'))
print("✓ dai.MonoCameraProperties exists:", hasattr(dai, 'MonoCameraProperties'))

# 5. UsbSpeed の確認
print("✓ dai.UsbSpeed exists:", hasattr(dai, 'UsbSpeed'))
if hasattr(dai, 'UsbSpeed'):
    print("  - SUPER_PLUS:", hasattr(dai.UsbSpeed, 'SUPER_PLUS'))

# 6. デバイス情報取得
print("\n=== Device API Check ===")
print("✓ dai.Device.getAllAvailableDevices exists:", hasattr(dai.Device, 'getAllAvailableDevices'))
print("✓ dai.XLinkProtocol exists:", hasattr(dai, 'XLinkProtocol'))

# 7. Node メソッドの確認
color_cam = pipeline.create(dai.node.ColorCamera)
print("\n=== ColorCamera Methods ===")
print("✓ setResolution:", hasattr(color_cam, 'setResolution'))
print("✓ setFps:", hasattr(color_cam, 'setFps'))
print("✓ setColorOrder:", hasattr(color_cam, 'setColorOrder'))
print("✓ setInterleaved:", hasattr(color_cam, 'setInterleaved'))

# 8. 解像度列挙型の確認
print("\n=== Resolution Enums ===")
if hasattr(dai, 'ColorCameraProperties'):
    props = dai.ColorCameraProperties
    print("✓ ColorCameraProperties.SensorResolution exists:", hasattr(props, 'SensorResolution'))
    if hasattr(props, 'SensorResolution'):
        sr = props.SensorResolution
        print("  - THE_1080_P:", hasattr(sr, 'THE_1080_P'))

print("\n✓ MonoCameraProperties.SensorResolution exists:", hasattr(dai.MonoCameraProperties, 'SensorResolution'))
if hasattr(dai.MonoCameraProperties, 'SensorResolution'):
    sr = dai.MonoCameraProperties.SensorResolution
    print("  - THE_720_P:", hasattr(sr, 'THE_720_P'))

# 9. バージョン情報
print("\n=== Version Info ===")
print("depthai version:", dai.__version__)
