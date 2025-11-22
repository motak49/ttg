"""
セキュリティ問題の修正を示すためのファイル
"""

import secrets
import random

# B311: random.choice と random.randint の使用を secrets に置き換える例
def secure_random_choice(items):
    """セキュアな乱数選択"""
    return secrets.choice(items)

def secure_random_int(min_val, max_val):
    """セキュアな乱数生成"""
    return secrets.randbelow(max_val - min_val + 1) + min_val

# B101: assert 文を削除または条件付き実行に変更
def check_value(value):
    """値の検証（assert を使用せず）"""
    if value < 0:
        raise ValueError("値は負数であってはなりません")
    return True

# B110: try-except-pass ブロックを修正
def safe_operation():
    """安全な操作"""
    try:
        # 何かの処理
        result = 10 / 0  # 例としてゼロ除算
        return result
    except ZeroDivisionError as e:
        print(f"エラーが発生しました: {e}")
        return None

# 例として backend/moving_target.py の修正
def example_moving_target_fix():
    """moving_target.py の修正例"""
    dx = secure_random_int(-5, 5) if random.randint(0, 1) == 0 else secrets.randbelow(10) - 5
    dy = secure_random_int(-5, 5) if random.randint(0, 1) == 0 else secrets.randbelow(10) - 5
    return dx, dy

if __name__ == "__main__":
    print("セキュリティ問題の修正例を実行中...")
    print(f"secure_random_choice: {secure_random_choice([1, 2, 3])}")
    print(f"secure_random_int: {secure_random_int(1, 10)}")
    check_value(5)  # OK
    try:
        check_value(-1)
    except ValueError as e:
        print(f"ValueError: {e}")
