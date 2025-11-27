"""DepthAI 互換性ラッパー（レガシー）

depthai 3.1.0 では以下の変更が発生:
1. XLinkOut/XLinkIn ノードが廃止
2. Device(pipeline) コンストラクタが廃止
3. Output.createOutputQueue() で直接キューを生成
4. device.getOutputQueue() が廃止

このモジュールの関数は現在は使用されていません。
代わりに camera_manager.py の initialize_camera() メソッドで
depthai 3.1.0 推奨パターンを実装しています。

参考: tests/3_1_test.py
"""
from typing import Any, Optional, Sequence
import logging

import depthai as dai


def safe_link(src: Any, dst: Any, src_candidates: Optional[Sequence[str]] = None, dst_candidates: Optional[Sequence[str]] = None) -> bool:
    """src の出力ピン候補と dst の入力ピン候補を順に試してリンクする。

    成功したら True を返す。失敗したら False を返す。
    
    【depthai 3.1.0 対応】
    """
    if src_candidates is None:
        src_candidates = ['out', 'video', 'preview', 'isp']
    if dst_candidates is None:
        dst_candidates = ['input', 'inputLeft', 'inputRight', 'left', 'right']

    for s in src_candidates:
        if not hasattr(src, s):
            continue
        src_pin = getattr(src, s)
        for d in dst_candidates:
            if not hasattr(dst, d):
                continue
            dst_pin = getattr(dst, d)
            try:
                src_pin.link(dst_pin)
                return True
            except Exception:
                continue
    return False


# ============================================================================
# 以下の関数はレガシーであり、depthai 3.1.0 では使用されていません。
# 新しいコードは camera_manager.py::initialize_camera() を参考にしてください。
# ============================================================================

def create_node(pipeline: Any, node_cls: Any, legacy_name: Optional[str] = None) -> Any:
    """【非推奨】パイプライン上にノードを作成する。
    
    depthai 3.1.0 では pipeline.create(dai.node.Xxx) を直接使用してください。
    """
    try:
        return pipeline.create(node_cls)
    except Exception:
        logging.debug(f"pipeline.create({node_cls.__name__}) failed")

    if legacy_name and hasattr(pipeline, legacy_name):
        try:
            return getattr(pipeline, legacy_name)()
        except Exception:
            logging.debug(f"legacy create {legacy_name} failed")

    raise RuntimeError(f'Could not create node for {node_cls}')


class XLinkOutProxy:
    """【非推奨】XLinkOut ノードの代替（3.1.0 用）。
    
    depthai 3.1.0 では XLinkOut が廃止されたため使用不可。
    代わりに Output.createOutputQueue() を使用してください。
    """
    def __init__(self, output_node: Any) -> None:
        self.output_node = output_node
        self._stream_name: Optional[str] = None

    def setStreamName(self, name: str) -> None:
        self._stream_name = name

    def get_output_queue(self) -> Any:
        if self._stream_name:
            return self.output_node.createOutputQueue(name=self._stream_name)
        else:
            return self.output_node.createOutputQueue()


def create_xlinkout(output_node: Any) -> XLinkOutProxy:
    """【非推奨】XLinkOut ノードの代替を返す。
    
    depthai 3.1.0 では XLinkOut が廃止されたため使用不可。
    代わりに Output.createOutputQueue() を使用してください。
    """
    return XLinkOutProxy(output_node)  # type: ignore


def create_device(pipeline: Any = None, device_info: Any = None) -> Any:
    """【非推奨】Device の生成を行う。
    
    depthai 3.1.0 では pipeline.start() で自動管理されます。
    Device を手動で作成する必要はありません。
    """
    import time
    try:
        if device_info is None:
            device_infos = []
            for device_detection_attempt in range(5):
                device_infos = dai.Device.getAllAvailableDevices()
                logging.debug(f'Device detection attempt {device_detection_attempt + 1}: {[d.name for d in device_infos]}')
                if len(device_infos) > 0:
                    break
                if device_detection_attempt < 4:
                    wait_time = 0.2
                    logging.debug(f'No devices found, waiting {wait_time}s before retry...')
                    time.sleep(wait_time)
            
            if len(device_infos) > 0:
                device_info = device_infos[0]
            else:
                logging.error('No available devices found.')
                raise RuntimeError(
                    'No DepthAI devices detected. Please check that the device is connected and '
                    'no other process is using it.'
                )
        
        if device_info is None:
            raise RuntimeError('device_info is None')
            
        device_name = device_info.name if hasattr(device_info, 'name') else str(device_info)
        logging.debug(f'Attempting to open device: {device_name}')
        
        last_error = None
        for attempt in range(3):
            try:
                if attempt > 0:
                    logging.debug(f'Re-enumerating devices (attempt {attempt + 1})...')
                    fresh_devices = dai.Device.getAllAvailableDevices()
                    for d in fresh_devices:
                        if d.name == device_name:
                            device_info = d
                            break
                
                device = dai.Device(device_info)
                logging.info(f'Device created successfully: {device_name} (attempt {attempt + 1})')
                return device
                
            except Exception as device_err:
                last_error = device_err
                logging.warning(f'Device creation attempt {attempt + 1} failed: {type(device_err).__name__}: {device_err}')
                
                if attempt < 2:
                    logging.debug(f'Waiting 1s before retry...')
                    time.sleep(1)
        
        raise RuntimeError(f'Failed to create device after 3 attempts: {last_error}') from last_error
        
    except Exception as e:
        logging.error(f'create_device failed: {type(e).__name__}: {e}')
        raise


def get_output_queue(device: Any, name: str, **kwargs: Any) -> Any:
    """【非推奨】出力キューを取得する。
    
    depthai 3.1.0 では device.getOutputQueue() は廃止されました。
    代わりに Output.createOutputQueue() を直接使用してください。
    """
    if device is None:
        raise RuntimeError('device is None')
    
    if not hasattr(device, 'getOutputQueue'):
        raise AttributeError(
            'device.getOutputQueue() is not available in depthai 3.1.0. '
            'Use Output.createOutputQueue() instead.'
        )
    
    try:
        return device.getOutputQueue(name=name, **kwargs)
    except TypeError:
        try:
            return device.getOutputQueue(name, **kwargs)
        except Exception as e:
            logging.error(f'getOutputQueue failed for {name}: {e}')
            raise
    except Exception as e:
        logging.error(f'getOutputQueue failed for {name}: {e}')
        raise
