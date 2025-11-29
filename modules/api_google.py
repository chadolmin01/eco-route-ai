import requests
import random
import math

class GoogleElevation:
    def __init__(self, api_key, use_mock=False):
        self.api_key = api_key
        self.use_mock = use_mock

    def get_elevations_bulk(self, coords_list):
        """
        [최종 수정] POST 방식 문제 해결을 위해 GET 방식으로 전환하되,
        URL 길이 제한(8192자)을 넘지 않도록 50개씩 끊어서 요청 (Chunking)
        """
        if not coords_list: return []

        # Mock 모드
        if self.use_mock:
            return [50 + random.uniform(-5, 50) for _ in range(len(coords_list))]

        results = []
        # GET 요청은 URL 길이가 한정되어 있으므로 안전하게 50개씩 끊음
        # (좌표 1개당 약 25자 * 50개 = 1250자 -> 아주 여유로움)
        chunk_size = 50 
        
        base_url = "https://maps.googleapis.com/maps/api/elevation/json"

        for i in range(0, len(coords_list), chunk_size):
            chunk = coords_list[i : i + chunk_size]
            
            # 1. 좌표 데이터 정제 (NaN 제거)
            valid_points = []
            for item in chunk:
                # 입력이 딕셔너리인지 튜플인지 확인
                if isinstance(item, dict):
                    lat, lon = item.get('lat'), item.get('lng')
                else:
                    lat, lon = item[0], item[1]

                if (lat is not None and lon is not None and 
                    not math.isnan(float(lat)) and not math.isnan(float(lon))):
                    # 소수점 6자리로 줄여서 URL 길이 절약
                    valid_points.append(f"{float(lat):.6f},{float(lon):.6f}")
                else:
                    valid_points.append("0,0")

            # 2. GET 파라미터 조립 (파이프 | 로 구분)
            locations_str = "|".join(valid_points)
            
            params = {
                "locations": locations_str,
                "key": self.api_key
            }
            
            try:
                # [핵심] POST가 아닌 GET 사용
                resp = requests.get(base_url, params=params, timeout=10)
                
                data = resp.json()
                if data['status'] == 'OK':
                    for res in data['results']:
                        results.append(res['elevation'])
                else:
                    print(f"   ⚠️ 구글 거절 ({data['status']}): {data.get('error_message')}")
                    results.extend([0] * len(chunk))
                    
            except Exception as e:
                print(f"   ⚠️ 연결 오류: {e}")
                results.extend([0] * len(chunk))
                
        return results