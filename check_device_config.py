import depthai as dai

# Device.Config の確認
config = dai.Device.Config()
print("Device.Config attributes:")
attrs = [a for a in dir(config) if not a.startswith('_')]
for attr in sorted(attrs)[:30]:
    print(f"  - {attr}")

# setXLinkChunkSize の確認
print("\nDevice.Config methods/properties (filtered):")
methods = [m for m in dir(config) if 'pipeline' in m.lower() or 'xlink' in m.lower()]
print(f"  Pipeline/XLink-related: {methods}")

print("\nAll Config attributes (filtered):")
for attr in sorted(attrs):
    if any(x in attr.lower() for x in ['pipeline', 'xlink', 'queue', 'stream']):
        print(f"  - {attr}")
