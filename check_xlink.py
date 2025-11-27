import depthai as dai

print("=== Checking XLinkOut availability ===\n")
print("XLink-related in dai.node:", [x for x in dir(dai.node) if 'Link' in x or 'XLink' in x])

print("\nAll dai.node items:")
for item in sorted(dir(dai.node)):
    if not item.startswith('_'):
        print(f"  - {item}")

# XLinkOut 別名チェック
print("\n=== Alternative names ===")
print("dai.node.XLinkOut:", getattr(dai.node, 'XLinkOut', 'NOT FOUND'))
print("dai.XLinkOut:", getattr(dai, 'XLinkOut', 'NOT FOUND'))

# Pipeline のメソッド
print("\n=== Pipeline methods for XLink ===")
pipeline = dai.Pipeline()
print([m for m in dir(pipeline) if 'Link' in m or 'XLink' in m])
