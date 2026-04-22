import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("정량적 분석 데이터를 기반으로 작성된 리포트입니다. 초기 대비 최종 변화를 확인하세요.")

METRIC_GUIDE = {
    "피부 밝기 (Brightness)": "↑ 높을수록 환함",
    "피부결 (Smoothness)": "↑ 높을수록 표면이 매끄러움",
    "홍조 (Redness)": "↓ 낮을수록 붉은기 진정",
    "여드름/트러블 (Acne)": "↓ 낮을수록 피부 깨끗함",
    "모공/요철 (Pores)": "↓ 낮을수록 모공 촘촘함",
    "색소침착 (Pigmentation)": "↓ 낮을수록 개선"
}
POSITIVE_METRICS = ["피부 밝기 (Brightness)", "피부결 (Smoothness)"]
ALL_ITEMS = list(METRIC_GUIDE.keys())

uploaded_files = st.file_uploader("사진을 업로드하세요", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

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
        analysis["회차"] = label
        results.append(analysis)
        with img_cols[i]:
            st.image(img, caption=label, use_container_width=True)
    
    df = pd.DataFrame(results)
    
    st.divider()
    st.subheader("📊 종합 지표 변화")
    fig_main = px.bar(df, x="회차", y=ALL_ITEMS, barmode="group", text_auto=True)
    fig_main.update_layout(xaxis_title="", yaxis_title="상대 점수")
    st.plotly_chart(fig_main, use_container_width=True)

    st.divider()
    st.subheader("📈 항목별 상세 추이")
    st.info("💡 수치 가이드: [밝기/결]은 높을수록 우수하며, [홍조/트러블/모공/색소]는 낮을수록 안정적인 상태를 의미합니다.")
    
    item_cols = st.columns(2)
    for idx, item in enumerate(ALL_ITEMS):
        with item_cols[idx % 2]:
            fig_item = px.line(df, x="회차", y=item, markers=True, text=item, title=f"[{item}] 변화")
            fig_item.update_traces(textposition="top center")
            fig_item.update_layout(xaxis_title="", yaxis_title="점수")
            st.plotly_chart(fig_item, use_container_width=True)

    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 분석 데이터 요약")
        
        last_idx = len(results) - 1
        summary_cols = st.columns(len(ALL_ITEMS))
        
        improved_list = []
        for i, item in enumerate(ALL_ITEMS):
            val_now = df.loc[last_idx, item]
            val_before = df.loc[0, item]
            if item in POSITIVE_METRICS:
                diff = ((val_now - val_before) / val_before) * 100 if val_before != 0 else 0
            else:
                diff = ((val_before - val_now) / val_before) * 100 if val_before != 0 else 0
            
            improved_list.append(diff)
            with summary_cols[i]:
                st.metric(label=item, value=f"{val_now}", delta=f"{diff:.1f}%")
                st.caption(METRIC_GUIDE[item])

        st.divider()
        
        col_res1, col_res2 = st.columns([1, 1])
        
        with col_res1:
            st.markdown("### 📝 전문 데이터 분석")
            # 1. 최종 개선율 (전체 평균)
            avg_imp = sum(improved_list) / len(improved_list)
            status_text = "개선" if avg_imp >= 0 else "하락"
            st.write(f"✅ **초기 대비 최종 개선율:** 약 **{avg_imp:.1f}% {status_text}**")
            
            # 2. 베스트 시점 판독
            impro_totals = []
            for idx in range(len(df)):
                total = 0
                for item in ALL_ITEMS:
                    v0, v_curr = df.loc[0, item], df.loc[idx, item]
                    if item in POSITIVE_METRICS: total += (v_curr - v0)
                    else: total += (v0 - v_curr)
                impro_totals.append(total)
            best_idx = np.argmax(impro_totals)
            best_label = df.loc[best_idx, "회차"]
            st.success(f"🏆 분석 결과, 피부 컨디션이 가장 극대화된 시점은 **[{best_label}]** 입니다.")

            # 3. 개선 지표 (담백하게 변경)
            top_idx = np.argmax(improved_list)
            st.write(f"- **가장 높은 개선 지표:** {ALL_ITEMS[top_idx]}")

        with col_res2:
            st.markdown("### 📍 전문가 관리 가이드")
            # 주의 항목
            worst_idx = np.argmin(improved_list)
            if improved_list[worst_idx] < -2:
                st.warning(f"⚠️ **주의 필요 지표:** {ALL_ITEMS[worst_idx]}")
            
            # 홍조 기반 시술 가이드
            if df.loc[last_idx, "홍조 (Redness)"] > df.loc[0, "홍조 (Redness)"] * 1.05:
                st.info("🛋️ **진정 회복기:** 일시적인 홍조 증가가 확인됩니다. 고기능성 성분 사용을 중단하고 무자극 진정/재생 관리에 집중하세요.")
            else:
                st.info("✨ **장벽 안정기:** 피부가 안정적인 궤도에 올랐습니다. 현재 루틴을 유지하며 기초 체력을 길러주세요.")
            
            st.warning("🧴 **필수 사항:** 개선된 상태를 유지하기 위해 자외선 차단제는 매일 꼼꼼히 사용해 주시기 바랍니다.")

else:
    st.info("사진을 업로드하면 정량적 분석 리포트가 생성됩니다.")
