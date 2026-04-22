import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정
st.set_page_config(page_title="피부 분석 데이터 백업 시스템", layout="wide")

st.title("📂 피부 분석 및 개선율 정량 리포트")
st.markdown("본 리포트는 내부 데이터 분석 및 컨텐츠 백업용 자료입니다.")

# 지표 가이드
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

uploaded_files = st.file_uploader("사진을 업로드하세요 (Before부터 순서대로)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

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
    # [섹션 1] 사진 기록
    st.subheader("📸 분석 대상 기록")
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
    
    # [섹션 2] 상세 추이 그래프
    st.divider()
    st.subheader("📊 항목별 개선 추이 상세")
    item_cols = st.columns(2)
    for idx, item in enumerate(ALL_ITEMS):
        with item_cols[idx % 2]:
            fig_item = px.line(df, x="회차", y=item, markers=True, text=item, title=f"[{item}] 추이")
            fig_item.update_traces(textposition="top center")
            st.plotly_chart(fig_item, use_container_width=True)

    # [섹션 3] 최종 분석 데이터 요약 (개선율 워딩 반영)
    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 개선율 분석 요약")
        
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
                # '개선율' 워딩 명시
                st.metric(label=f"{item} 개선율", value=f"{diff:.1f}%", delta=f"현재 점수: {val_now}")

        st.divider()
        
        # --- 내부 백업용 정밀 분석 섹션 ---
        col_res1, col_res2 = st.columns([1, 1])
        
        with col_res1:
            st.markdown("### 📝 전문 데이터 총평")
            # 1. 초기 대비 최종 누적 개선율
            avg_imp = sum(improved_list) / len(improved_list)
            status = "개선" if avg_imp >= 0 else "하락"
            st.subheader(f"초기 대비 최종 누적 개선율: {avg_imp:.1f}% {status}")
            
            # 2. 최적 개선 세션 (Before 대비 합산 개선도가 가장 높은 시점)
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
            st.success(f"🏆 **최적 개선 세션:** 분석 결과, 데이터 정점은 **[{best_label}]** 입니다.")

            # 3. 최고/최저 개선 지표
            top_idx = np.argmax(improved_list)
            worst_idx = np.argmin(improved_list)
            st.write(f"- **최고 개선 지표:** {ALL_ITEMS[top_idx]} ({improved_list[top_idx]:.1f}% 개선)")
            st.write(f"- **최저 개선 지표:** {ALL_ITEMS[worst_idx]} ({improved_list[worst_idx]:.1f}% 하락/정체)")

        with col_res2:
            st.markdown("### ⚡ 최대 개선 구간 분석 (모멘텀)")
            # 4. 최대 개선 구간 (현재 세션 - 이전 세션 변화폭 최대 지점)
            momentum_data = []
            for idx in range(1, len(df)):
                session_impro = []
                for item in ALL_ITEMS:
                    v_prev, v_curr = df.loc[idx-1, item], df.loc[idx, item]
                    if item in POSITIVE_METRICS: imp = ((v_curr - v_prev) / v_prev) * 100
                    else: imp = ((v_prev - v_curr) / v_prev) * 100
                    session_impro.append(imp)
                momentum_data.append(sum(session_impro) / len(session_impro))
            
            if momentum_data:
                max_mom_idx = np.argmax(momentum_data)
                start_label = df.loc[max_mom_idx, "회차"]
                end_label = df.loc[max_mom_idx + 1, "회차"]
                st.info(f"🚀 **최대 개선 구간:** [{start_label} → {end_label}]")
                st.write(f"- 해당 구간에서 평균 **{momentum_data[max_mom_idx]:.1f}%**의 최대 변화폭이 기록되었습니다.")
                st.caption("※ 이 시점의 관리 기법이나 사용 제품을 컨텐츠 소스로 활용하는 것을 권장합니다.")

            st.markdown("---")
            # 시술 직후 가이드 (백업용 기록)
            if df.loc[last_idx, "홍조 (Redness)"] > df.loc[0, "홍조 (Redness)"] * 1.05:
                st.warning("⚠️ **특이사항:** 홍조 수치 일시적 상승 (시술 후 반응기)")
            else:
                st.write("✅ **특이사항:** 피부 안정도 양호")

else:
    st.info("데이터 분석을 위해 사진을 업로드해 주세요.")
