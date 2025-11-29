import requests
import json

class KakaoNavi:
    def __init__(self, api_key):
        self.headers = {"Authorization": f"KakaoAK {api_key}"}

    def get_coords(self, query):
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        try:
            resp = requests.get(url, headers=self.headers, params={"query": query})
            
            # [디버깅 코드 추가] 상태 코드 확인
            if resp.status_code != 200:
                print(f"🔥 카카오 API 에러 ({resp.status_code}): {resp.text}")
                return None, None
                
            docs = resp.json().get('documents')
            if docs:
                return docs[0]['x'], docs[0]['y']
            else:
                print(f"⚠️ 검색 결과 없음: '{query}'에 대한 결과를 찾지 못했습니다.")
                return None, None
                
        except Exception as e:
            print(f"☠️ 연결 오류: {e}")
        return None, None

    def get_multi_routes(self, origin, dest):
        ox, oy = self.get_coords(origin)
        dx, dy = self.get_coords(dest)
        
        if not ox or not dx: return []

        url = "https://apis-navi.kakaomobility.com/v1/directions"
        
        # [핵심 수정] 전략을 더 강력하게 구성
        # 1. 추천 경로 (기본)
        # 2. 최단 거리 (Distance)
        # 3. 무료 도로 (Avoid Tolls) -> 강제로 국도로 보냄 (탄소 배출량 비교에 최고)
        strategies = [
            {
                "label": "추천경로",
                "params": {"priority": "RECOMMEND"}
            },
            {
                "label": "최단거리",
                "params": {"priority": "DISTANCE"}
            },
            {
                "label": "무료도로",
                "params": {"priority": "RECOMMEND", "avoid": "toll"} # 톨게이트 회피
            }
        ]
        
        collected_routes = []
        seen_signatures = set() 

        print(f"   🔄 3가지 전략(추천, 최단거리, 무료도로)으로 경로를 탐색합니다...")

        for strategy in strategies:
            label = strategy['label']
            custom_params = strategy['params']
            
            # 기본 파라미터 + 전략별 커스텀 파라미터 합치기
            base_params = {
                "origin": f"{ox},{oy}",
                "destination": f"{dx},{dy}",
                "alternatives": "false",
                "car_fuel": "GASOLINE",
                "car_type": "1"
            }
            final_params = {**base_params, **custom_params}
            
            try:
                resp = requests.get(url, headers=self.headers, params=final_params)
                if resp.status_code == 200:
                    data = resp.json()
                    routes = data.get('routes', [])
                    
                    if routes:
                        route = routes[0]
                        summary = route['summary']
                        
                        # 중복 제거 (거리와 시간이 1% 오차 내로 같으면 같은 경로로 간주)
                        dist = summary['distance']
                        dur = summary['duration']
                        
                        is_duplicate = False
                        for s_dist, s_dur in seen_signatures:
                            if abs(dist - s_dist) < 100 and abs(dur - s_dur) < 60:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            seen_signatures.add((dist, dur))
                            route['strategy_label'] = label 
                            collected_routes.append(route)
                            print(f"      👉 [{label}] 새로운 경로 확보 (거리: {dist/1000:.1f}km)")
                        else:
                            print(f"      ℹ️ [{label}] 기존 경로와 중복되어 제외됨")
                            
            except Exception as e:
                print(f"      ⚠️ API 호출 오류 ({label}): {e}")

        if not collected_routes:
            print("   ⚠️ 경로를 찾지 못했습니다.")

        return collected_routes