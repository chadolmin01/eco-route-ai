import streamlit as st

def apply_styles():
    st.set_page_config(
        page_title="Eco-Route AI",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; }
        
        /* TMAP 스타일 원형 점수판 */
        .score-container {
            display: flex; justify-content: center; align-items: center; margin: 20px 0;
        }
        .score-circle {
            width: 180px; height: 180px;
            border-radius: 50%;
            background: white;
            border: 8px solid #3b82f6;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .score-val { font-size: 48px; font-weight: 800; color: #333; line-height: 1.0; }
        .score-label { font-size: 16px; color: #666; margin-top: 5px; }
        
        /* 리포트 리스트 스타일 */
        .report-list {
            background-color: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border: 1px solid #f0f0f0;
        }
        .report-item {
            display: flex; align-items: center; justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .report-item:last-child { border-bottom: none; }
        .item-icon { font-size: 20px; margin-right: 15px; width: 30px; text-align: center; }
        .item-text { flex-grow: 1; font-size: 16px; color: #333; font-weight: 500; }
        .item-value { font-weight: bold; color: #3b82f6; }
        
        .item-good { color: #2ecc71; }
        .item-bad { color: #e74c3c; }
        
        /* 환경 리포트 카드 */
        .env-card {
            background-color: #e8f5e9;
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            border: 1px solid #c8e6c9;
        }
        
        /* 탭 스타일 */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            height: 45px; background-color: #fff; border-radius: 5px; border: 1px solid #ddd;
        }
        .stTabs [aria-selected="true"] {
            background-color: #e8f5e9; color: #2e7d32; border: 1px solid #2e7d32; font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)