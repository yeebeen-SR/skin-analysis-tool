import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("정량적 분석 데이터를 기반으로 작성된 리포트입니다. 최종 상담 시 전문가의 가이드를 따르세요.")

# 지표 가이드 정의 (상담 시 기준점으로 활용)
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
    st.subheader("📊 지표 변화 그래프")
    fig_main = px.bar(df, x="회차", y=ALL_ITEMS, barmode="group", text_auto=True)
    st.plotly_chart(fig_main, use_container_width=True)

    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 분석 데이터 요약")
        # 대표님 요청: 기준점 가이드 유지
        st.info("💡 수치 가이드: [밝기/결]은 높을수록 우수하며, [홍조/트러블/모공/색소]는 낮을수록 안정적인 상태를 의미합니다.")
        
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
        
        # --- 논리적 분석 및 가이드 섹션 ---
        col_res1, col_res2 = st.columns([1, 1])
        
        with col_res1:
            st.markdown("### 📝 데이터 총평")
            # 부정 지표 개수 파악
            negative_count = sum(1 for d in improved_list if d < -1) 
            
            if negative_count >= 3:
                st.error("⚠️ **주의:** 현재 다수의 지표가 초기 대비 하락한 것으로 나타납니다. 피부 장벽 약화나 외부 자극 요인을 점검해야 합니다.")
            elif improved_list[ALL_ITEMS.index("홍조 (Redness)")] < -5:
                st.warning("⚖️ **민감도 관리 필요:** 전반적인 지표 대비 홍조 수치가 증가하여 현재 피부가 일시적으로 예민해진 상태입니다.")
            else:
                st.success("✅ **안정적 개선:** 주요 지표들이 전반적으로 안정적인 우상향 그래프를 그리고 있습니다.")

            # 가장 큰 변화 지표 언급
            best_idx = np.argmax(improved_list)
            st.write(f"- **핵심 성과:** 현재 {ALL_ITEMS[best_idx]} 영역에서 가장 높은 개선율을 보이고 있습니다.")

        with col_res2:
            st.markdown("### 📍 전문가 관리 가이드")
            # 홍조 기반 시술 여부 판단 로직
            if df.loc[last_idx, "홍조 (Redness)"] > df.loc[0, "홍조 (Redness)"] * 1.05:
                st.info("🛋️ **진정 집중기:** 현재 붉은기가 관찰되는 회복기입니다. **고기능성 앰플(비타민, 레티놀 등) 및 필링제 사용을 즉각 중단**하고 무자극 보습과 재생 관리에만 집중하세요.")
            else:
                st.info("✨ **장벽 유지기:** 피부가 안정 궤도에 올랐습니다. 새로운 제품 시도보다는 현재의 유수분 밸런스를 유지하며 장벽을 탄탄하게 만드는 홈케어를 지속하세요.")
            
            st.warning("🧴 **필수 사항:** 개선된 컨디션을 유지하기 위해 자외선 차단제는 매일 꼼꼼히 사용해 주시기 바랍니다.")

else:
    st.info("사진을 업로드하면 정량적 분석 리포트가 생성됩니다.")
