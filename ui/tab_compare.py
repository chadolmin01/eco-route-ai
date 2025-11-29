import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def render_tab_compare(car_data, pub_data, weather_info):
    """
    [최종] 주행 시뮬레이션(게이지), 위험 리포트, 비교 분석을 통합한 대시보드
    """
    
    # 1. 데이터 준비
    # 최적 경로(Baseline) 데이터 추출
    best_car_summary = min(car_data['summary'], key=lambda x: x['CO2'])
    target_emission = best_car_summary['CO2'] # 예측된 총 배출량 (목표치)
    total_distance = best_car_summary['Dist'] # 총 거리
    
    # 이벤트 데이터 (리포트용)
    events = car_data.get('events', {'uphill': 0, 'congestion': 0, 'weather_bad': 0})

    # ============================================================
    # [Section 1] 실시간 주행 시뮬레이션 (Interactive Simulation)
    # ============================================================
    st.markdown("### 🚘 실시간 탄소 배출 모니터링")
    st.caption("슬라이더를 움직여 주행 상황을 가정하고, 운전 습관에 따른 배출량 변화를 확인해보세요.")

    # 레이아웃 분할: 컨트롤 패널(좌) vs 게이지 차트(우)
    col_ctrl, col_gauge = st.columns([1, 1.5])

    with col_ctrl:
        st.write("") # 여백
        # 1. 거리 조절 슬라이더
        current_dist = st.slider(
            "📍 현재 주행 거리 (km)", 
            min_value=0.0, 
            max_value=total_distance, 
            value=total_distance * 0.0, # 0에서 시작
            step=0.1
        )
        
        st.write("")
        # 2. 운전 스타일 선택 (토글 효과)
        driving_style = st.radio(
            "⚙️ 운전 스타일 가정", 
            ["🌱 연비 운전 (Eco)", "🚗 일반 주행", "🏎️ 급가속/과속 (Sport)"], 
            index=1,
            help="실제 주행 시 운전 습관에 따라 탄소 배출량이 달라집니다."
        )

        # 계산 로직
        progress_ratio = current_dist / total_distance if total_distance > 0 else 0
        base_current = target_emission * progress_ratio
        
        if "Eco" in driving_style:
            current_emission = base_current * 0.85 # 15% 절감 효과
            msg = "🌿 훌륭합니다! 탄소를 절약하고 있습니다."
            msg_color = "green"
        elif "Sport" in driving_style:
            current_emission = base_current * 1.3 # 30% 증가 패널티
            msg = "⚠️ 경고: 급가속으로 배출량이 급증했습니다!"
            msg_color = "red"
        else:
            current_emission = base_current
            msg = "일반적인 주행 상태입니다."
            msg_color = "blue"
            
        # 상태 메시지 박스
        st.markdown(f"""
        <div style="margin-top:15px; padding:10px; border-radius:5px; background-color:#f8f9fa; border-left:4px solid {msg_color};">
            <small style="color:#666;">주행 상태</small><br>
            <b style="color:{msg_color};">{msg}</b>
        </div>
        """, unsafe_allow_html=True)

    with col_gauge:
        # 3. 게이지 차트 (요청하신 디자인 유지)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = current_emission,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "<b>누적 탄소 배출량 (g)</b>", 'font': {'size': 18}},
            # Delta: 예측치(기준) 대비 현재 상태 비교
            delta = {'reference': target_emission * progress_ratio, 'increasing': {'color': "red"}, 'decreasing': {'color': "green"}},
            gauge = {
                'axis': {'range': [0, target_emission * 1.4], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#3b82f6"}, # 파란색 바
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "#eee",
                'steps': [
                    {'range': [0, target_emission], 'color': "#e8f5e9"}, # 안전 구간 (초록)
                    {'range': [target_emission, target_emission * 1.4], 'color': "#ffcdd2"} # 초과 구간 (빨강)
                ],
                'threshold': { # 목표치 라인
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target_emission
                }
            }
        ))
        # 여백 조정으로 컴팩트하게 표시
        fig_gauge.update_layout(height=300, margin=dict(l=30, r=30, t=30, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    st.divider()

    # ============================================================
    # [Section 2] 종합 분석 (리포트 & 비교 차트)
    # ============================================================
    col_report, col_chart = st.columns([1, 1.2])

    with col_report:
        st.markdown("#### 🚦 주행 위험 요소 리포트")
        
        # 데이터 가공
        uphill_n = events.get('uphill', 0)
        uphill_txt = f"{uphill_n}개 급경사 구간" if uphill_n > 0 else "평탄함 (양호)"
        uphill_stat = "bad" if uphill_n > 3 else "good"
        
        cong_n = events.get('congestion', 0)
        cong_txt = f"{cong_n}개 정체 구간" if cong_n > 0 else "원활함 (양호)"
        cong_stat = "bad" if cong_n > 5 else "good"
        
        weather_txt = weather_info['condition']
        if weather_info['is_wet']: weather_txt += " (빗길 저항↑)"
        
        # HTML 리스트 디자인
        st.markdown(f"""
        <div class="report-list">
            <div class="report-item">
                <div class="item-icon">⛰️</div>
                <div class="item-text">지형 요인</div>
                <div class="item-value {'item-bad' if uphill_stat=='bad' else 'item-good'}">{uphill_txt}</div>
            </div>
            <div class="report-item">
                <div class="item-icon">🐢</div>
                <div class="item-text">교통 요인</div>
                <div class="item-value {'item-bad' if cong_stat=='bad' else 'item-good'}">{cong_txt}</div>
            </div>
            <div class="report-item">
                <div class="item-icon">🌦️</div>
                <div class="item-text">기상 요인</div>
                <div class="item-value" style="color:#555;">{weather_txt}</div>
            </div>
            <div class="report-item" style="background-color:#f8f9fa;">
                <div class="item-icon">🏁</div>
                <div class="item-text"><b>총 예측 배출량</b></div>
                <div class="item-value" style="font-size:18px; color:#e74c3c;">{target_emission:.0f} g</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        st.markdown("#### 📊 비교 분석")
        # 탭으로 공간 활용 최적화
        sub_tab1, sub_tab2 = st.tabs(["경로별 비교", "대중교통 비교"])
        
        with sub_tab1:
            # 승용차 경로끼리 비교 (막대 차트)
            df_car = pd.DataFrame(car_data['summary'])
            fig_car = px.bar(df_car, x='Route', y='CO2', color='Route', text_auto='.0f',
                             title=None)
            fig_car.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
            st.plotly_chart(fig_car, use_container_width=True)
            
        with sub_tab2:
            if pub_data:
                # 최적 승용차 vs 최적 대중교통
                best_pub = min(pub_data, key=lambda x: x['CO2'])
                comp_data = [
                    {"수단": "내 차 (Best)", "배출량": target_emission, "Color": "Car"},
                    {"수단": f"대중교통 ({best_pub['Route']})", "배출량": best_pub['CO2'], "Color": "Pub"}
                ]
                fig_pub = px.bar(comp_data, x='배출량', y='수단', orientation='h', text_auto='.0f',
                                 color='Color', color_discrete_map={'Car': '#ef5350', 'Pub': '#66bb6a'})
                fig_pub.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
                st.plotly_chart(fig_pub, use_container_width=True)
            else:
                st.info("대중교통 경로가 없습니다.")