import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. 프로젝트 이름 및 워딩 정리 (요청하신 비즈니스 스타일)
st.set_page_config(page_title="스킨 분석 리포트", layout="wide")

st.title("🔬 AI 기반 피부 진단 및 개선율 대시보드")
st.markdown("""
본 솔루션은 사진 분석을 통해 **피부 밝기, 홍조, 모공/요철, 색소침착** 지표를 정량화합니다.  
비포 사진부터 순서대로 업로드하여 개선율을 확인하세요.
""")

# 분석 항목 정의
ITEMS = ["피부 밝기 (Brightness)", "홍조 (Redness)", "모공/요철 (Pores)", "색소침착 (Pigmentation)"]

# 파일 업로드
uploaded_files = st.file_uploader("피부 사진을 업로드하세요 (여러 장 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_skin(image):
    img = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # 1. 피부 밝기 (L채널 평균) - 높을수록 밝음
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    brightness = np.mean(l)
    
    # 2. 홍조 (a채널 평균) - 낮을수록 개선
    redness = np.mean(a)
    
    # 3. 모공/요철 (에지 검출) - 낮을수록 개선
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 30, 70)
    pore_score = (np.sum(edges > 0) / edges.size) * 100
    
    # 4. 색소침착 (어두운 영역 추출) - 낮을수록 개선
    _, dark_spots = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    pigment_score = (np.sum(dark_spots > 0) / dark_spots.size) * 100

    return {
        "피부 밝기 (Brightness)": round(brightness, 1),
        "홍조 (Redness)": round(redness, 1),
        "모공/요철 (Pores)": round(pore_score * 0.7, 1),
        "색소침착 (Pigmentation)": round(pigment_score * 0.5, 1)
    }

if uploaded_files:
    data = []
    cols = st.columns(len(uploaded_files))
    
    for i, file in enumerate(uploaded_files):
        img = Image.open(file)
        analysis = analyze_skin(img)
        
        label = f"Session {i}" if i > 0 else "Before"
        analysis["세션"] = label
        data.append(analysis)
        
        with cols[i]:
            st.image(img, caption=label, use_container_width=True)
            for key, val in list(analysis.items())[:-1]:
                st.write(f"- {key}: **{val}**")

    df = pd.DataFrame(data)
    
    st.divider()
    st.subheader("📊 지표별 개선 추이")
    
    # 그래프 출력
    fig = px.line(df, x="세션", y=ITEMS, title="항목별 변화 추이", markers=True)
    st.plotly_chart(fig, use_container_width=True)
    
    if len(data) >= 2:
        before = data[0]
        after = data[-1]
        
        st.subheader("🎯 최종 개선율 요약 (Before 대비)")
        summary_cols = st.columns(len(ITEMS))
        
        for idx, item in enumerate(ITEMS):
            # 피부 밝기는 높을수록 좋음, 나머지는 낮을수록 좋음
            if "밝기" in item:
                impro = ((after[item] - before[item]) / before[item]) * 100 if before[item] != 0 else 0
            else:
                impro = ((before[item] - after[item]) / before[item]) * 100 if before[item] != 0 else 0
            
            with summary_cols[idx]:
                st.metric(label=item, value=f"{after[item]}", delta=f"{impro:.1f}%")
        
        # 간단 명료한 AI 코멘트
        st.info(f"✨ 분석 결과, 전체 세션 중 피부 상태가 가장 좋았던 회차는 **[{df.loc[:, ITEMS].sum(axis=1).idxmin() if '밝기' not in ITEMS[0] else '분석중'}회차]** 입니다.")

else:
    st.info("비포/애프터 사진을 업로드하시면 분석 리포트가 생성됩니다.")
