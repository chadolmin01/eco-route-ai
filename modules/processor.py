import math
import statistics

def haversine(lat1, lon1, lat2, lon2):
    try:
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    except:
        return 0

class DataProcessor:
    def __init__(self, google_api):
        self.google = google_api

    # 1. 중앙값 필터
    def apply_median_filter(self, elevations, window_size=5):
        if not elevations: return []
        filtered = []
        half = window_size // 2
        length = len(elevations)
        for i in range(length):
            start = max(0, i - half)
            end = min(length, i + half + 1)
            filtered.append(statistics.median(elevations[start:end]))
        return filtered

    # 2. 이동 평균 필터
    def apply_moving_average(self, elevations, window_size=10):
        if not elevations: return []
        smoothed = []
        half = window_size // 2
        length = len(elevations)
        for i in range(length):
            start = max(0, i - half)
            end = min(length, i + half + 1)
            subset = elevations[start:end]
            smoothed.append(sum(subset) / len(subset))
        return smoothed

    def process_route(self, route_data):
        processed_segments = []
        coords_to_query = [] 
        temp_segments = []

        sections = route_data.get('sections', [])
        prev_speed = 0

        # --- 1. 파싱 및 샘플링 ---
        for section in sections:
            roads = section.get('roads', [])
            for road in roads:
                name = road.get('name', '일반 도로')
                speed = road.get('traffic_speed', 0)
                if speed <= 0: speed = road.get('limit_speed', 30)
                state = road.get('traffic_state', 0)
                
                vertexes = road.get('vertexes') or road.get('vertex')
                if not vertexes: continue

                path_coords = []
                for i in range(0, len(vertexes), 2):
                    if i+1 < len(vertexes):
                        lat = round(vertexes[i+1], 6)
                        lon = round(vertexes[i], 6)
                        path_coords.append((lat, lon))

                if not path_coords: continue

                start_pt = path_coords[0]
                accumulated_dist = 0
                segment_path_dist = 0

                for i in range(len(path_coords) - 1):
                    curr_pt = path_coords[i]
                    next_pt = path_coords[i+1]
                    
                    step_dist = haversine(curr_pt[0], curr_pt[1], next_pt[0], next_pt[1])
                    accumulated_dist += step_dist
                    segment_path_dist += step_dist
                    
                    if accumulated_dist >= 100 or i == len(path_coords) - 2:
                        end_pt = next_pt
                        coords_to_query.append(start_pt)
                        coords_to_query.append(end_pt)
                        
                        delta_v = speed - prev_speed
                        
                        straight_dist = haversine(start_pt[0], start_pt[1], end_pt[0], end_pt[1])
                        sinuosity = segment_path_dist / straight_dist if straight_dist > 0 else 1.0
                        
                        temp_segments.append({
                            "name": name,
                            "distance_m": accumulated_dist,
                            "speed_kph": speed,
                            "congestion": state,
                            "delta_v": delta_v,
                            "p_start": start_pt,
                            "p_end": end_pt,
                            "sinuosity": sinuosity
                        })
                        
                        start_pt = end_pt
                        accumulated_dist = 0
                        segment_path_dist = 0
                prev_speed = speed

        # --- 2. 구글 API 호출 ---
        if not coords_to_query: return []
        unique_coords = list(dict.fromkeys(coords_to_query))
        raw_elevations = self.google.get_elevations_bulk(unique_coords)
        alt_map = {pt: alt for pt, alt in zip(unique_coords, raw_elevations)}

        merged_data = []
        for item in temp_segments:
            item['start_alt'] = alt_map.get(item.pop('p_start'), 0)
            item['end_alt'] = alt_map.get(item.pop('p_end'), 0)
            merged_data.append(item)

        # --- 3. 필터링 및 재구성 ---
        if merged_data:
            raw_elevs = [d['start_alt'] for d in merged_data]
            raw_elevs.append(merged_data[-1]['end_alt'])
            
            median_elevs = self.apply_median_filter(raw_elevs, window_size=5)
            smoothed_elevs = self.apply_moving_average(median_elevs, window_size=10)
            
            current_alt = smoothed_elevs[0]
            stats = {"tunnel": 0, "real": 0, "neighbor_avg": 0}
            
            # 이전 구간의 확정된 경사도 저장용 (초기값 0)
            prev_final_grade = 0

            for i, item in enumerate(merged_data):
                dist = item['distance_m']
                
                # 현재 스무딩 데이터 기준 다음 높이
                target_next = smoothed_elevs[i+1]
                
                if dist > 0:
                    raw_grade = ((target_next - current_alt) / dist) * 100
                else:
                    raw_grade = 0
                
                speed = item['speed_kph']
                sinuosity = item['sinuosity']
                is_highway = (speed >= 80) or any(k in item['name'] for k in ["고속", "IC", "JC", "순환", "대교", "터널"])
                
                final_grade = raw_grade

                # ==================================================
                # 🚦 [필터링 로직]
                # ==================================================
                if is_highway:
                    # 고속도로: 기존 로직 유지 (엄격)
                    if abs(raw_grade) < 0.5:
                        final_grade = 0
                    elif abs(raw_grade) > 7.0:
                        if sinuosity < 1.05:
                            final_grade = 0
                            stats["tunnel"] += 1
                        else:
                            limit = 5.0
                            if raw_grade > limit: final_grade = limit
                            elif raw_grade < -limit: final_grade = -limit
                            stats["real"] += 1
                    else:
                        limit = 5.0
                        if raw_grade > limit: final_grade = limit
                        elif raw_grade < -limit: final_grade = -limit
                else:
                    # [일반도로] 15% 초과 시 이웃 평균 보정
                    if abs(raw_grade) > 15.0:
                        # 1. 다음 구간의 예상 경사도 계산 (Look-ahead)
                        next_grade_est = 0
                        if i + 1 < len(merged_data):
                            next_dist = merged_data[i+1]['distance_m']
                            # i+1번째와 i+2번째 고도 차이 이용
                            if i + 2 < len(smoothed_elevs) and next_dist > 0:
                                next_grade_est = ((smoothed_elevs[i+2] - smoothed_elevs[i+1]) / next_dist) * 100
                        
                        # 2. 이전 구간(prev_final_grade)과 다음 구간(next_grade_est)의 평균
                        avg_grade = (prev_final_grade + next_grade_est) / 2
                        
                        # 3. 그래도 너무 크면 15%로 안전 제한 (Safety Clamp)
                        if avg_grade > 15.0: avg_grade = 15.0
                        elif avg_grade < -15.0: avg_grade = -15.0
                        
                        final_grade = avg_grade
                        stats["neighbor_avg"] += 1
                    
                    # 15% 이하는 그대로 인정
                    else:
                        final_grade = raw_grade

                # 재구성
                next_alt = current_alt + (dist * final_grade / 100)
                
                item['start_alt'] = current_alt
                item['end_alt'] = next_alt
                item['grade_pct'] = final_grade
                
                processed_segments.append(item)
                
                # 다음 루프를 위한 갱신
                current_alt = next_alt
                prev_final_grade = final_grade

        if processed_segments:
            total_len = sum(s['distance_m'] for s in processed_segments) / 1000
            print(f"      ✂️ [Filter] 터널{stats['tunnel']}회 / 산악{stats['real']}회 / 이웃보정{stats['neighbor_avg']}회")
        
        return processed_segments