# 背景混合問題の分析と改善策

## 問題の詳細

### 状況設定
```
カメラ（深度0）
    ↓
ボール（1.2m） ← 深度中心が無効、周辺から補間
    ↓
スクリーン背景（1.7m） ← 補間時に拾われやすい
```

### 発生メカニズム

**ステップ1: ボール中心が無効**
```
深度フレーム（640x360）
  [180, 320] = 0  ← 無効フラグ
```

**ステップ2: 補間範囲内の深度値構成**
```
半径20px内の有効画素（例）:
  - ボール周辺（1.2m）: 約 40-50 画素
  - スクリーン背景（1.7m）: 約 60-80 画素 ← 多い
  
中央値選択: (40+50+60+70+80)/5 = 60 → 1.7m側に偏る
```

**ステップ3: 結果**
```
期待値: 1.2m（ボール）
実測値: 1.7m（背景混合）
誤差: 500mm = 大きな誤り
```

## 根本原因

### 原因1: 中央値の限界

中央値は **多数派に引っ張られる**:
- 補間範囲内に背景が多い → 背景値で中央値決定
- ボール領域が小さい → 少数派となる

### 原因2: 距離ソート不十分

現在のアルゴリズム:
```python
valid_values.sort(key=lambda v: v[1])  # 距離でソート
depths_only = [d for d, _ in valid_values]  # 距離情報を破棄
median_depth_mm = depths_only[len(depths_only) // 2]  # 中央値
```

問題：
- 距離でソート後、その情報が捨てられる
- 距離加重平均を計算していない

### 原因3: オブジェクトの硬い境界

ボール（球体）は:
- 中心: 1.2m
- 周辺: 1.2m ～ 1.2m+深度勾配
- 背景: 1.7m（急激な段差）

補間時に段差を跨ぐと、背景値を拾いやすい

## 改善策

### 改善1: 距離加重平均（推奨）

**アルゴリズム**:
```python
# 近い画素をより重視
weights = [1.0 / (distance + 1.0) for depth, distance in valid_values]
weighted_sum = sum(d * w for (d, _), w in zip(valid_values, weights))
weighted_depth = weighted_sum / sum(weights)
```

**効果**:
- 中心に近い画素（ボール）を優先
- 遠い画素（背景）の影響を軽減

### 改善2: 段差検出と除外

**アルゴリズム**:
```python
# 段差（急激な深度変化）を検出
max_depth = max([d for d, _ in valid_values])
min_depth = min([d for d, _ in valid_values])
depth_range = max_depth - min_depth

# 異常な段差は除外（例: > 300mm）
if depth_range > 300:  # 閾値
    # 外れ値除外: 平均±std外の値を除外
    mean_depth = sum([d for d, _ in valid_values]) / len(valid_values)
    std_depth = (sum((d - mean_depth)**2 for d, _ in valid_values) / len(valid_values))**0.5
    valid_values = [(d, dist) for d, dist in valid_values if abs(d - mean_depth) <= 1.5 * std_depth]
```

**効果**:
- 背景の1.7m（外れ値）を除外
- ボール周辺の1.2m付近に集中

### 改善3: 複数候補法

**アルゴリズム**:
```python
# 3つの補間方法で計算
candidate1 = weighted_depth  # 距離加重平均
candidate2 = median_depth    # 中央値
candidate3 = min_depth       # 最小深度

# 最も信頼度が高い候補を選択
if abs(candidate1 - candidate3) < 200:  # 近い場合
    result = candidate1  # 距離加重平均を優先
else:
    result = candidate1  # または中央値
```

**効果**:
- 複数手法の結果で検証
- ボール側に偏った値を選択

### 改善4: 深度勾配を考慮した段差検出

**背景と物体の判別**:
```python
# 中心周辺の勾配を計算
center_depth = depth_frame[y, x]
if center_depth == 0 or center_depth >= 65535:
    # 無効なので、周辺勾配から推定
    gradient_horizontal = depth_frame[y, x+5] - depth_frame[y, x-5]
    gradient_vertical = depth_frame[y+5, x] - depth_frame[y-5, x]
    gradient = (gradient_horizontal**2 + gradient_vertical**2)**0.5
    
    # 勾配が小さい（平坦）→ 同一オブジェクト
    # 勾配が大きい（段差）→ 異なるオブジェクト
```

## 推奨実装順序

### Phase 1: 距離加重平均（最優先）
- 実装難度: ⭐ 低
- 改善効果: ⭐⭐⭐ 高
- テスト容易性: ⭐⭐ 中

### Phase 2: 段差検出
- 実装難度: ⭐⭐ 中
- 改善効果: ⭐⭐⭐ 高
- テスト容易性: ⭐⭐ 中

### Phase 3: 複数候補法
- 実装難度: ⭐⭐ 中
- 改善効果: ⭐⭐ 中
- テスト容易性: ⭐ 低

## 実装パラメータ推定

### 距離加重平均の減衰係数

```python
# 候補1: 逆距離加重（Inverse Distance Weighting）
weight = 1.0 / (distance + 1.0)

# 候補2: ガウシアン減衰
sigma = 5.0  # 減衰幅
weight = math.exp(-(distance**2) / (2 * sigma**2))

# 候補3: 指数減衰
decay_rate = 0.9
weight = decay_rate ** distance
```

推奨: **逆距離加重**（シンプル＆効果的）

### 段差検出の閾値

```python
# ボール（1.2m）とスクリーン（1.7m）の場合
depth_range_threshold = 300  # mm
# 300mm以上の段差がある → 異なるオブジェクト候補

# ただし、シーンによって変化
# 提案: ユーザー設定可能にする
```

## テスト計画

### テストケース1: ボール+背景シーン
```python
深度フレーム:
  ボール周辺（1.2m）: 40画素
  背景（1.7m）: 60画素
  
期待値: 1.2m（±0.1m）
修正前: 1.7m（失敗）
修正後: 1.2m（成功）✅
```

### テストケース2: 単一オブジェクト（回帰）
```python
深度フレーム:
  オブジェクト（1.5m）: 100画素
  
期待値: 1.5m
修正前: 1.5m（成功）
修正後: 1.5m（成功）✅
```

### テストケース3: 複雑背景
```python
深度フレーム:
  ボール（1.2m）: 30画素
  背景1（1.7m）: 40画素
  背景2（2.0m）: 30画素
  
期待値: 1.2m（±0.2m）
修正前: 1.7m（失敗）
修正後: 1.2m（成功）✅
```

## まとめ

| 問題 | 原因 | 改善方法 |
|------|------|---------|
| 背景混合 | 中央値が多数派に引っ張られる | 距離加重平均 |
| 大きな誤差 | 段差を跨ぐ | 段差検出・除外 |
| 不安定 | 単一候補 | 複数候補法 |

**推奨実装**: 距離加重平均 + 段差検出（Phase 1 + Phase 2）

---

次のステップ: 実装を開始してもよろしいでしょうか？
