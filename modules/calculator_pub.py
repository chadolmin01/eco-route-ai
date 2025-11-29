from datetime import datetime

class PublicTransportCalculator:
    def __init__(self):
        # 1. 기본 배출 원단위 (g/p.km) - 평균 탑승률 기준
        self.base_factors = {
            1: 3.0,    # 지하철 (평균)
            2: 38.0,   # 시내버스
            3: 0.0,    # 도보
            99: 50.0   # 광역/좌석버스 (디젤 비중 높음)
        }

        # 2. 지하철 노선별 효율 등급 (낮을수록 좋음)
        # 노후 노선은 전력 효율이 낮아 배출량이 높음
        self.subway_efficiency = {
            "1호선": 1.2, "2호선": 1.0, "3호선": 1.1, "4호선": 1.1,
            "5호선": 1.0, "6호선": 1.0, "7호선": 1.0, "8호선": 1.0,
            "9호선": 0.9, "신분당선": 0.8, "GTX-A": 0.7
        }

    def get_time_occupancy_factor(self):
        """
        [시간대별 혼잡도 보정]
        사람이 많을수록(Rush Hour) 1인당 배출량은 줄어듦 (나누기 N 효과)
        """
        hour = datetime.now().hour
        
        # 출퇴근 시간 (07~09시, 17~19시): 효율 좋음
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            return 0.6 
        
        # 심야/새벽 (22~05시): 효율 나쁨 (빈 차)
        if hour >= 22 or hour <= 5:
            return 1.8 
            
        return 1.0

    def get_congestion_penalty(self, mode, bus_type, avg_car_speed):
        """
        [승용차 속도 연동] 도로 혼잡 시 버스 배출량 할증
        """
        # 지하철(1)이나 도보(3)는 도로 상황 영향 없음
        if mode in [1, 3] or avg_car_speed is None:
            return 1.0

        penalty = 1.0
        
        # 승용차 속도가 20km/h 이하 (정체)
        if avg_car_speed <= 20:
            if bus_type in [10, 11, 12, 13, 14]: # 광역/직행 (전용차로 혜택)
                penalty = 1.1 
            else: # 일반 시내버스 (같이 막힘)
                penalty = 1.5 
                
        # 승용차 속도가 40km/h 이하 (서행)
        elif avg_car_speed <= 40:
            if bus_type in [10, 11, 12, 13, 14]:
                penalty = 1.05 
            else:
                penalty = 1.2
                
        return penalty

    def calculate(self, path_data, avg_car_speed=None):
        """
        대중교통 경로 배출량 계산 (승용차 속도 연동 포함)
        path_data: ODsay API의 subPath 데이터
        avg_car_speed: 승용차 경로 분석에서 나온 평균 속도
        """
        total_co2 = 0
        
        info = path_data.get('info', {})
        total_dist = info.get('totalDistance', 0) / 1000 # m -> km
        total_time = info.get('totalTime', 0) # 분
        
        sub_paths = path_data.get('subPath', [])
        details = []
        
        # 시간대 보정 계수
        time_factor = self.get_time_occupancy_factor()

        for sub in sub_paths:
            mode = sub.get('trafficType', 3) # 1:지하철, 2:버스, 3:도보
            dist_km = sub.get('distance', 0) / 1000
            
            # 1. 기본 계수 선택
            factor = self.base_factors.get(mode, 0)
            
            lane_name = "도보"
            bus_type = 0 # 0:일반, 11~:광역 등
            
            lanes = sub.get('lane', [])
            if lanes:
                lane_info = lanes[0]
                lane_name = lane_info.get('busNo') or lane_info.get('name')
                
                # 버스 타입 확인 (광역버스 감지)
                if mode == 2:
                    bus_type = lane_info.get('type', 0)
                    # ODsay type: 10(외곽), 11(간선급행), 12(좌석), 13(마을), 14(공항) 등
                    if bus_type in [10, 11, 12, 13, 14]:
                        factor = self.base_factors[99] # 광역버스 계수 적용
                        lane_name += " (광역)"

                # 지하철 노후도 반영
                if mode == 1:
                    # 노선 이름에서 '수도권' 같은 접두사 제거하고 매칭
                    eff_ratio = 1.0
                    for line_key, ratio in self.subway_efficiency.items():
                        if line_key in lane_name:
                            eff_ratio = ratio
                            break
                    factor = factor * eff_ratio

            # 2. 동적 보정 적용 (시간대 + 도로혼잡)
            if mode != 3: # 도보는 제외
                traffic_penalty = self.get_congestion_penalty(mode, bus_type, avg_car_speed)
                factor = factor * time_factor * traffic_penalty

            # 최종 구간 배출량
            emission = dist_km * factor
            total_co2 += emission
            
            details.append({
                "mode": mode,
                "name": lane_name,
                "dist": dist_km,
                "co2": emission
            })

        return {
            "total_co2": total_co2,
            "total_dist": total_dist,
            "total_time": total_time,
            "details": details
        }