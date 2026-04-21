import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정 및 제목 (자극적인 워딩 지양)
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("촬영된 사진을 정량 분석하여 세션별 변화를 기록합니다. **첫 번째 사진은 반드시 관리 전(Before) 사진**이어야 합니다.")

# 2. 지표 정의 및 방향성 도움말
METRIC_GUIDE = {
    "피부 밝기 (Brightness)": "↑ 높을수록 안색이 환함",
    "피부결 (Smoothness)": "↑ 높을수록 표면이 매끄러움",
    "홍조 (Redness)": "↓ 낮을수록 붉은기 진정",
    "여드름/트러블 (Acne)": "↓ 낮을수록 피부 깨끗함",
    "모공/요철 (Pores)": "↓ 낮을수록 모공 촘촘함",
    "색소침착 (Pigmentation)": "↓ 낮을수록 기미/잡티 개선"
}
POSITIVE_METRICS = ["피부 밝기 (Brightness)", "피부결 (Smoothness)"]
NEGATIVE_METRICS = ["홍조 (Redness)", "여드름/트러블 (Acne)", "모공/요철 (Pores)", "색소침착 (Pigmentation)"]
ALL_ITEMS = list(METRIC_GUIDE.keys())

# 파일 업로드
uploaded_files = st.file_uploader("사진을 선택하세요 (Before 사진부터 순서대로)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_logic(image):
    img = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # 이미지 분석 알고리즘 (0~100 스케일 기반 수치화)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    
    brightness = np.mean(l) # 밝기
    redness = np.mean(a) # 홍조
    
    # 여드름/트러블 (붉은색 국소 포인트 추출)
    red_mask = cv2.inRange(a, 145, 255)
    acne_score = (np.sum(red_mask > 0) / red_mask.size) * 1000
    
    # 모공/요철
    edges = cv2.Canny(gray, 50, 150)
    pore_score = (np.sum(edges > 0) / edges.size) * 100
    
    # 피부결 (표면 대비 표준편차 활용)
    grain = np.std(gray)
    smoothness = 100 - grain
    
    # 색소침착 (어두운 영역 밀도)
    pigment_score = (np.sum(gray < 80) / gray.size) * 100

    return {
        "피부 밝기 (Brightness)": round(brightness, 1),
        "피부결 (Smoothness)": round(smoothness, 1),
        "홍조 (Redness)": round(redness, 1),
        "여드름/트러블 (Acne)": round(acne_score, 1),
        "모공/요철 (Pores)": round(pore_score, 1),
        "색소침착 (Pigmentation)": round(pigment_score, 1)
    }

if uploaded_files:
    results = []
    # 사진 레이아웃 상단 배치
    st.subheader("📸 세션별 사진 기록")
    img_cols = st.columns(len(uploaded_files))
    
    for i, file in enumerate(uploaded_files):
        label = "Before" if i == 0 else f"Session {i}"
        img = Image.open(file)
        analysis = analyze_logic(img)
        analysis["세션"] = label
        results.append(analysis)
        with img_cols[i]:
            st.image(img, caption=label, use_container_width=True)

    df = pd.DataFrame(results)
    
    # 3. 지표별 상세 변화 (그래프 수치 표기)
    st.divider()
    st.subheader("📊 항목별 상세 수치 변화")
    st.caption("그래프 위의 숫자는 해당 세션에서 측정된 피부 점수(pt)입니다.")
    
    # 항목별 쪼개서 보기 (가시성 확보)
    item_cols = st.columns(2)
    for idx, item in enumerate(ALL_ITEMS):
        with item_cols[idx % 2]:
            # markers=True와 text 매개변수로 수치 노출
            fig = px.line(df, x="세션", y=item, 
                          title=f"{item} ({METRIC_GUIDE[item]})", 
                          markers=True, text=item)
            fig.update_traces(textposition="top center") # 수치를 점 위에 표시
            # 변화폭이 잘 보이도록 Y축 범위 자동 최적화
            fig.update_yaxes(range=[df[item].min()*0.8, df[item].max()*1.2])
            st.plotly_chart(fig, use_container_width=True)

    # 4. 최종 성과 요약 및 최고의 세션 판독
    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 개선 성과 리포트 (전 기간 누적)")
        
        last_idx = len(results) - 1 # 마지막(최신) 세션
        summary_cols = st.columns(len(ALL_ITEMS))
        
        for i, item in enumerate(ALL_ITEMS):
            val_now = df.loc[last_idx, item]
            val_before = df.loc[0, item]
            
            # 개선율 계산 (Before 기준)
            if item in POSITIVE_METRICS:
                diff = ((val_now - val_before) / val_before) * 100 if val_before != 0 else 0
            else:
                diff = ((val_before - val_now) / val_before) * 100 if val_before != 0 else 0
            
            with summary_cols[i]:
                st.metric(label=f"{item}", value=f"{val_now} pt", delta=f"{diff:.1f}% 개선")
                st.caption(f"기준: {METRIC_GUIDE[item]}")

        # 통합 개선도 기반 최적 세션 판독
        df_impro = df.copy()
        best_idx = 0
        max_total_impro = -9999
        for idx in range(1, len(df)):
            total_impro = 0
            for item in ALL_ITEMS:
                if item in POSITIVE_METRICS: 
                    total_impro += (df.loc[idx, item] - df.loc[0, item])
                else: 
                    total_impro += (df.loc[0, item] - df.loc[idx, item])
            if total_impro > max_total_impro:
                max_total_impro = total_impro
                best_idx = idx
        
        st.success(f"💡 분석 결과, 첫 방문(Before) 대비 전체 지표가 가장 종합적으로 개선된 회차는 **[{df.loc[best_idx, '세션']}]** 입니다.")

else:
    st.info("비포 사진부터 순서대로 업로드하면 데이터 분석이 시작됩니다.")
