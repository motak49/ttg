# 「前面スクリーン向き移動物体検知」仕様変更可能性分析

## 実装可能性: ✅ **可能（推奨）**

色ベースのトラッキングから「深度軸での移動物体検知」へ仕様変更することは技術的に十分可能です。むしろ現在の問題（深度値の不正確性）を根本的に解決できるアプローチです。

---

## 現在の仕様（色ベース）の問題点

### 1. 色ベース検知の限界
```
フレーム解析: HSV色域で赤いボールを検出 ← 照度変動に弱い
    ↓
深度取得: その座標から深度値を取得 ← タイミング、ノイズの影響大
    ↓
スクリーン深度と比較: depth ≈ 1.701m?
    ↓
問題: ボール検出成功 → 深度値が不正確 → 誤ったヒット判定
```

**具体的な問題:**
- 赤いボールが見つかった → その座標の深度値を信じる
- しかし深度値は計測ノイズ → 0, 無効値、または古い値
- フォールバック先はスクリーン深度（1.7m）
- ボール実位置が 1.2m でも 1.7m として判定される

### 2. 照度変動への弱さ
- 照度変動でHSV範囲から外れるとボール検出失敗
- 色判定の信頼性が環境に依存

---

## 提案する新仕様：「深度軸での移動検知」

### 基本コンセプト
```
【物体移動検知の流れ】

フレームt-1の深度フレーム
    ↓
フレームtの深度フレーム ← 各ピクセルで深度変化を計算
    ↓
深度変化マップ: Δdepth = depth_t - depth_t-1
    ↓
大きな深度減少（物体が近づいている）を検知
    ↓
移動ベクトル + 深度ベクトルで軌道判定
    ↓
「スクリーンに向かう物体」をフィルタリング
    ↓
衝突判定: depth ≈ screen_depth ?
```

### 利点
1. ✅ **色に依存しない** → 照度変動に強い
2. ✅ **深度信号は直接** → リアルタイム性が高い
3. ✅ **背景分離が自動** → 移動していない背景は検知されない
4. ✅ **複数物体対応** → 大きく移動する物体を優先
5. ✅ **ノイズ耐性** → 補間処理でノイズ除外可能

---

## 実装アーキテクチャ

### 新しいトラッカークラス構成

```
MotionBasedTracker (新規クラス)
├── get_frame_pair()
│   └─ t-1フレームと tフレームの深度フレームを取得
├── compute_depth_change_map()
│   ├─ 各ピクセルでΔdepth計算
│   ├─ ノイズフィルタリング
│   └─ 移動領域を抽出
├── detect_moving_objects()
│   ├─ 深度変化が大きい領域を検知
│   ├─ 輪郭検出
│   └─ 候補物体を複数取得
├── filter_approaching_objects()
│   ├─ 深度が減少（近づいている）物体のみ抽出
│   ├─ スクリーン方向への移動成分を確認
│   └─ 最も信頼度高い物体を選択
└── get_collision_candidate()
    └─ 衝突候補（位置・深度）を返す
```

### 既存BallTrackerとの関係
```
┌─ BallTracker (既存、色ベース) ← 廃止 or モード選択
├─ MotionBasedTracker (新規、深度ベース) ← デフォルト
└─ HybridTracker (オプション)
    └─ 両方を組み合わせる（色 AND 深度変化）
```

---

## 技術的実装詳細

### 1. 深度差分マップの計算

```python
def compute_depth_change_map(depth_frame_t, depth_frame_t_minus_1):
    """
    深度フレーム間の変化を計算（物体が近づいているか検知）
    
    入力: 
        depth_frame_t: 現在フレームの深度 [640x360]
        depth_frame_t_minus_1: 前フレームの深度
    
    出力:
        delta_depth: 深度変化 (負 = 近づいている)
        moving_mask: 移動領域のバイナリマスク
    """
    # Step 1: 無効値フィルタリング
    valid_mask = (depth_frame_t > 0) & (depth_frame_t_minus_1 > 0)
    
    # Step 2: 深度差分計算（mm単位）
    delta_depth = depth_frame_t.astype(float) - depth_frame_t_minus_1.astype(float)
    
    # Step 3: 物体が近づいている領域（Δdepth < -50mm が移動と判定）
    moving_mask = (delta_depth < -50) & valid_mask
    
    # Step 4: ノイズ除外（5ピクセル以下の領域は除外）
    moving_mask = cv2.morphologyEx(moving_mask, cv2.MORPH_OPEN, kernel_5x5)
    
    return delta_depth, moving_mask
```

### 2. 移動物体検知

```python
def detect_moving_objects(moving_mask, delta_depth):
    """
    移動領域から物体候補を検出
    
    出力:
        List[(center_x, center_y, avg_delta_depth, confidence)]
    """
    contours, _ = cv2.findContours(moving_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 30:  # 最小面積フィルタ
            continue
        
        x, y, w, h = cv2.boundingRect(contour)
        center_x = x + w // 2
        center_y = y + h // 2
        
        # 領域内の平均深度変化（負の値 = 近づいている）
        roi = delta_depth[y:y+h, x:x+w]
        avg_delta = np.mean(roi[moving_mask[y:y+h, x:x+w]])
        
        # 信頼度: |Δdepth| が大きいほど高い（大きく近づいている）
        confidence = min(abs(avg_delta) / 200.0, 1.0)
        
        candidates.append({
            'center': (center_x, center_y),
            'delta_depth': avg_delta,
            'confidence': confidence,
            'area': area
        })
    
    return candidates
```

