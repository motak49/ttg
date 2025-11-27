"""
depthai 3.1.0 での HostNode 使用例確認
"""
import depthai as dai

print("=== HostNode メソッド確認 ===\n")

pipeline = dai.Pipeline()
host_node = pipeline.create(dai.node.HostNode)

print("HostNode methods:")
methods = [m for m in dir(host_node) if not m.startswith('_') and callable(getattr(host_node, m))]
for method in sorted(methods)[:20]:
    print(f"  - {method}")

# Stream-related methods
print("\nStream-related methods:")
stream_methods = [m for m in dir(host_node) if 'stream' in m.lower() or 'input' in m.lower() or 'output' in m.lower()]
for method in sorted(stream_methods):
    if not method.startswith('_'):
        print(f"  - {method}")

# Properties
print("\nHostNode properties:")
print("  - inputImage:", hasattr(host_node, 'inputImage'))
print("  - getAsyncInQueue:", hasattr(host_node, 'getAsyncInQueue'))
print("  - getAsyncOutQueue:", hasattr(host_node, 'getAsyncOutQueue'))

# Legacy XLinkOut 互換性
print("\n=== Checking for legacy compatibility ===")
print("Pipeline.createXLinkOut:", hasattr(pipeline, 'createXLinkOut'))

# Camera と ColorCamera の違い
print("\n=== Camera vs ColorCamera ===")
cam1 = pipeline.create(dai.node.Camera)
print("Camera node created successfully")
print("Camera has setResolution:", hasattr(cam1, 'setResolution'))
