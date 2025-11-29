import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.lines import Line2D
import numpy as np
import os
import platform

# 웹 시각화를 위한 Plotly 라이브러리
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def configure_font():
    """OS별 한글 폰트 자동 설정"""
    system_name = platform.system()
    if system_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='NanumGothic')
    plt.rc('axes', unicode_minus=False)

def draw_comparison_graph(all_routes_data, origin, dest, filename):
    """
    [이미지 저장용] Matplotlib을 사용하여 정적 이미지 파일 생성
    """
    num_routes = len(all_routes_data)
    if num_routes == 0: return

    configure_font()

    fig, axes = plt.subplots(num_routes, 1, figsize=(12, 5 * num_routes), squeeze=False)
    axes = axes.flatten()

    color_list = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
    cmap = ListedColormap(color_list)
    norm = BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)
    
    legend_elements = [
        Line2D([0], [0], color=color_list[0], lw=4, label='원활'),
        Line2D([0], [0], color=color_list[1], lw=4, label='서행'),
        Line2D([0], [0], color=color_list[2], lw=4, label='지체'),
        Line2D([0], [0], color=color_list[3], lw=4, label='정체'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='black', markersize=5, label='데이터 포인트(100m)')
    ]

    for i, ax in enumerate(axes):
        route_data = all_routes_data[i]
        segments = route_data['segments']
        label = route_data['label']
        stats = route_data['stats']
        route_id = route_data.get('id', i+1)

        lines, colors, all_dists, all_alts = [], [], [], []
        current_dist = 0.0
        
        for seg in segments:
            dist_km = seg['distance_m'] / 1000
            start_d, end_d = current_dist, current_dist + dist_km
            current_dist = end_d
            
            lines.append([(start_d, seg.get('start_alt', 0)), (end_d, seg.get('end_alt', 0))])
            congestion = seg.get('congestion', 1)
            colors.append(congestion if congestion in [1,2,3,4] else 1)
            
            all_dists.extend([start_d, end_d])
            all_alts.extend([seg.get('start_alt', 0), seg.get('end_alt', 0)])

        lc = LineCollection(lines, cmap=cmap, norm=norm)
        lc.set_array(np.array(colors))
        lc.set_linewidth(3)
        ax.add_collection(lc)
        ax.scatter(all_dists, all_alts, s=5, color='black', zorder=5, alpha=0.6)

        # 세로축 비율 조정 (납작하게)
        ax.set_aspect(0.015, adjustable='box')
        
        if all_dists:
            ax.set_xlim(min(all_dists), max(all_dists))
            ax.set_ylim(min(all_alts) - 30, max(all_alts) + 50)
            ax.fill_between(all_dists[::2], min(all_alts)-30, all_alts[::2], color='gray', alpha=0.1)
        
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_ylabel("해발 고도 (m)", fontsize=10)
        
        if i == num_routes - 1:
             ax.set_xlabel("주행 거리 (km)", fontsize=12)

        if i == 0:
            ax.legend(handles=legend_elements, loc='lower left', fontsize=9, frameon=True)

        # 기상 정보 표시
        weather_text = ""
        weather_pct = stats.get('weather_pct', 0.0)
        if abs(weather_pct) > 0.1:
            pm = "+" if weather_pct > 0 else ""
            weather_text = f"  |  🌤️기상영향: {pm}{weather_pct:.1f}%"

        title_text = (f"[경로 {route_id}: {label}]  "
                      f"거리: {stats['dist']:.1f}km  |  "
                      f"시간: {stats['time']:.0f}분  |  "
                      f"CO2: {stats['co2']:.0f}g"
                      f"{weather_text}")
        
        ax.set_title(title_text, fontsize=12, fontweight='bold', pad=10)

    fig.suptitle(f"승용차 경로별 탄소 배출량 비교 분석\n({origin} -> {dest})", fontsize=14, fontweight='bold', y=0.99)
    plt.tight_layout()
    plt.subplots_adjust(top=0.92)

    ensure_dir = os.path.dirname(filename)
    if ensure_dir and not os.path.exists(ensure_dir):
        os.makedirs(ensure_dir)
        
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"   🖼️ 통합 비교 그래프 저장 완료: {filename}")

def create_interactive_graph(all_routes_data):
    """
    [웹 시연용] Plotly를 이용한 대화형(Interactive) 그래프 생성
    - 줌(Zoom), 팬(Pan), 마우스 오버(Hover) 기능 지원
    """
    num_routes = len(all_routes_data)
    if num_routes == 0: return None

    # 1. 서브플롯 생성 (세로 배치)
    titles = []
    for d in all_routes_data:
        stats = d['stats']
        w_pct = stats.get('weather_pct', 0)
        w_txt = f"(기상 {w_pct:+.1f}%)" if abs(w_pct) > 0.1 else ""
        titles.append(f"<b>[{d['label']}]</b> 거리: {stats['dist']:.1f}km, CO2: {stats['co2']:.0f}g {w_txt}")

    fig = make_subplots(
        rows=num_routes, cols=1,
        subplot_titles=titles,
        vertical_spacing=0.12
    )

    # 색상/라벨 매핑
    color_map = {1: '#2ecc71', 2: '#f1c40f', 3: '#e67e22', 4: '#e74c3c'}
    label_map = {1: '원활', 2: '서행', 3: '지체', 4: '정체'}

    for i, route_data in enumerate(all_routes_data):
        segments = route_data['segments']
        
        dists = []
        alts = []
        colors = []
        hover_texts = []
        
        current_dist = 0
        for seg in segments:
            dist_km = seg['distance_m'] / 1000
            
            dists.append(current_dist)
            alts.append(seg.get('start_alt', 0))
            
            cong = seg.get('congestion', 1)
            if cong not in color_map: cong = 1
            colors.append(color_map[cong])
            
            # 툴팁 내용 (HTML 태그 사용 가능)
            txt = (f"<b>{seg['name']}</b><br>"
                   f"속도: {seg['speed_kph']}km/h ({label_map[cong]})<br>"
                   f"경사: {seg['grade_pct']:.1f}%<br>"
                   f"배출: {seg.get('step_emission', 0):.1f}g")
            hover_texts.append(txt)
            
            current_dist += dist_km

        # 1. 회색 실선 (전체 경로 연결)
        fig.add_trace(
            go.Scatter(
                x=dists, y=alts,
                mode='lines',
                line=dict(color='gray', width=1),
                hoverinfo='skip',
                showlegend=False
            ),
            row=i+1, col=1
        )

        # 2. 컬러 점 (구간별 상태 표시)
        fig.add_trace(
            go.Scatter(
                x=dists, y=alts,
                mode='markers',
                marker=dict(color=colors, size=6),
                text=hover_texts,
                hoverinfo='text+y+x',
                name=f"{route_data['label']}",
                showlegend=False
            ),
            row=i+1, col=1
        )

        # Y축 설정
        fig.update_yaxes(title_text="해발 고도(m)", row=i+1, col=1)

    # 3. 레이아웃 설정
    fig.update_layout(
        height=350 * num_routes, # 그래프 높이 자동 조절
        title_text="<b>🚗 경로별 지형 및 교통 혼잡도 상세 분석</b> (마우스를 올려보세요!)",
        template="plotly_white",
        hovermode="closest"
    )
    
    fig.update_xaxes(title_text="주행 거리 (km)", row=num_routes, col=1)

    return fig