### 3. スクリーン向き判定

```python
def is_approaching_screen(candidate, prev_position, screen_area):
    """
    候補物体が「スクリーン向かって移動」しているか判定
    
    判定ロジック:
    1. 深度が減少していて (Δdepth < 0)
    2. スクリーン領域への方向成分がある (trajectory の深度軸成分)
    3. スクリーン領域内に存在する
    """
    center = candidate['center']
    delta_depth = candidate['delta_depth']
    
    # 判定1: 深度減少（近づいている）
    if delta_depth >= 0:
        return False, 0.0
    
    # 判定2: 軌道方向の確認
    if prev_position is not None:
        px, py = prev_position
        cx, cy = center
        movement_vector = np.array([cx - px, cy - py])
        # スクリーン中心への方向ベクトル
        screen_center = calculate_screen_center(screen_area)
        approach_vector = np.array([screen_center[0] - cx, screen_center[1] - cy])
        
        # コサイン類似度（同じ方向なら正、反対方向なら負）
        if np.linalg.norm(movement_vector) > 0 and np.linalg.norm(approach_vector) > 0:
            cosine_sim = np.dot(movement_vector, approach_vector) / (
                np.linalg.norm(movement_vector) * np.linalg.norm(approach_vector)
            )
            directional_score = max(0, cosine_sim)  # 0.0～1.0
        else:
            directional_score = 1.0  # 停止時は無視
    else:
        directional_score = 1.0
    
    # 判定3: スクリーン領域内
    in_screen = point_in_polygon(center, screen_area)
    
    overall_confidence = (
        abs(delta_depth) / 200.0 * directional_score * (1.0 if in_screen else 0.5)
    )
    
    return overall_confidence > 0.5, overall_confidence
```

---

## 移行戦略

### フェーズ1: 実装・検証（推奨1～2日）
```
1. MotionBasedTracker クラスを新規作成
2. 深度差分マップ計算の実装・テスト
3. 移動物体検知ロジック実装
4. スクリーン向き判定実装
```

### フェーズ2: 統合（1～2日）
```
5. BallTracker / MotionBasedTracker の選択可能化
6. DepthService との統合
7. OxGame での使用開始
```

### フェーズ3: 最適化（1～2日）
```
8. パラメータ調整（閾値、感度）
9. ノイズ耐性の向上
10. 複数物体シナリオでのテスト
```

---

## 既存コードとの互換性

### インターフェース互換性
```python
# 既存インターフェース
class BallTrackerInterface:
    def get_hit_area(self, frame) -> Optional[Tuple[int, int, float]]:
        pass

# MotionBasedTracker も同じインターフェース実装
class MotionBasedTracker(BallTrackerInterface):
    def get_hit_area(self, frame):
        # 深度ベース検知を実装
        return (x, y, depth)
```

### 利点
- ✅ `ox_game.py` の変更なし
- ✅ インターフェース層で透過的に置き換え可能
- ✅ フォールバック可能（問題があれば色ベースに戻す）

---

## 実装に必要な追加情報

| 項目 | 現状 | 必要な対応 |
|-----|------|--------|
| **深度フレーム取得** | 実装済み | 毎フレーム2つのフレームペアを管理 |
| **差分計算** | 新規 | ノイズフィルタリング付きで実装 |
| **物体検知** | 部分的 | 深度ベースの輪郭検出に変更 |
| **軌道判定** | 既存（角度） | 深度軸成分を追加 |
| **パラメータ** | 要調整 | 環境に応じた閾値設定 |

---

## リスク評価と対策

| リスク | 確度 | 対策 |
|--------|------|------|
| 深度フレームのタイミングずれ | 低 | フレーム同期機構で対応 |
| ノイズによる誤検知 | 中 | 補間 + モルフォロジー演算で低減 |
| 複数物体時の混乱 | 低 | 信頼度スコアリングで優先度付け |
| 性能低下（FPS）| 低 | GPU最適化で対応（CUDA、OpenCL） |

---

## 結論と推奨

**✅ 実装可能・推奨**

現在の色ベーストラッキングの問題（深度値の不正確性）は、根本的には以下の理由で解決困難です：
1. 色検出後の深度値は計測のタイミングに左右される
2. 静止背景の色に反応する可能性
3. 照度変動への弱さ

これに対し、深度軸での移動物体検知は：
- 深度値を**直接的に利用**（リアルタイム性高い）
- **移動していない背景は検知されない**（自動分離）
- **複数物体に対応可能**（信頼度スコアリング）

**→ 短期的には現修正で改善が見込まれます**
**→ 長期的には深度ベース検知への移行がベストプラクティスです**

---

## 実装予定スケジュール例

```
日程: 2025年12月3日〜12月5日

12/3 (木):
  - MotionBasedTracker 実装
  - 基本動作確認
  - ノイズ対策

12/4 (金):
  - OxGame 統合
  - パラメータ調整
  - テスト実行

12/5 (土):
  - 微調整・最適化
  - ドキュメント作成
```

---

## 質問・フォローアップ

実装を進める場合、以下を確認させてください：

1. **優先度**: 深度ベース検知への完全移行 vs 色ベース + 深度の併用？
2. **タイムライン**: いつまでに実装したいか？
3. **テスト環境**: 現在のカメラセットアップで即座にテスト可能か？
4. **パラメータ**: 調整用の外部設定ファイルが必要か？
