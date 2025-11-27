"""
Camera Manager Tests
====================

カメラマネージャーのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any

# インターフェースをインポート
from backend.interfaces import CameraInterface
# 実装クラスをインポート
from backend.camera_manager import CameraManager


def test_camera_manager_inherits_interface() -> None:
    """CameraManager が CameraInterface を正しく実装しているかを確認"""
    camera = CameraManager()
    assert isinstance(camera, CameraInterface)


@patch('depthai.Device')
@patch('depthai.Pipeline')
def test_initialize_camera_success(mock_pipeline: Mock, mock_device: Mock) -> None:
    """カメラ初期化が成功するテスト（depthai 3.1.0 対応）"""
    # モックの設定
    mock_pipeline_instance = Mock()
    mock_device_instance = Mock()
    mock_pipeline.return_value = mock_pipeline_instance
    mock_device.return_value = mock_device_instance
    
    # depthai 3.1.0 ではパイプラインにノードがあって、
    # Output.createOutputQueue() でキューを生成する
    # そのため、create_node() の戻り値にこれを設定
    mock_color_cam = Mock()
    mock_video_output = Mock()
    mock_video_output.createOutputQueue.return_value = Mock()
    mock_color_cam.video = mock_video_output
    
    mock_stereo = Mock()
    mock_depth_output = Mock()
    mock_depth_output.createOutputQueue.return_value = Mock()
    mock_stereo.depth = mock_depth_output
    
    # create_node() をモック
    def mock_create_node(pipeline, node_cls, legacy_name=None):
        if 'ColorCamera' in str(node_cls):
            return mock_color_cam
        elif 'StereoDepth' in str(node_cls):
            return mock_stereo
        else:
            return Mock()
    
    with patch('backend.camera_manager.create_node', side_effect=mock_create_node):
        # カメラマネージャーの作成と初期化
        camera = CameraManager()
        result = camera.initialize_camera()
        
        # 結果の確認
        assert result is True
        assert camera.is_initialized() is True
        mock_pipeline.assert_called_once()
        # depthai 3.1.0: Device() はパイプラインなしで呼び出される
        mock_device.assert_called_once()


@patch('depthai.Device')
@patch('depthai.Pipeline')
def test_initialize_camera_failure(mock_pipeline, mock_device) -> None:
    """カメラ初期化が失敗するテスト（depthai 3.1.0 対応）"""
    # モックの設定 - 例外をスロー
    mock_pipeline_instance = Mock()
    mock_pipeline.return_value = mock_pipeline_instance
    mock_device.side_effect = Exception("デバイス接続エラー")
    
    # depthai 3.1.0: Device() はパイプラインなしで呼び出される
    with patch('backend.camera_manager.create_device') as mock_create_device:
        mock_create_device.side_effect = Exception("デバイス接続エラー")
        
        # カメラマネージャーの作成と初期化
        camera = CameraManager()
        result = camera.initialize_camera()
        
        # 結果の確認
        assert result is False
        assert camera.is_initialized() is False


def test_get_frame_success() -> None:
    """カメラフレーム取得が成功するテスト"""
    # カメラを初期化
    camera = CameraManager()
    # 初期化状態を偽装
    camera._initialized = True
    
    # モックの設定
    mock_queue = Mock()
    mock_frame = Mock()
    mock_frame.getCvFrame.return_value = "mock_frame_data"
    camera.video_stream = mock_queue
    mock_queue.get.return_value = mock_frame
    
    # フレーム取得
    frame = camera.get_frame()
    
    # 結果の確認
    assert frame == "mock_frame_data"
    mock_queue.get.assert_called_once()


def test_get_frame_failure() -> None:
    """カメラフレーム取得が失敗するテスト"""
    # カメラを初期化
    camera = CameraManager()
    # 初期化状態を偽装
    camera._initialized = True
    
    # モックの設定 - 例外をスロー
    mock_queue = Mock()
    camera.video_stream = mock_queue
    mock_queue.get.side_effect = Exception("フレーム取得エラー")
    
    # フレーム取得
    frame = camera.get_frame()
    
    # 結果の確認 - プレースホルダー画像が返されることを確認
    assert frame is not None  # 何かが返るはず（プレースホルダー）


def test_close_camera() -> None:
    """カメラクローズ処理のテスト"""
    # カメラを初期化
    camera = CameraManager()
    # 初期化状態を偽装
    camera._initialized = True
    mock_device = Mock()
    camera.device = mock_device
    
    # クローズ処理
    camera.close_camera()
    
    # 結果の確認
    mock_device.close.assert_called_once()
    assert camera.device is None
    assert camera.pipeline is None
    assert camera.video_stream is None
    assert camera._initialized is False
