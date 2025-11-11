# tests/test_validation.py
"""
validation.py のテスト
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from common.validation import check_persistent_settings, create_default_settings, validate_and_create_defaults

def test_validation_functions():
    """validation.py の関数が正しく動作するかをテスト"""
    # テスト前にデフォルト設定を作成
    create_default_settings()
    
    # バリデーションを実行
    is_ok, messages = check_persistent_settings()
    
    # すべてのファイルが存在し、有効な状態であることを確認
    assert is_ok == True
    assert len(messages) == 0
    
    print("validation.py のテストに成功しました")

if __name__ == "__main__":
    test_validation_functions()
