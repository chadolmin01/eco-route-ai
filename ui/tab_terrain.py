import streamlit as st
from modules.visualizer import create_interactive_graph

def render_tab_terrain(car_data):
    st.markdown("### 🏔️ 4차원 도로 지형 상세 분석")
    st.caption("구글 위성 고도 데이터와 실시간 교통 흐름을 100m 단위로 시각화했습니다.")
    
    if car_data and car_data.get('collected'):
        fig_3d = create_interactive_graph(car_data['collected'])
        st.plotly_chart(fig_3d, use_container_width=True)
        st.info("💡 **Tip:** 그래프 위에 마우스를 올리면 구간별 상세 정보(경사도, 속도)가 보입니다.")
    else:
        st.warning("분석된 데이터가 없습니다.")