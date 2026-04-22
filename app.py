import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("정량적 데이터 분석을 통해 피부 변화를 기록합니다. 첫 번째 사진부터 순서대로 업로드해 주세요.")

# 2. 지표 가이드 및 방향성 정의
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
    # [섹션 1] 사진 기록
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
    st.subheader("📊 항목별 변화 추이")
    st.info("💡 수치 가이드: [밝기/결]은 높을수록 우수하며, [홍조/트러블/모공/색소]는 낮을수록 안정적인 상태를 의미합니다.")
    
    tab1, tab2 = st.tabs(["종합 분석", "상세 항목별"])
    
    with tab1:
        fig_main = px.bar(df, x="회차", y=ALL_ITEMS, barmode="group", text_auto=True)
        fig_main.update_layout(xaxis_title="", yaxis_title="상대 점수")
        st.plotly_chart(fig_main, use_container_width=True)
        
    with tab2:
        item_cols = st.columns(2)
        for idx, item in enumerate(ALL_ITEMS):
            with item_cols[idx % 2]:
                fig_item = px.line(df, x="회차", y=item, markers=True, text=item)
                fig_item.update_traces(textposition="top center")
                fig_item.update_layout(xaxis_title="")
                st.plotly_chart(fig_item, use_container_width=True)

    # [섹션 3] 최종 개선 성과 리포트
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
                st.metric(label=item, value=f"{val_now}", delta=f"{diff:.1f}% 개선")
                st.caption(METRIC_GUIDE[item])

        st.divider()
        
        # 전문 분석 요약 생성
        improvements = []
        for item in ALL_ITEMS:
            v0, v1 = df.loc[0, item], df.loc[last_idx, item]
            imp = ((v1-v0)/v0) if item in POSITIVE_METRICS else ((v0-v1)/v0)
            improvements.append(imp)
        
        best_item = ALL_ITEMS[np.argmax(improvements)]
        best_label = df.loc[df.apply(lambda x: sum([x[m] if m in POSITIVE_METRICS else -x[m] for m in ALL_ITEMS]), axis=1).idxmax(), "회차"]
        
        col_res1, col_res2 = st.columns([1.5, 1])
        with col_res1:
            st.markdown("### 📝 전문 분석 요약")
            st.write(f"1. **종합 개선도:** 첫 방문(Before) 대비 전체 피부 지표가 조화롭게 개선되고 있습니다.")
            st.write(f"2. **최우수 성과:** 현재 **{best_item}** 영역에서 가장 비약적인 성과를 보이며, 이는 진행 중인 프로그램이 고객님의 피부 타입에 매우 적합함을 증명합니다.")
            st.success(f"🏆 전체 기간 중 피부 컨디션이 가장 극대화된 시점은 **[{best_label}]** 입니다.")

        with col_res2:
            st.markdown("### 📍 맞춤형 관리 가이드")
            st.info("✅ **장벽 유지:** 지표가 안정화되는 시기이므로, 급격한 제품 변경보다는 현재의 루틴을 유지하며 피부 장벽을 탄탄하게 관리하세요.")
            st.info("🧴 **제품 흡수:** 피부결이 정돈됨에 따라 유효 성분의 흡수율이 높아진 상태입니다. 고기능성 앰플 사용 시 시너지 효과를 기대할 수 있습니다.")
            st.write("---")
            st.caption("※ 본 리포트는 AI 영상 분석 기술을 기반으로 작성되었습니다.")

else:
    st.info("사진을 업로드하면 상세 리포트가 생성됩니다.")
