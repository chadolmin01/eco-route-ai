import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# --- 모듈 임포트 ---
# 1. 승용차 & 분석 모듈
from modules.api_kakao import KakaoNavi
from modules.api_google import GoogleElevation
from modules.processor import DataProcessor
from modules.calculator import CarbonCalculator
from modules.visualizer import draw_comparison_graph 
from modules.api_weather import WeatherAPI
from modules.vehicle_db import VehicleDB

# 2. 대중교통 모듈
from modules.api_odsay import ODsayClient
from modules.calculator_pub import PublicTransportCalculator

def main():
    # 1. 환경 설정 로드
    load_dotenv()
    KAKAO_KEY = os.getenv("KAKAO_API_KEY")
    GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
    ODSAY_KEY = os.getenv("ODSAY_API_KEY")
    OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

    # 2. 인스턴스 초기화
    kakao = KakaoNavi(KAKAO_KEY)
    google = GoogleElevation(GOOGLE_KEY, use_mock=False)
    processor = DataProcessor(google)
    car_calculator = CarbonCalculator()
    weather_api = WeatherAPI(OPENWEATHER_KEY)
    vehicle_db = VehicleDB()
    
    odsay = ODsayClient(ODSAY_KEY)
    pub_calculator = PublicTransportCalculator()

    print("\n" + "=" * 70)
    print("      🌍 [졸업연구] 통합 탄소 배출량 분석 시스템 (Car vs Public)")
    print("=" * 70)
    
    # 3. 사용자 입력 (차량 & 주소)
    print("\n🚗 [Step 1] 분석할 차량 타입을 선택하세요:")
    print("   1. 경차 (모닝, 레이 등)")
    print("   2. 중형 세단 (쏘나타, K5 등) [기본값]")
    print("   3. SUV (싼타페, 쏘렌토 등)")
    print("   4. 소형 트럭 (포터 등)")
    print("   5. 하이브리드 (그랜저 HEV 등)")
    print("   6. 전기차 (아이오닉5, 테슬라 등)")
    
    v_sel = input("👉 선택 (번호 입력): ") or "2"
    my_car = vehicle_db.get_vehicle_spec(v_sel)
    print(f"   ✅ 선택된 차량: {my_car['name']} (배출 특성 반영됨)")

    print("\n📍 [Step 2] 경로 입력 (도로명 주소 권장)")
    print("   - 예시: 경기 수원시 팔달구 덕영대로 924")
    
    start_addr = input("   👉 출발지: ") or "경기 수원시 팔달구 덕영대로 924"
    end_addr = input("   👉 도착지: ") or "서울 강남구 강남대로 396"

    # 4. 좌표 변환
    print(f"\n🔍 주소 변환 중...")
    sx, sy = kakao.get_coords(start_addr)
    ex, ey = kakao.get_coords(end_addr)

    if not sx or not ex:
        print("\n❌ 주소 변환에 실패했습니다. 올바른 주소를 입력해주세요.")
        return

    # 5. 날씨 정보 조회 (출발지 기준)
    print(f"\n🌦️ [Step 3] 현재 기상 상태 확인 중...")
    weather_info = weather_api.get_weather(sy, sx)
    print(f"   >>> 기온: {weather_info['temp']}°C | 습도: {weather_info['humidity']}% | 상태: {weather_info['condition']}")
    
    if weather_info['is_wet']: 
        print("   ☔ [Scope 1] 비/눈 감지 -> 노면 저항 계수 증가")
    if weather_info['temp'] > 25 or weather_info['temp'] < 10:
        print("   🔋 [Scope 2] 공조 장치(에어컨/히터) 부하 적용")

    # ==========================================
    # 🚗 PART 1. 승용차 분석 (Car Analysis)
    # ==========================================
    print(f"\n[1] 🚗 승용차 경로 분석 중... ({start_addr} -> {end_addr})")
    
    car_routes = kakao.get_multi_routes(start_addr, end_addr)
    car_results = [] 
    
    global_avg_car_speed = None 
    car_speeds_collector = []
    collected_car_data = [] # 시각화 데이터 모음

    if car_routes:
        print(f"   ✅ 총 {len(car_routes)}개의 승용차 경로를 발견했습니다.")
        
        for idx, route in enumerate(car_routes):
            strategy = route.get('strategy_label', '일반')
            print(f"   >>> 승용차 경로 {idx+1} [{strategy}] 정밀 분석 중...")
            
            # (1) 데이터 처리 (100m 리샘플링 + 10% 경사 제한)
            segments = processor.process_route(route)
            
            if not segments:
                print("      ⚠️ 유효한 구간 데이터가 없습니다. 건너뜁니다.")
                continue
            
            # (2) 탄소 배출량 계산 (VSP + 날씨 + 차량스펙)
            # calculate_weather_impact 함수 내부에서 vehicle_spec을 사용하도록 전달
            total_co2, add_g, weather_pct = car_calculator.calculate_weather_impact(
                segments, weather_info, vehicle_spec=my_car
            )
            
            total_dist = sum(s['distance_m'] for s in segments) / 1000
            
            # (3) 시간 및 속도
            duration_sec = route['summary']['duration']
            time_min = duration_sec / 60
            
            if time_min > 0:
                avg_speed = total_dist / (time_min / 60)
                car_speeds_collector.append(avg_speed)

            # (4) 시각화 데이터 수집
            stats = {
                'dist': total_dist, 
                'time': time_min, 
                'co2': total_co2,
                'weather_pct': weather_pct
            }
            
            collected_car_data.append({
                'segments': segments,
                'label': strategy,
                'stats': stats,
                'id': idx + 1
            })

            # (5) 결과 저장
            car_results.append({
                "Type": f"Car ({strategy})",
                "Route_ID": idx+1,
                "Distance_km": round(total_dist, 2),
                "Time_min": round(time_min, 0),
                "CO2_g": round(total_co2, 2),
                "Weather_Impact_pct": round(weather_pct, 1),
                "Efficiency": round(total_co2 / total_dist, 1) if total_dist else 0
            })
            
            print(f"      📊 [{strategy}] 거리: {total_dist:.1f}km | CO2: {total_co2:.0f}g (기상영향: {weather_pct:+.1f}%)")

        # 통합 그래프 생성
        if collected_car_data:
            timestamp = datetime.now().strftime("%H%M%S")
            img_name = f"data/images/car_comparison_{timestamp}.png"
            draw_comparison_graph(collected_car_data, start_addr, end_addr, img_name)

        # 전체 평균 속도 산출 (버스 패널티용)
        if car_speeds_collector:
            global_avg_car_speed = sum(car_speeds_collector) / len(car_speeds_collector)
            print(f"   🚦 현재 도로 승용차 평균 속도: {global_avg_car_speed:.1f} km/h")
            if global_avg_car_speed <= 20:
                print("      ⚠️ 정체 구간 감지! 버스 배출량 계산에 할증이 적용됩니다.")

    else:
        print("   ⚠️ 승용차 경로를 찾을 수 없습니다.")


    # ==========================================
    # 🚌 PART 2. 대중교통 분석 (Public Transport)
    # ==========================================
    print(f"\n[2] 🚌 대중교통 경로 분석 중... (ODsay API)")
    
    pub_data = odsay.search_path(sx, sy, ex, ey)
    pub_results = []

    if pub_data and 'path' in pub_data:
        paths = pub_data['path'][:3]
        
        for idx, path in enumerate(paths):
            # 대중교통 계산 (승용차 속도 연동)
            res = pub_calculator.calculate(
                {"info": path['info'], "subPath": path['subPath']},
                avg_car_speed=global_avg_car_speed
            )
            
            path_type_name = "복합"
            if path['pathType'] == 1: path_type_name = "지하철"
            elif path['pathType'] == 2: path_type_name = "버스"
            
            print(f"   >>> 대중교통 {idx+1} ({path_type_name}): CO2 {res['total_co2']:.0f}g ({res['total_time']}분)")

            pub_results.append({
                "Type": "Public",
                "Route_ID": idx+1,
                "Method": path_type_name,
                "Distance_km": round(res['total_dist'], 2),
                "Time_min": round(res['total_time'], 0),
                "CO2_g": round(res['total_co2'], 2),
                "Weather_Impact_pct": 0,
                "Efficiency": round(res['total_co2'] / res['total_dist'], 1) if res['total_dist'] else 0
            })
    else:
        print("   ⚠️ 대중교통 경로를 찾을 수 없습니다.")


    # ==========================================
    # 📊 PART 3. 최종 비교 리포트
    # ==========================================
    print("\n" + "="*50)
    print("             📢 최종 탄소 배출량 비교 리포트             ")
    print("="*50)

    rep_car = car_results[0] if car_results else None
    rep_pub = min(pub_results, key=lambda x: x['CO2_g']) if pub_results else None

    if rep_car:
        print(f"🚗 [승용차]  {rep_car['Time_min']}분 소요  |  배출량: {rep_car['CO2_g']} g 🔴")
        print(f"   ㄴ 차량: {my_car['name']}")
    
    if rep_pub:
        print(f"🚌 [대중교통] {rep_pub['Time_min']}분 소요  |  배출량: {rep_pub['CO2_g']} g 🟢")
        print(f"   ㄴ 추천수단: {rep_pub['Method']}")

    if rep_car and rep_pub:
        saved_co2 = rep_car['CO2_g'] - rep_pub['CO2_g']
        reduction_rate = (saved_co2 / rep_car['CO2_g']) * 100
        
        print("-" * 50)
        if saved_co2 > 0:
            print(f"💡 결론: 대중교통 이용 시 탄소 배출을 {reduction_rate:.1f}% ({saved_co2:.0f}g) 줄일 수 있습니다!")
            print(f"🌲 이는 소나무 {saved_co2 / 2770:.2f}그루가 1년간 흡수하는 탄소량과 같습니다.")
        else:
            print(f"💡 결론: 현재 선택한 차량(전기차/하이브리드 등)이나 교통 상황으로 인해 배출량 차이가 크지 않습니다.")
    
    print("="*50)

    # 통합 저장
    all_data = car_results + pub_results
    if all_data:
        df = pd.DataFrame(all_data)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not os.path.exists("data"):
            os.makedirs("data")
            
        csv_filename = f"data/final_result_{ts}.csv"
        df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
        print(f"\n💾 상세 분석 결과가 '{csv_filename}'에 저장되었습니다.")
        print("✨ 프로그램이 성공적으로 종료되었습니다.")

if __name__ == "__main__":
    main()