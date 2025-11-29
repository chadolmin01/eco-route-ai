import streamlit as st
import pandas as pd

def render_tab_info():
    st.markdown("### 🔬 VSP 기반 탄소 배출량 산출 모델")
    st.info("본 시스템은 **Jimenez-Palacios (1999)**의 VSP 모델을 한국형 도로 환경에 맞게 개량하였습니다.")
    st.latex(r"""VSP = v \cdot [1.1 \cdot a + 9.81 \cdot \sin(\theta) + C_r] + (C_d \cdot K_{air}) \cdot v^3 + P_{aux}""")
    
    st.markdown("#### 1. 기상 요인 보정 (Weather Correction)")
    weather_data = [
        {"요인": "공기 밀도", "변수": "$K_{air}$", "내용": "기온 저하 시 공기 밀도 증가 → 저항 증가"},
        {"요인": "구름 저항", "변수": "$C_r$", "내용": "젖은 노면 마찰력 증가 (+20%)"},
        {"요인": "공조 부하", "변수": "$P_{aux}$", "내용": "여름철 에어컨(잠열 포함), 겨울철 히터 부하"}
    ]
    st.table(pd.DataFrame(weather_data))
    
    st.markdown("#### 2. 데이터 전처리 (Preprocessing)")
    algo_data = [
        {"기술": "리샘플링", "내용": "긴 도로를 100m 단위 마이크로 트립으로 분할"},
        {"기술": "이상치 제거", "내용": "최대 경사도 ±10% (고속도로 ±5%) 제한"},
        {"기술": "평탄화", "내용": "이동 평균 필터(Window=10) 및 굴곡도 기반 터널 보정"}
    ]
    st.table(pd.DataFrame(algo_data))