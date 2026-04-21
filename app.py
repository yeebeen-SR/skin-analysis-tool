import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 페이지 설정
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("촬영된 사진을 정량 분석하여 변화를 기록합니다. 첫 번째 사진부터 순서대로 업로드해 주세요.")

# 지표 정의
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

uploaded_files = st.file_uploader("사진 업로드", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_logic(image):
    img = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    
    brightness = np.mean(l)
    redness = np.mean(a)
    red_mask = cv2.inRange(a, 145, 255)
    acne_score = (np.sum(red_mask > 0) / red_mask.size) * 1000
    edges = cv2.Canny(gray, 50, 150)
    pore_score = (np.sum(edges > 0) / edges.size) * 100
    grain = np.std(gray)
    smoothness = 100 - grain
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
    st.subheader("📸 사진 기록")
    img_cols = st.columns(len(uploaded_files))
    
    for i, file in enumerate(uploaded_files):
        label = "Before" if i == 0 else f"After {i}"
        img = Image.open(file)
        analysis = analyze_logic(img)
        analysis["회차"] = label # '세션' 대신 '회차' 사용 혹은 공백 가능
        results.append(analysis)
        with img_cols[i]:
            st.image(img, caption=label, use_container_width=True)

    df = pd.DataFrame(results)
    
    # 1. 통합 항목별 변화 추이 (그림 그래프 유지)
    st.divider()
    st.subheader("📊 항목별 변화 추이")
    
    # 통합 라인 차트 (세션 워딩 제거를 위해 x축 라벨 공백 처리)
    fig = px.line(df, x="회차", y=ALL_ITEMS, markers=True, text_auto=True)
    fig.update_layout(xaxis_title="", yaxis_title="상대 점수")
    st.plotly_chart(fig, use_container_width=True)

    # 2. 최종 개선 성과 리포트
    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 개선 성과 리포트")
        
        last_idx = len(results) - 1
        summary_cols = st.columns(len(ALL_ITEMS))
        
        for i, item in enumerate(ALL_ITEMS):
            val_now = df.loc[last_idx, item]
            val_before = df.loc[0, item]
            
            if item in POSITIVE_METRICS:
                diff = ((val_now - val_before) / val_before) * 100 if val_before != 0 else 0
            else:
                diff = ((val_before - val_now) / val_before) * 100 if val_before != 0 else 0
            
            with summary_cols[i]:
                # pt 워딩 제거, 수치만 표시
                st.metric(label=f"{item}", value=f"{val_now}", delta=f"{diff:.1f}% 개선")
                st.caption(METRIC_GUIDE[item]) # 여기에만 가이드 표시

        # 최적 회차 판독
        best_idx = 0
        max_total_impro = -9999
        for idx in range(1, len(df)):
            total_impro = 0
            for item in ALL_ITEMS:
                if item in POSITIVE_METRICS: total_impro += (df.loc[idx, item] - df.loc[0, item])
                else: total_impro += (df.loc[0, item] - df.loc[idx, item])
            if total_impro > max_total_impro:
                max_total_impro = total_impro
                best_idx = idx
        
        st.success(f"💡 분석 결과, 첫 방문 대비 가장 종합적으로 개선된 시점은 **[{df.loc[best_idx, '회차']}]** 입니다.")

else:
    st.info("사진을 업로드하면 분석 리포트가 생성됩니다.")
