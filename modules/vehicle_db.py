class VehicleDB:
    def __init__(self):
        """
        차량별 제원 데이터베이스 (VSP 모델 변수용)
        
        [변수 설명]
        - type: 엔진 타입 (ice:내연기관, hev:하이브리드, ev:전기차)
        - weight_kg: 공차중량 + 탑승자 1인 (kg) -> VSP 운동에너지 항에 사용
        - drag_term: 공기저항 계수 항 (Cd * Area / Mass * 0.5 * rho)
          -> 값이 클수록 고속 주행 시 공기 저항을 많이 받음 (SUV/트럭 > 세단)
        - emission_factor: 내연기관 기준 배출량 가중치 (세단=1.0 기준)
        """
        self.specs = {
            "1": {
                "name": "경차 (Compact - Gasoline)",
                "type": "ice", 
                "weight_kg": 1100,      # 가벼움
                "drag_term": 0.000327,  # 무게 대비 면적이 커서 저항 항이 높음
                "emission_factor": 0.85 # 배기량이 작아 배출량 적음
            },
            "2": {
                "name": "중형 세단 (Sedan - Gasoline)",
                "type": "ice",
                "weight_kg": 1500,      # 기준값
                "drag_term": 0.000264,  # 공기역학적 설계 (저항 낮음)
                "emission_factor": 1.00 # 기준
            },
            "3": {
                "name": "SUV (Medium - Gasoline)",
                "type": "ice",
                "weight_kg": 1900,      # 무거움
                "drag_term": 0.000312,  # 전면 면적이 넓어 저항 큼
                "emission_factor": 1.30 # 엔진 부하 큼
            },
            "4": {
                "name": "소형 트럭 (Truck - Diesel)",
                "type": "ice",
                "weight_kg": 2500,      # 적재함 포함 가정
                "drag_term": 0.000345,  # 박스형 디자인 (공기저항 최악)
                "emission_factor": 1.60 # 디젤 엔진 특성상 탄소 배출 많음
            },
            "5": {
                "name": "하이브리드 (HEV - Grandeur급)",
                "type": "hev",
                "weight_kg": 1650,      # 배터리로 인해 동급 세단보다 무거움
                "drag_term": 0.000264,  # 세단과 동일한 공기역학
                "emission_factor": 0.70 # 회생제동/모터 개입으로 약 30% 절감
            },
            "6": {
                "name": "전기차 (EV - Ioniq 5급)",
                "type": "ev",
                "weight_kg": 2050,      # 대용량 배터리로 인해 매우 무거움 (관성 큼)
                "drag_term": 0.000290,  # CUV 형태 (세단과 SUV 사이)
                "emission_factor": 0.0  # 직접 배출 0 (계산기에서 전력량으로 별도 계산)
            }
        }

    def get_vehicle_spec(self, selection):
        """
        사용자 입력 번호(문자열)에 해당하는 스펙 반환
        입력이 잘못되면 기본값(2번 세단) 반환
        """
        return self.specs.get(str(selection), self.specs["2"])