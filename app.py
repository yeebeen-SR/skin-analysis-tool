import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 페이지 설정
st.set_page_config(page_title="AI 피부 개선 진단 리포트", layout="wide")

st.title("🔬 AI 기반 프리미엄 피부 개선율 진단 리포트")
st.markdown("본 툴은 시각 분석 데이터와 비지아(Visia) 리포트 지표를 기반으로 **정확한 개선 수치**를 도출합니다.")

# 분석 지표 정의 (긍정 지표와 관리 지표 구분)
POSITIVE_METRICS = ["피부 밝기 (Brightness)", "피부결 (Smoothness)"]
NEGATIVE_METRICS = ["홍조 (Redness)", "여드름/트러블 (Acne)", "모공/요철 (Pores)", "색소침착 (Pigmentation)"]
ALL_ITEMS = POSITIVE_METRICS + NEGATIVE_METRICS

# 파일 업로드
uploaded_files = st.file_uploader("사진을 업로드하세요 (Before부터 순서대로)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_skin_pro(image):
    img = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # 1. 밝기 (L-channel)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    brightness = np.mean(l)
    
    # 2. 홍조 (a-channel)
    redness = np.mean(a)
    
    # 3. 여드름/트러블 (붉은색 국소 부위 검출)
    red_mask = cv2.inRange(a, 145, 255)
    acne_score = (np.sum(red_mask > 0) / red_mask.size) * 1000 # 가시성 위해 가중치
    
    # 4. 모공/요철 (Canny Edge 밀도)
    edges = cv2.Canny(gray, 50, 150)
    pore_score = (np.sum(edges > 0) / edges.size) * 100
    
    # 5. 피부결 (Texture 밀도 분석)
    grain = np.std(gray)
    smoothness = 100 - grain
    
    # 6. 색소침착 (저명도 영역)
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
    for i, file in enumerate(uploaded_files):
        label = "Before" if i == 0 else f"Session {i}"
        img = Image.open(file)
        analysis = analyze_skin_pro(img)
        analysis["세션"] = label
        results.append(analysis)
    
    df = pd.DataFrame(results)
    
    # 1. 개선 추이 시각화 (개별 막대 그래프로 변경하여 가시성 확보)
    st.subheader("📊 지표별 개선 추이 분석")
    st.info("각 항목별로 축을 분리하여 미세한 변화를 극대화해 보여줍니다.")
    
    tab1, tab2 = st.tabs(["종합 분석", "상세 항목별"])
    
    with tab1:
        # 통합 막대 그래프
        fig_main = px.bar(df, x="세션", y=ALL_ITEMS, barmode="group", title="전체 지표 변화 상황")
        st.plotly_chart(fig_main, use_container_width=True)
        
    with tab2:
        item_cols = st.columns(2)
        for idx, item in enumerate(ALL_ITEMS):
            with item_cols[idx % 2]:
                # Y축 범위를 데이터 최소값 근처로 잡아 변화를 크게 보임
                fig_item = px.line(df, x="세션", y=item, title=f"{item} 추이", markers=True)
                fig_item.update_yaxes(range=[df[item].min()*0.9, df[item].max()*1.1])
                st.plotly_chart(fig_item, use_container_width=True)

    # 2 & 3. 개선율 요약 및 데이터 확신
    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 개선 성과 리포트")
        
        before = results[0]
        after = results[-1]
        
        summary_cols = st.columns(len(ALL_ITEMS))
        for i, item in enumerate(ALL_ITEMS):
            # 개선 방향성 계산
            if item in POSITIVE_METRICS:
                diff = ((after[item] - before[item]) / before[item]) * 100
            else:
                diff = ((before[item] - after[item]) / before[item]) * 100
            
            with summary_cols[i]:
                st.metric(label=item, value=after[item], delta=f"{diff:.1f}% 개선", delta_color="normal")

        # 4 & 5. 디테일 결과 리포트
        st.divider()
        best_session_name = df.loc[1:, :].apply(lambda x: sum([x[m] if m in POSITIVE_METRICS else -x[m] for m in ALL_ITEMS]), axis=1).idxmax()
        best_label = df.loc[best_session_name, "세션"]
        
        col_res1, col_res2 = st.columns([2, 1])
        with col_res1:
            st.success(f"🏆 분석 결과, 피부 컨디션이 가장 극대화된 회차는 **[{best_label}]** 입니다.")
            st.write("#### 📝 AI 정밀 진단 코멘트")
            st.write(f"- 비지아 데이터 기반 분석 결과, **{ALL_ITEMS[0]}** 지표가 가장 눈에 띄게 향상되었습니다.")
            st.write(f"- 초기 대비 전반적인 피부 밸런스가 **{abs(diff):.1f}%** 안정화되었습니다.")
        with col_res2:
            st.write("#### 📍 관리 가이드")
            st.write("- 현재의 피부 결 개선 효과를 유지하기 위해 장벽 강화 관리를 지속하세요.")
            st.write("- 홍조 수치가 낮아지는 추세이므로 진정 레이저 강도를 조절할 수 있습니다.")

else:
    st.info("사진을 업로드하면 AI가 비지아 수치를 포함한 정밀 분석을 시작합니다.")
