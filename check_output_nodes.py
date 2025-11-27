"""
depthai 3.1.0 での出力ノード確認
"""
import depthai as dai

print("=== Output node 確認 ===\n")

# Out-related nodes
out_nodes = [x for x in dir(dai.node) if 'Out' in x]
print("Output-related nodes:", out_nodes)

# BenchmarkOut の確認
pipeline = dai.Pipeline()
bench_out = pipeline.create(dai.node.BenchmarkOut)
print("\nBenchmarkOut created successfully")
print("BenchmarkOut methods:")
methods = [m for m in dir(bench_out) if not m.startswith('_') and 'input' in m.lower()]
for method in sorted(methods):
    print(f"  - {method}")

# Pipeline getDefaultQueue の確認
print("\n=== Pipeline methods ===")
print("Pipeline has setXLinkChunkSize:", hasattr(pipeline, 'setXLinkChunkSize'))
print("Pipeline has getDefaultQueue:", hasattr(pipeline, 'getDefaultQueue'))

# Device の出力キュー取得
print("\n=== Device methods ===")
device_methods = [m for m in dir(dai.Device) if 'queue' in m.lower() or 'output' in m.lower() or 'stream' in m.lower()]
print("Device queue/output related methods:", sorted(device_methods))
