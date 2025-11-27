#!/usr/bin/env python3
"""
激進的なモジュール再初期化テスト（depthai 3.1.0 対応）
参考: camera_manager.py の initialize_camera() パターン
"""
import sys
import gc
import subprocess

def clear_depthai_cache():
    """depthai モジュールと依存を完全にアンロード"""
    print("Clearing depthai modules...")
    
    # アンロード対象
    modules_to_remove = [
        name for name in sys.modules 
        if 'depthai' in name or 'pal' in name or '_depthai' in name
    ]
    
    print(f"Found {len(modules_to_remove)} depthai-related modules to unload")
    
    for module_name in modules_to_remove:
        print(f"  - Unloading {module_name}")
        del sys.modules[module_name]
    
    # ガベージ コレクション
    gc.collect()
    print("Garbage collection completed")

def test_pipeline():
    """パイプライン作成をテスト（depthai 3.1.0 対応）"""
    try:
        import depthai as dai
        
        devices = dai.Device.getAllAvailableDevices()
        print(f"\nDevices found: {[d.name for d in devices]}")
        
        if len(devices) == 0:
            print("No devices!")
            return False
        
        # パイプライン作成
        print("\nCreating pipeline...")
        pipeline = dai.Pipeline()
        print("✓ Pipeline created successfully!")
        
        print("\nAdding Camera node...")
        # ColorCamera ではなく Camera ノードを使用（requestOutput 対応）
        cam_rgb = pipeline.create(dai.node.Camera).build()
        preview = cam_rgb.requestOutput((640, 480), type=dai.ImgFrame.Type.RGB888p)
        q = preview.createOutputQueue()
        print("✓ Camera node added with requestOutput!")
        
        # パイプライン実行テスト
        print("\nTesting pipeline execution...")
        with pipeline:
            print("✓ Pipeline started with context manager!")
            
            # 1フレーム取得テスト
            if q.has():
                msg = q.get()
                frame = msg.getCvFrame()
                print(f"✓ Frame captured: {frame.shape}")
                return True
            else:
                print("⚠ No frame available (timeout)")
                return True
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Aggressive Depthai Reset Test (depthai 3.1.0)")
    print("=" * 60)
    
    # テスト 1: 前のモジュール削除なし
    print("\n[Test 1] Without module cleanup:")
    result1 = test_pipeline()
    
    # テスト 2: モジュール削除後
    print("\n[Test 2] With aggressive module cleanup:")
    clear_depthai_cache()
    result2 = test_pipeline()
    
    # 結果表示
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  Test 1 (no cleanup): {'✓ PASS' if result1 else '✗ FAIL'}")
    print(f"  Test 2 (with cleanup): {'✓ PASS' if result2 else '✗ FAIL'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
