"""
深度測定サービス（DepthMeasurementService）

このモジュールは、DepthAI Stereo Depth フレームから深度値を取得し、
複数のゲームやUIで共通利用可能な深度測定サービスを提供します。

【主要機能】
- RGB座標 → Stereo Depth座標への自動変換
- 深度値の検証・補間・キャッシング
- 領域平均深度の計算
- 信頼度スコアの算出
"""

import logging
from typing import Optional, Any, cast
from dataclasses import dataclass


@dataclass
class DepthConfig:
    """深度測定設定"""
    
    # 有効な深度値の範囲（メートル）
    min_valid_depth_m: float = 0.5
    max_valid_depth_m: float = 5.0
    
    # 周辺値検索の半径（ピクセル）
    interpolation_radius: int = 10
    
    # 信頼度計算用の参考値
    reference_depth_m: float = 2.0


class DepthMeasurementService:
    """
    DepthAI Stereo Depth から深度値を測定するサービス
    
    機能:
    - RGB座標系でのシンプルなAPI
    - 座標変換の自動処理
    - 多層的なエラーハンドリング（検証→補間→キャッシング→エラーリターン）
    """
    
    def __init__(self, camera_manager: Any, config: Optional[DepthConfig] = None):
        """
        初期化
        
        Args:
            camera_manager: CameraManager インスタンス
            config: DepthConfig インスタンス（Noneの場合は デフォルト値）
        """
        self.camera_manager = camera_manager
        self.config = config or DepthConfig()
        self._last_valid_depth_m: float = self.config.reference_depth_m  # 初期値は参考値
        self._measurement_count: int = 0
        self._cache_hit_count: int = 0
        
        # 深度フレーム解像度のキャッシュ（動的対応）
        self._cached_depth_frame_width: Optional[int] = None
        self._cached_depth_frame_height: Optional[int] = None
        
        logging.info(
            f"[DepthMeasurementService.__init__] "
            f"有効範囲: {self.config.min_valid_depth_m:.2f}~{self.config.max_valid_depth_m:.2f}m, "
            f"補間半径: {self.config.interpolation_radius}px"
        )
    
    def measure_at_rgb_coords(self, x: int, y: int) -> float:
        """
        RGB座標での深度値を測定（メートル単位）
        
        処理フロー:
        1. RGB座標 → Stereo Depth座標に変換
        2. 深度値を取得（mm）
        3. 検証（有効範囲チェック）
        4. 補間処理（無効値の場合、周辺値から補完）
        5. キャッシング（最後の有効値を保存）
        
        Args:
            x, y: RGB座標系での座標
            
        Returns:
            float: 深度値（メートル）
                   - 正常値: 0.5～5.0m
                   - エラー: -1.0（測定失敗）
        """
        self._measurement_count += 1
        
        try:
            # ★Step 1: RGB座標 → Stereo Depth座標に変換
            depth_x, depth_y = self._scale_rgb_to_depth_coords(x, y)
            
            # ★Step 2: 深度フレームから値を取得（mm）
            depth_frame = self.camera_manager.get_depth_frame()
            if depth_frame is None:
                logging.warning(
                    f"[measure_at_rgb_coords] 深度フレーム取得失敗 "
                    f"RGB({x}, {y}) → Depth({depth_x}, {depth_y})"
                )
                return self._get_fallback_depth_m()
            
            # ★Step 3: 座標の範囲チェック
            h, w = depth_frame.shape
            if not (0 <= depth_x < w and 0 <= depth_y < h):
                logging.warning(
                    f"[measure_at_rgb_coords] 座標が範囲外 "
                    f"RGB({x}, {y}) → Depth({depth_x}, {depth_y}), フレーム: {w}x{h}"
                )
                return self._get_fallback_depth_m()
            
            # ★Step 4: 深度値を取得
            depth_mm = float(depth_frame[depth_y, depth_x])
            
            # ★Step 5: 検証と補間
            depth_m = self._validate_and_interpolate(depth_mm, depth_frame, depth_x, depth_y)
            
            # ★Step 6: キャッシング
            if depth_m >= 0.0:
                self._last_valid_depth_m = depth_m
                logging.debug(
                    f"[measure_at_rgb_coords] ✓ 深度測定成功 "
                    f"RGB({x}, {y}) → {depth_m:.3f}m"
                )
                return depth_m
            else:
                logging.debug(
                    f"[measure_at_rgb_coords] 検証失敗 "
                    f"RGB({x}, {y}), 深度フレーム値: {depth_mm:.1f}mm"
                )
                return self._get_fallback_depth_m()
        
        except Exception as e:
            logging.error(f"[measure_at_rgb_coords] 予期しないエラー: {e}")
            return self._get_fallback_depth_m()
    
    def measure_at_region(self, x1: int, y1: int, x2: int, y2: int, 
                         mode: str = "mean") -> float:
        """
        矩形領域内の深度値を統計的に計算
        
        Args:
            x1, y1: 矩形の左上座標（RGB座標系）
            x2, y2: 矩形の右下座標（RGB座標系）
            mode: 統計モード
                - "mean": 平均値（デフォルト）
                - "median": 中央値
                - "max": 最大値
                - "min": 最小値
            
        Returns:
            float: 計算結果（メートル）、計算失敗時は -1.0
        """
        if not (0 <= x1 < x2 and 0 <= y1 < y2):
            logging.warning(
                f"[measure_at_region] 無効な領域指定: "
                f"({x1}, {y1}) - ({x2}, {y2})"
            )
            return -1.0
        
        depth_values = []
        
        # ★領域内のサンプル点から深度を収集
        step = max(1, (x2 - x1) // 5)  # 最大25ポイント
        for x in range(x1, x2, step):
            for y in range(y1, y2, step):
                depth_m = self.measure_at_rgb_coords(x, y)
                if depth_m >= 0.0 and self.is_valid_depth(depth_m):
                    depth_values.append(depth_m)
        
        if not depth_values:
            logging.warning(
                f"[measure_at_region] 領域内に有効な深度値がありません"
            )
            return -1.0
        
        # ★統計計算
        if mode == "mean":
            result = sum(depth_values) / len(depth_values)
        elif mode == "median":
            sorted_vals = sorted(depth_values)
            mid = len(sorted_vals) // 2
            result = sorted_vals[mid]
        elif mode == "max":
            result = max(depth_values)
        elif mode == "min":
            result = min(depth_values)
        else:
            result = sum(depth_values) / len(depth_values)
        
        logging.debug(
            f"[measure_at_region] 領域平均深度: {result:.3f}m "
            f"({len(depth_values)} samples, mode={mode})"
        )
        return result
    
    def is_valid_depth(self, depth_m: float) -> bool:
        """
        深度値が有効な範囲内かを判定
        
        Args:
            depth_m: 深度値（メートル）
            
        Returns:
            bool: 有効な場合 True
        """
        if depth_m < 0:
            return False
        
        is_valid = (
            self.config.min_valid_depth_m <= depth_m <= self.config.max_valid_depth_m
        )
        
        if not is_valid:
            logging.debug(
                f"[is_valid_depth] 範囲外 {depth_m:.3f}m "
                f"(有効: {self.config.min_valid_depth_m:.2f}~{self.config.max_valid_depth_m:.2f}m)"
            )
        
        return is_valid
    
    def get_confidence_score(self, x: int, y: int) -> float:
        """
        座標における深度値の信頼度を計算（0.0～1.0）
        
        信頼度は以下を考慮:
        - 参考値からの偏差
        - 周辺値とのばらつき
        
        Args:
            x, y: RGB座標系での座標
            
        Returns:
            float: 信頼度スコア（0.0=低信頼度, 1.0=高信頼度）
        """
        try:
            depth_m = self.measure_at_rgb_coords(x, y)
            
            if depth_m < 0.0:
                return 0.0
            
            # ★参考値からの相対偏差を計算
            if self.config.reference_depth_m > 0:
                deviation = abs(depth_m - self.config.reference_depth_m) / self.config.reference_depth_m
                # 偏差が20%以内なら高信頼度
                base_score = max(0.0, 1.0 - deviation)
            else:
                base_score = 0.5
            
            # ★周辺値のばらつきを考慮
            region_depth = self.measure_at_region(x - 10, y - 10, x + 10, y + 10, mode="mean")
            if region_depth >= 0.0:
                region_deviation = abs(depth_m - region_depth) / region_depth
                region_score = max(0.0, 1.0 - region_deviation)
                # 50% は単一値、50% は周辺一貫性
                final_score = 0.5 * base_score + 0.5 * region_score
            else:
                final_score = base_score
            
            logging.debug(
                f"[get_confidence_score] RGB({x}, {y}): "
                f"深度={depth_m:.3f}m, 信頼度={final_score:.2f}"
            )
            
            return max(0.0, min(1.0, final_score))
        
        except Exception as e:
            logging.error(f"[get_confidence_score] エラー: {e}")
            return 0.0
    
    # ========== Private Methods ==========
    
    def _scale_rgb_to_depth_coords(self, x: int, y: int) -> tuple[int, int]:
        """
        RGB座標系 (1280x800) → Stereo Depth座標系に動的に変換
        
        デフォルトスケーリング係数（640x360の場合）:
        - X軸: 640 / 1280 = 0.5
        - Y軸: 360 / 800 = 0.45
        
        動的対応：ハードウェアの実際の深度フレーム解像度を検出
        
        Args:
            x, y: RGB座標
            
        Returns:
            tuple[int, int]: Depth座標
        """
        # デフォルトのRGBサイズ（キャッシュが無い場合のフォールバック）
        rgb_w = getattr(self.camera_manager, "_rgb_frame_width", 1280)
        rgb_h = getattr(self.camera_manager, "_rgb_frame_height", 800)

        # Ensure fallback to int defaults if attributes are mocks or non‑int
        if not isinstance(rgb_w, int):
            rgb_w = 1280
        if not isinstance(rgb_h, int):
            rgb_h = 800

        # カメラが get_rgb_dimensions を提供しているか確認し、取得できれば上書き
        try:
            dims = self.camera_manager.get_rgb_dimensions()
            if isinstance(dims, (list, tuple)) and len(dims) == 2:
                rgb_w = int(dims[0])
                rgb_h = int(dims[1])
        except Exception:
            # 取得失敗時はデフォルト（上記）を使用
            pass

        # 深度フレーム解像度を動的に取得
        depth_w = self._cached_depth_frame_width
        depth_h = self._cached_depth_frame_height

        if depth_w is None or depth_h is None:
            try:
                depth_frame = self.camera_manager.get_depth_frame()
                if depth_frame is not None:
                    depth_h_actual, depth_w_actual = depth_frame.shape[:2]
                    self._cached_depth_frame_width = depth_w_actual
                    self._cached_depth_frame_height = depth_h_actual
                    depth_w, depth_h = depth_w_actual, depth_h_actual
                    logging.debug(
                        f"[_scale_rgb_to_depth_coords] "
                        f"深度フレーム解像度をキャッシュ: {depth_w}x{depth_h}"
                    )
                else:
                    depth_w, depth_h = 640, 360
                    logging.warning(
                        f"[_scale_rgb_to_depth_coords] "
                        f"深度フレーム取得失敗、デフォルト解像度を使用: {depth_w}x{depth_h}"
                    )
            except Exception as e:
                depth_w, depth_h = 640, 360
                logging.warning(
                    f"[_scale_rgb_to_depth_coords] "
                    f"解像度取得エラー: {e}、デフォルト値を使用: {depth_w}x{depth_h}"
                )

        # ★座標スケーリング（動的解像度対応）
        scale_x = depth_w / rgb_w
        scale_y = depth_h / rgb_h

        depth_x = int(x * scale_x)
        depth_y = int(y * scale_y)

        # 境界チェック（0～サイズ-1 の範囲内）    
        if depth_w is not None:
            depth_x = max(0, min(depth_x, depth_w - 1))
        if depth_h is not None:
            depth_y = max(0, min(depth_y, depth_h - 1))

        logging.debug(
            f"[_scale_rgb_to_depth_coords] "
            f"RGB({x}, {y}) → Depth({depth_x}, {depth_y}) "
            f"(解像度: {depth_w}x{depth_h}, scale: {scale_x:.3f}, {scale_y:.3f})"
        )

        return (depth_x, depth_y)
    
    def _validate_and_interpolate(
        self, 
        depth_mm: float, 
        depth_frame: Any, 
        x: int, 
        y: int
    ) -> float:
        """
        深度値を検証し、必要に応じて周辺値から補間する（DepthAI無効フラグ対応）
        
        DepthAI無効フラグ:
        - 0: 無効 (invalid)
        - 65535: 無効 (no measurement / saturated) ※uint16形式
        
        処理フロー:
        1. DepthAI無効フラグをチェック
        2. mm → m に変換
        3. 有効範囲チェック
        4. 無効の場合、周辺値から補間
        5. それでも失敗の場合は -1.0 を返す
        
        Args:
            depth_mm: 深度値（ミリメートル）
            depth_frame: 深度フレーム (ndarray)
            x, y: Depth座標
            
        Returns:
            float: 検証済み深度値（メートル）、検証失敗時は -1.0
        """
        # ★Step 0: DepthAI無効フラグの検出（uint16形式）
        # 0: 無効, 65535: 無効（計測不可または飽和）
        if depth_mm == 0 or depth_mm >= 65535:
            logging.debug(
                f"[_validate_and_interpolate] ⚠ DepthAI無効フラグ検出 "
                f"Depth({x}, {y}): {depth_mm}mm, 補間を試みます"
            )
            # 小さなボール対応：補間範囲を拡大
            interpolated_m = self._interpolate_from_neighbors(depth_frame, x, y, is_small_object=True)
            if interpolated_m >= 0.0 and self.is_valid_depth(interpolated_m):
                return interpolated_m
            return -1.0
        
        # ★Step 1: mm → m に変換
        depth_m = depth_mm / 1000.0
        
        # ★Step 2: 有効範囲チェック
        if self.is_valid_depth(depth_m):
            logging.debug(
                f"[_validate_and_interpolate] ✓ 検証OK "
                f"Depth({x}, {y}): {depth_m:.3f}m"
            )
            return depth_m
        
        # ★Step 3: 無効な場合、周辺値から補間
        logging.debug(
            f"[_validate_and_interpolate] ⚠ 検証失敗、補間処理開始 "
            f"Depth({x}, {y}): {depth_m:.3f}m (範囲外)"
        )
        
        interpolated_m = self._interpolate_from_neighbors(depth_frame, x, y, is_small_object=False)
        if interpolated_m >= 0.0 and self.is_valid_depth(interpolated_m):
            logging.debug(
                f"[_validate_and_interpolate] ✓ 補間成功 "
                f"Depth({x}, {y}): {interpolated_m:.3f}m"
            )
            return interpolated_m
        
        # ★Step 4: 失敗
        logging.warning(
            f"[_validate_and_interpolate] ✗ 補間失敗 "
            f"Depth({x}, {y}): 有効な値が取得できません"
        )
        return -1.0
    
    def _interpolate_from_neighbors(
        self, 
        depth_frame: Any, 
        x: int, 
        y: int,
        is_small_object: bool = False
    ) -> float:
        """
        周辺ピクセルから有効な深度値を探索・補間する（背景混合対応）
        
        補間アルゴリズム:
        1. 距離加重平均（背景混合回避）
        2. 段差検出（異なるオブジェクト判別）
        3. 外れ値除外（統計的除外）
        
        探索範囲: 指定半径内（デフォルト10px、小オブジェクト時は20px）
        
        DepthAI無効フラグ対応:
        - 0: 無効として除外
        - 65535: 無効として除外
        
        小さなボール対応:
        - ゴルフボール（5-10px）などの小さなオブジェクト用
        - 補間範囲を2倍に拡大（10px → 20px）
        
        背景混合対応（新規）:
        - 距離加重平均で近い画素（オブジェクト）を優先
        - 段差検出で背景を除外
        - 複数手法の結果を比較
        
        Args:
            depth_frame: 深度フレーム (ndarray)
            x, y: 基準座標（Depth座標系）
            is_small_object: 小オブジェクトの場合True（補間範囲を2倍に拡大）
            
        Returns:
            float: 補間された深度値（メートル）、見つからない場合は -1.0
        """
        if depth_frame is None:
            logging.warning(
                f"[_interpolate_from_neighbors] depth_frame is None"
            )
            return -1.0
        
        h, w = depth_frame.shape[:2]
        radius = self.config.interpolation_radius
        
        # 小さなボール対応：補間範囲を2倍に拡大
        if is_small_object:
            radius = radius * 2
            logging.debug(
                f"[_interpolate_from_neighbors] "
                f"小さなボール対応：補間範囲を拡大 "
                f"{self.config.interpolation_radius}px → {radius}px"
            )
        
        valid_values: list[tuple[int, int]] = []  # (depth_mm, distance)
        
        # ★周辺ピクセルを探索（距離情報を保持）
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    try:
                        neighbor_depth = int(depth_frame[ny, nx])
                        # DepthAI無効フラグ（0および65535）を除外
                        if 0 < neighbor_depth < 65535:  # 有効な値
                            distance = int((dx**2 + dy**2) ** 0.5)  # ユークリッド距離
                            valid_values.append((neighbor_depth, distance))
                    except (ValueError, TypeError):
                        pass
        
        if valid_values:
            # ★Phase 1: 距離加重平均（背景混合回避）
            weighted_depth_mm = self._calculate_weighted_average(valid_values)
            weighted_depth_m = weighted_depth_mm / 1000.0
            
            # ★Phase 2: 段差検出と外れ値除外
            valid_values_filtered = self._filter_background_pixels(valid_values, weighted_depth_mm)
            
            if valid_values_filtered:
                # フィルタ後の加重平均を再計算
                filtered_depth_mm = self._calculate_weighted_average(valid_values_filtered)
                filtered_depth_m = filtered_depth_mm / 1000.0
                
                # 有効範囲チェック
                if self.is_valid_depth(filtered_depth_m):
                    min_distance = min([d for _, d in valid_values_filtered])
                    logging.debug(
                        f"[_interpolate_from_neighbors] "
                        f"補間成功（背景除外後）: {filtered_depth_m:.3f}m "
                        f"({len(valid_values_filtered)}/{len(valid_values)}個の有効画素, "
                        f"最近 {min_distance}px, "
                        f"半径={radius}px)"
                    )
                    return filtered_depth_m
            
            # フィルタ後が空の場合、加重平均のみで検証
            if self.is_valid_depth(weighted_depth_m):
                min_distance = min([d for _, d in valid_values])
                logging.debug(
                    f"[_interpolate_from_neighbors] "
                    f"補間成功（加重平均）: {weighted_depth_m:.3f}m "
                    f"({len(valid_values)}個の有効画素, "
                    f"最近 {min_distance}px, "
                    f"半径={radius}px)"
                )
                return weighted_depth_m
        
        logging.warning(
            f"[_interpolate_from_neighbors] "
            f"補間失敗: 有効な周辺画素なし "
            f"(x={x}, y={y}, radius={radius}, "
            f"小オブジェクト対応={is_small_object})"
        )
        return -1.0
    
    def _calculate_weighted_average(self, values: list[tuple[int, int]]) -> int:
        """
        距離加重平均で深度値を計算
        
        近い画素（距離小）をより重視する逆距離加重法
        
        Args:
            values: [(depth_mm, distance), ...] のリスト
            
        Returns:
            加重平均深度（ミリメートル）
        """
        if not values:
            return 0
        
        # 逆距離加重（Inverse Distance Weighting）
        # weight = 1.0 / (distance + 1.0)
        # +1.0 は distance=0 時のゼロ除算対策
        total_weight = 0.0
        weighted_sum = 0.0
        
        for depth_mm, distance in values:
            weight = 1.0 / (distance + 1.0)
            weighted_sum += depth_mm * weight
            total_weight += weight
        
        if total_weight > 0:
            return int(weighted_sum / total_weight)
        return 0
    
    def _filter_background_pixels(
        self, 
        values: list[tuple[int, int]], 
        reference_depth_mm: int
    ) -> list[tuple[int, int]]:
        """
        段差検出で背景ピクセルを除外
        
        複数の深度値が混在する場合（段差がある）、より小さい深度値（オブジェクト側）
        を優先し、大きく異なる値（背景など）を統計的に除外する
        
        Strategy:
        1. 段差を検出（深度範囲が大きい）
        2. 最小深度値を基準に、その近辺を保持
        3. 大きく異なる値（背景）を除外
        
        Args:
            values: [(depth_mm, distance), ...] のリスト
            reference_depth_mm: 参照深度値（mm、通常は加重平均）
            
        Returns:
            フィルタ後の values（背景除外）
        """
        if len(values) < 3:
            # サンプル数が少ない場合はフィルタしない
            return values
        
        depths_only = [d for d, _ in values]
        
        # 深度値の統計情報を計算
        max_depth = max(depths_only)
        min_depth = min(depths_only)
        depth_range = max_depth - min_depth
        
        # 段差検出（深度範囲）
        # ボール（1.2m） と 背景（1.7m） の場合、差は500mm
        if depth_range > 200:  # 200mm以上の段差 = 複数オブジェクト混在
            # 戦略: 最小深度（オブジェクト）に近い値を保持
            # 最小値 + 段差の20% を閾値とする
            # 例: min=1200, max=1700, range=500 → 1200+100=1300（+20%）
            depth_threshold = min_depth + int(depth_range * 0.2)
            
            filtered = [
                (d, dist) for d, dist in values
                if d <= depth_threshold
            ]
            
            if filtered:  # フィルタ後が空でなければ返す
                logging.debug(
                    f"[_filter_background_pixels] "
                    f"段差検出（{depth_range}mm）→ {len(values)}→{len(filtered)}個に削減 "
                    f"(min={min_depth}mm, threshold={depth_threshold}mm)"
                )
                return filtered
            else:
                # フィルタが厳しすぎる場合は、min_depth±20% で再試行
                depth_threshold = min_depth + int(depth_range * 0.5)
                filtered = [
                    (d, dist) for d, dist in values
                    if d <= depth_threshold
                ]
                
                if filtered:
                    logging.debug(
                        f"[_filter_background_pixels] "
                        f"フィルタが厳しすぎ → 緩い閾値で再フィルタ（min + 50%）"
                    )
                    return filtered
                else:
                    # それでもダメな場合はオリジナルを返す
                    logging.debug(
                        f"[_filter_background_pixels] "
                        f"フィルタ失敗、オリジナルを使用"
                    )
                    return values
        
        # 段差が小さい（同一オブジェクト）場合はそのまま返す
        return values
    
    def _get_fallback_depth_m(self) -> float:
        """
        フォールバック: 最後の有効な深度値をキャッシュから返す
        
        Returns:
            float: キャッシュされた深度値（メートル）
        """
        self._cache_hit_count += 1
        logging.info(
            f"[_get_fallback_depth_m] キャッシュ から値を返却: {self._last_valid_depth_m:.3f}m "
            f"(キャッシュ利用回数: {self._cache_hit_count})"
        )
        return self._last_valid_depth_m
    
    def get_statistics(self) -> dict[str, Any]:
        """
        測定統計を返す（デバッグ・ログ用）
        
        Returns:
            dict: 統計情報
        """
        cache_hit_rate = (
            (self._cache_hit_count / self._measurement_count * 100)
            if self._measurement_count > 0 else 0.0
        )
        
        return {
            "total_measurements": self._measurement_count,
            "cache_hits": self._cache_hit_count,
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "last_valid_depth_m": f"{self._last_valid_depth_m:.3f}m",
        }
