import streamlit as st
import cv2
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image

# 페이지 설정
st.set_page_config(page_title="AX 피부 분석 자동화 툴", layout="wide")

st.title("✨ AI 피부 분석 & 비포/애프터 대시보드")
st.markdown("""
이 툴은 업로드된 사진을 분석하여 피부의 **홍조(Redness)**와 **톤 균일도(Tone)** 변화를 정량화합니다.
비포 사진부터 순서대로 업로드해 주세요.
""")

# 1. 파일 업로드 섹션
uploaded_files = st.file_uploader("피부 사진들을 업로드하세요 (여러 장 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

def analyze_skin(image):
    # 이미지를 OpenCV 형식으로 변환
    img = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # 1. 홍조(Redness) 분석: Lab 색공간에서 a채널(빨강-초록) 활용
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    redness_score = np.mean(a) # a값이 높을수록 붉은기가 강함
    
    # 2. 톤 균일도(Tone) 분석: 밝기(L) 채널의 표준편차 활용
    # 표준편차가 낮을수록 톤이 균일함 (우리는 점수화를 위해 역산)
    tone_std = np.std(l)
    tone_score = 100 - tone_std # 100에 가까울수록 균일
    
    return round(redness_score, 2), round(tone_score, 2)

if uploaded_files:
    cols = st.columns(len(uploaded_files))
    data = []
    
    # 2. 이미지 전시 및 분석
    for i, file in enumerate(uploaded_files):
        img = Image.open(file)
        red_val, tone_val = analyze_skin(img)
        
        # 데이터 저장
        label = f"{i+1}회차" if i > 0 else "Before"
        data.append({"세션": label, "홍조 지수": red_val, "톤 균일도": tone_val})
        
        with cols[i]:
            st.image(img, caption=label, use_container_width=True)
            st.write(f"🔴 홍조: {red_val}")
            st.write(f"⚪ 톤: {tone_val}")

    # 3. 데이터 시각화
    df = pd.DataFrame(data)
    
    st.divider()
    st.subheader("📊 분석 결과 리포트")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_red = px.line(df, x="세션", y="홍조 지수", title="회차별 홍조 변화 (낮을수록 개선)", markers=True)
        st.plotly_chart(fig_red, use_container_width=True)
        
    with col_chart2:
        fig_tone = px.line(df, x="세션", y="톤 균일도", title="회차별 톤 균일도 변화 (높을수록 개선)", markers=True)
        st.plotly_chart(fig_tone, use_container_width=True)

    # 4. 개선율 계산 (Before vs Last After)
    if len(data) >= 2:
        before = data[0]
        after = data[-1]
        
        red_impro = ((before['홍조 지수'] - after['홍조 지수']) / before['홍조 지수']) * 100
        tone_impro = ((after['톤 균일도'] - before['톤 균일도']) / before['톤 균일도']) * 100
        
        st.success(f"### 📢 분석 요약")
        st.write(f"- 첫 회차 대비 **홍조가 {red_impro:.1f}% 개선**되었습니다.")
        st.write(f"- 피부 톤 균일도가 **{tone_impro:.1f}% 향상**되었습니다.")
        
        best_session = df.loc[df['톤 균일도'].idxmax()]['세션']
        st.info(f"💡 전체 세션 중 피부 상태가 가장 좋았던 회차는 **[{best_session}]** 입니다.")

else:
    st.info("사진을 업로드하면 분석이 시작됩니다.")
