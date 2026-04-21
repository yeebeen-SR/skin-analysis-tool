import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("촬영된 사진을 정량 분석하여 변화를 기록합니다. 첫 번째 사진부터 순서대로 업로드해 주세요.")

# 2. 지표 가이드 (리포트에만 활용)
METRIC_GUIDE = {
    "피부 밝기 (Brightness)": "↑ 높을수록 안색이 환함",
    "피부결 (Smoothness)": "↑ 높을수록 표면이 매끄러움",
    "홍조 (Redness)": "↓ 낮을수록 붉은기 진정",
    "여드름/트러블 (Acne)": "↓ 낮을수록 피부 깨끗함",
    "모공/요철 (Pores)": "↓ 낮을수록 모공 촘촘함",
    "색소침착 (Pigmentation)": "↓ 낮을수록 기미/잡티 개선"
}
POSITIVE_METRICS = ["피부 밝기 (Brightness)", "피부결 (Smoothness)"]
ALL_ITEMS = list(METRIC_GUIDE.keys())

uploaded_files = st.file_uploader("사진 업로드", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_logic(image):
    img = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    l, a, _ = cv2.split(lab)
    
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
    # [섹션 1] 사진 기록 (상단 배치)
    st.subheader("📸 사진 기록")
    img_cols = st.columns(len(uploaded_files))
    for i, file in enumerate(uploaded_files):
        label = "Before" if i == 0 else f"After {i}"
        img = Image.open(file)
        analysis = analyze_logic(img)
        analysis["회차"] = label
        results.append(analysis)
        with img_cols[i]:
            st.image(img, caption=label, use_container_width=True)

    df = pd.DataFrame(results)

    # [섹션 2] 지표별 변화 추이 (이전 만족하셨던 항목별 막대 그래프 형태)
    st.divider()
    st.subheader("📊 항목별 상세 변화")
    
    item_cols = st.columns(2)
    for idx, item in enumerate(ALL_ITEMS):
        with item_cols[idx % 2]:
            # 막대 그래프로 변경 및 수치 표기
            fig = px.bar(df, x="회차", y=item, color="회차", text=item, title=item)
            fig.update_layout(xaxis_title="", yaxis_title="점수", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # [섹션 3] 최종 개선 성과 리포트 (전체 항목 유지)
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
                # pt 제거, 수치만 표시
                st.metric(label=f"{item}", value=f"{val_now}", delta=f"{diff:.1f}% 개선")
                st.caption(METRIC_GUIDE[item]) # 가이드 문구 유지

        # 베스트 시점 판독 로직
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
    st.info("사진을 업로드하면 상세 리포트가 생성됩니다.")
