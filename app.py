import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os
import requests

# UI 모듈 임포트
from ui.styles import apply_styles
from ui.tab_compare import render_tab_compare
from ui.tab_terrain import render_tab_terrain
from ui.tab_info import render_tab_info

# 로직 모듈 임포트
from modules.api_kakao import KakaoNavi
from modules.api_google import GoogleElevation
from modules.processor import DataProcessor
from modules.calculator import CarbonCalculator
from modules.api_weather import WeatherAPI
from modules.vehicle_db import VehicleDB
from modules.api_odsay import ODsayClient
from modules.calculator_pub import PublicTransportCalculator

# --- [핵심] API 키 로드 헬퍼 함수 ---
def get_key(key_name):
    """
    1순위: Streamlit Cloud Secrets (배포 환경)
    2순위: 로컬 .env 파일 (개발 환경)
    """
    # 1. Streamlit Secrets 확인
    try:
        if key_name in st.secrets:
            return st.secrets[key_name]
    except FileNotFoundError:
        pass # 로컬에 secrets.toml이 없으면 무시
        
    # 2. 로컬 환경변수 확인 (.env)
    return os.getenv(key_name)

# --- 초기화 함수 ---
@st.cache_resource
def load_resources():
    load_dotenv() # 로컬용 .env 로드
    
    # [수정됨] get_key 함수를 사용하여 안전하게 키 로드
    kakao_key = get_key("KAKAO_API_KEY")
    google_key = get_key("GOOGLE_API_KEY")
    odsay_key = get_key("ODSAY_API_KEY")
    weather_key = get_key("OPENWEATHER_API_KEY")
    
    return {
        "kakao": KakaoNavi(kakao_key),
        "google": GoogleElevation(google_key, use_mock=False),
        "weather": WeatherAPI(weather_key),
        "odsay": ODsayClient(odsay_key),
        "v_db": VehicleDB(),
        "car_calc": CarbonCalculator(),
        "pub_calc": PublicTransportCalculator()
    }

def run_analysis(start, end, my_car, res):
    """분석 실행 로직"""
    kakao, odsay, weather_api = res['kakao'], res['odsay'], res['weather']
    
    # Processor는 매번 새로 생성 (구글 객체 주입)
    processor = DataProcessor(res['google']) 
    
    # 1. 좌표 변환
    sx, sy = kakao.get_coords(start)
    ex, ey = kakao.get_coords(end)
    
    if not sx or not ex:
        return None 

    # 2. 날씨 정보
    w_info = weather_api.get_weather(sy, sx)

    # 3. 승용차 분석
    car_routes = kakao.get_multi_routes(start, end)
    collected, car_summ, car_speeds = [], [], []
    
    # 이벤트 카운터
    events = {"uphill": 0, "congestion": 0, "weather_bad": 0} 

    if car_routes:
        # 대표 경로 이벤트 집계 (첫 번째 경로 기준)
        first_segs = processor.process_route(car_routes[0])
        if first_segs:
            for s in first_segs:
                if abs(s['grade_pct']) > 5.0: events['uphill'] += 1
                if s['speed_kph'] < 20: events['congestion'] += 1
            if w_info['is_wet'] or w_info['temp'] > 28 or w_info['temp'] < 5:
                events['weather_bad'] = 1

        for idx, route in enumerate(car_routes):
            strategy = route.get('strategy_label', '일반')
            segs = processor.process_route(route)
            if not segs: continue
            
            co2, _, w_pct = res['car_calc'].calculate_weather_impact(segs, w_info, my_car)
            dist = sum(s['distance_m'] for s in segs) / 1000
            time = route['summary']['duration'] / 60
            if time > 0: car_speeds.append(dist/(time/60))
            
            stats = {'dist': dist, 'time': time, 'co2': co2, 'weather_pct': w_pct}
            collected.append({'segments': segs, 'label': strategy, 'stats': stats, 'id': idx+1})
            car_summ.append({"Type": "Car", "Route": strategy, "CO2": co2, "Time": time, "Dist": dist})

    # 4. 대중교통 분석
    pub_raw = odsay.search_path(sx, sy, ex, ey)
    pub_summ = []
    
    if pub_raw and 'path' in pub_raw:
        avg_speed = sum(car_speeds)/len(car_speeds) if car_speeds else None
        for path in pub_raw['path'][:3]:
            r = res['pub_calc'].calculate({"info": path['info'], "subPath": path['subPath']}, avg_speed)
            p_type = "지하철" if path['pathType']==1 else "버스" if path['pathType']==2 else "복합"
            pub_summ.append({"Type": "Pub", "Route": p_type, "CO2": r['total_co2'], "Time": r['total_time'], "Dist": r['total_dist']})

    return {
        "coords": {'sx': sx, 'sy': sy, 'ex': ex, 'ey': ey},
        "weather": w_info,
        "car_data": {'collected': collected, 'summary': car_summ, 'events': events},
        "pub_data": pub_summ
    }

