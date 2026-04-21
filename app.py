import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 페이지 설정 및 제목 (워딩 수정)
st.set_page_config(page_title="B&A 피부 개선 분석 리포트", layout="wide")

st.title("📋 B&A 피부 개선 분석 리포트")
st.markdown("촬영된 사진을 정량 분석하여 변화를 기록합니다. 첫 번째 사진부터 순서대로 업로드해 주세요.")

# 지표 정의
POSITIVE_METRICS = ["피부 밝기 (Brightness)", "피부결 (Smoothness)"]
NEGATIVE_METRICS = ["홍조 (Redness)", "여드름/트러블 (Acne)", "모공/요철 (Pores)", "색소침착 (Pigmentation)"]
ALL_ITEMS = POSITIVE_METRICS + NEGATIVE_METRICS

# 파일 업로드
uploaded_files = st.file_uploader("사진을 업로드하세요 (Before부터 순서대로)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_skin_pro(image):
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
    
    # [추가] 상단 사진 기록 섹션
    st.subheader("📸 사진 기록")
    img_cols = st.columns(len(uploaded_files))
    
    for i, file in enumerate(uploaded_files):
        label = "Before" if i == 0 else f"After {i}"
        img = Image.open(file)
        analysis = analyze_skin_pro(img)
        analysis["회차"] = label # '세션' 워딩 제거를 위해 '회차'로 변경
        results.append(analysis)
        
        with img_cols[i]:
            st.image(img, caption=label, use_container_width=True)
    
    df = pd.DataFrame(results)
    
    st.divider()
    st.subheader("📊 지표별 개선 추이 분석")
    
    tab1, tab2 = st.tabs(["종합 분석", "상세 항목별"])
    
    with tab1:
        # 통합 막대 그래프 (텍스트/수치 추가)
        fig_main = px.bar(df, x="회차", y=ALL_ITEMS, barmode="group", 
                          text_auto=True, title="전체 지표 변화 상황")
        fig_main.update_layout(xaxis_title="", yaxis_title="상대 점수")
        st.plotly_chart(fig_main, use_container_width=True)
        
    with tab2:
        item_cols = st.columns(2)
        for idx, item in enumerate(ALL_ITEMS):
            with item_cols[idx % 2]:
                # 꺾은선 그래프 (수치 텍스트 추가)
                fig_item = px.line(df, x="회차", y=item, title=f"{item} 추이", 
                                   markers=True, text=item)
                fig_item.update_traces(textposition="top center")
                fig_item.update_yaxes(range=[df[item].min()*0.9, df[item].max()*1.1])
                fig_item.update_layout(xaxis_title="")
                st.plotly_chart(fig_item, use_container_width=True)

    # 최종 개선 성과 리포트 (기존 틀 유지)
    if len(results) >= 2:
        st.divider()
        st.subheader("🎯 최종 개선 성과 리포트")
        
        before = results[0]
        after = results[-1]
        
        summary_cols = st.columns(len(ALL_ITEMS))
        for i, item in enumerate(ALL_ITEMS):
            if item in POSITIVE_METRICS:
                diff = ((after[item] - before[item]) / before[item]) * 100
                guide = "↑ 높을수록 환함/매끄러움"
            else:
                diff = ((before[item] - after[item]) / before[item]) * 100
                guide = "↓ 낮을수록 깨끗함/촘촘함"
            
            with summary_cols[i]:
                # pt 제거, 수치만 노출
                st.metric(label=item, value=after[item], delta=f"{diff:.1f}% 개선")
                st.caption(guide)

        st.divider()
        # 베스트 회차 판독
        best_session_name = df.loc[1:, :].apply(lambda x: sum([x[m] if m in POSITIVE_METRICS else -x[m] for m in ALL_ITEMS]), axis=1).idxmax()
        best_label = df.loc[best_session_name, "회차"]
        
        col_res1, col_res2 = st.columns([2, 1])
        with col_res1:
            st.success(f"🏆 분석 결과, 피부 컨디션이 가장 극대화된 시점은 **[{best_label}]** 입니다.")
            st.write("#### 📝 분석 요약")
            st.write(f"- 초기 대비 전반적인 피부 밸런스가 좋아졌으며, 현재 **{best_label}**에서 가장 높은 개선율을 보입니다.")
        with col_res2:
            st.write("#### 📍 관리 가이드")
            st.write("- 현재의 피부 상태를 유지하기 위해 꾸준한 홈케어를 권장합니다.")

else:
    st.info("사진을 업로드하면 정밀 분석 리포트가 생성됩니다.")
