"""DepthAI のバージョン差に対応する軽量互換ヘルパー。

このモジュールはランタイムで利用可能な API を判定し、
古い `pipeline.createXxx()` 形式と新しい `pipeline.create(dai.node.Xxx)`
形式の両方に対応するためのラッパーを提供します。
"""
from typing import Any, Optional, Sequence
import logging

import depthai as dai


def create_node(pipeline: Any, node_cls: Any, legacy_name: Optional[str] = None) -> Any:
    """パイプライン上にノードを作成する。

    まず legacy_name が指定され、pipeline に該当メソッドがあればそれを呼ぶ。
    失敗した場合は `pipeline.create(node_cls)` を試す。
    最後に node_cls のクラス名から createXxx を自動推定して呼び出す。
    """
    # 1) 明示的なレガシーメソッド名
    if legacy_name and hasattr(pipeline, legacy_name):
        try:
            return getattr(pipeline, legacy_name)()
        except Exception:
            logging.debug(f"legacy create {legacy_name} failed, falling back")

    # 2) 新 API pipeline.create(node_cls)
    try:
        return pipeline.create(node_cls)
    except Exception:
        logging.debug("pipeline.create(node_cls) failed, trying legacy naming")

    # 3) node_cls の名前から createXxx を推定
    try:
        cls_name = getattr(node_cls, '__name__', None)
        if cls_name is None and hasattr(node_cls, '__qualname__'):
            cls_name = node_cls.__qualname__
        if cls_name:
            legacy = 'create' + cls_name
            if hasattr(pipeline, legacy):
                try:
                    return getattr(pipeline, legacy)()
                except Exception:
                    logging.debug(f"fallback legacy {legacy} failed")
    except Exception:
        pass

    raise RuntimeError('Could not create node for %s' % (node_cls,))


def create_xlinkout(pipeline: Any) -> Any:
    return create_node(pipeline, dai.node.XLinkOut, legacy_name='createXLinkOut')


def create_device(pipeline: Any) -> Any:
    """Device の生成を互換的に行う。

    古い API は `dai.Device(pipeline)` を直接受け取るが、
    新しい API では `dai.Device()` を生成して別途パイプラインを始める場合があるため
    どちらも試す。
    """
    try:
        # まず古いスタイルを試す
        return dai.Device(pipeline)
    except Exception:
        logging.debug('dai.Device(pipeline) failed, trying alternate start')
    try:
        dev = dai.Device()
        # 可能ならパイプラインを開始する（メソッド名の差を吸収）
        if hasattr(dev, 'startPipeline'):
            try:
                dev.startPipeline(pipeline)
            except Exception:
                logging.debug('startPipeline failed')
        elif hasattr(dev, 'start'):
            try:
                dev.start(pipeline)
            except Exception:
                logging.debug('start failed')
        return dev
    except Exception as e:
        logging.error(f'create_device failed: {e}')
        raise


def get_output_queue(device: Any, name: str, **kwargs) -> Any:
    """OutputQueue を互換的に取得するラッパー。

    `device.getOutputQueue(name=...)` を優先的に呼ぶが、存在しない場合は
    positional 引数で試す。
    """
    if device is None:
        raise RuntimeError('device is None')
    try:
        return device.getOutputQueue(name=name, **kwargs)
    except TypeError:
        # 位置引数バージョンを試す
        try:
            return device.getOutputQueue(name)
        except Exception as e:
            logging.error(f'getOutputQueue failed for {name}: {e}')
            raise
    except Exception as e:
        logging.error(f'getOutputQueue failed for {name}: {e}')
        raise


def safe_link(src: Any, dst: Any, src_candidates: Optional[Sequence[str]] = None, dst_candidates: Optional[Sequence[str]] = None) -> bool:
    """src の出力ピン候補と dst の入力ピン候補を順に試してリンクする。

    成功したら True を返す。失敗したら False を返す。
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