# --- 메인 실행 ---
def main():
    # 1. 디자인 적용
    apply_styles()
    
    # 2. 세션 초기화
    if 'analyzed' not in st.session_state: st.session_state['analyzed'] = False
    
    res = load_resources()

    # 헤더
    st.title("🌍 Eco-Route AI")
    st.markdown("##### VSP 물리 모델 기반 **초정밀 탄소 배출량 비교 분석 시스템**")
    st.divider()

    # 사이드바 (입력)
    with st.sidebar:
        st.header("⚙️ 설정")
        v_keys = list(res['v_db'].specs.keys())
        v_sel = st.selectbox("차종 선택", v_keys, format_func=lambda x: res['v_db'].specs[x]['name'], index=1)
        my_car = res['v_db'].get_vehicle_spec(v_sel)
        
        st.markdown(f"""<div style="background:#f8f9fa; padding:10px; border-radius:5px;">
            <b>{my_car['name']}</b><br>⚖️ {my_car['weight_kg']}kg / 💨 {my_car['drag_term']:.6f}</div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        s = st.text_input("출발지", "경기 수원시 팔달구 덕영대로 924")
        e = st.text_input("도착지", "서울 강남구 강남대로 396")
        
        st.write("")
        btn_run = st.button("🚀 분석 시작", type="primary", use_container_width=True)


    def show_current_ip():
        try:
            # 내 컴퓨터(서버)의 공인 IP를 알려주는 사이트 호출
            response = requests.get('https://api.ipify.org')
            ip_address = response.text
            
            st.sidebar.markdown("---")
            st.sidebar.error(f"🔧 서버 현재 IP: {ip_address}")
            st.sidebar.info("이 IP를 ODsay 콘솔에 등록하세요!")
        except:
            st.sidebar.warning("IP 확인 실패")

# main 함수 안, 사이드바 코드 쪽에 호출
# ...
    with st.sidebar:
        # ... (기존 코드) ...
        
        # [임시 추가] IP 확인용
        show_current_ip()

    # 분석 실행 (메인 화면 로딩)
    if btn_run:
        st.session_state['analyzed'] = False
        placeholder = st.empty()
        
        with placeholder.container():
            with st.spinner("📡 위성 지형 및 교통 데이터를 정밀 분석 중입니다..."):
                result = run_analysis(s, e, my_car, res)
                if result:
                    st.session_state.update(result)
                    st.session_state['analyzed'] = True
                else:
                    st.error("경로를 찾을 수 없습니다. 주소를 확인해주세요.")
        
        if st.session_state['analyzed']:
            placeholder.empty()

    # 결과 렌더링
    if st.session_state['analyzed']:
        w = st.session_state['weather']
        st.subheader("🌦️ 실시간 주행 환경")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("기온", f"{w['temp']}°C")
        c2.metric("습도", f"{w['humidity']}%")
        c3.metric("날씨", w['condition'])
        
        w_msg = "양호"
        if w['is_wet']: w_msg = "비/눈 (저항↑)"
        elif w['temp'] > 25: w_msg = "고온 (에어컨)"
        elif w['temp'] < 10: w_msg = "저온 (히터)"
        c4.metric("환경 부하", w_msg)
        
        st.divider()

        # 탭 렌더링
        tab1, tab2, tab3 = st.tabs(["📋 종합 운전 리포트", "📊 상세 분석 (3D)", "📝 연구 모델 명세"])
        
        with tab1:
            render_tab_compare(st.session_state['car_data'], st.session_state['pub_data'], st.session_state['weather'])
        with tab2:
            render_tab_terrain(st.session_state['car_data'])
        with tab3:
            render_tab_info()

if __name__ == "__main__":
    main()