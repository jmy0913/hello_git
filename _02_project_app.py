import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px

# ✅ DB 연결 함수
def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='skn14',
        password='skn14',
        database='projectdb'
    )

# ✅ 충전소 요약 데이터
@st.cache_data
def load_summary_data():
    conn = get_connection()
    query = """
    SELECT 
        r.zname AS region,
        COUNT(DISTINCT s.statId) AS station_count,
        e.vehicle_count
    FROM stations s
    JOIN region_map r ON s.zcode = r.zcode
    JOIN ev_registered_yearly e ON r.zname = e.zname
    WHERE e.year = 2025
    GROUP BY r.zname, e.vehicle_count
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df["보급률(%)"] = (df["station_count"] / df["vehicle_count"]) * 100
    return df

# ✅ 전체 충전소 주소 → 시/구/동 추출
@st.cache_data
def load_all_address_data():
    conn = get_connection()
    df = pd.read_sql("SELECT statId, statNm, addr FROM stations", conn)
    conn.close()
    addr_split = df["addr"].str.split(" ", expand=True)
    df["시"] = addr_split[0]
    df["구"] = addr_split[1]
    df["동"] = addr_split[2]
    return df

# ✅ 충전소 상세정보
def load_station_detail(statId):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM stations WHERE statId = %s", conn, params=(statId,))
    conn.close()
    return df.iloc[0] if not df.empty else None

# ✅ 페이지 구성
st.set_page_config(layout="wide")
st.sidebar.title("📋 메뉴")
page = st.sidebar.radio("페이지를 선택하세요", ["📊 충전소 현황 분석", "📍 지역별 충전소 조회"])

# ---------- Page 1: 보급률 ----------
if page == "📊 충전소 현황 분석":
    st.title("🚗 전기차 충전소 시각화 대시보드")
    st.markdown("전국 **전기차 충전소 수**와 **전기차 등록 수 대비 보급률**을 시각화합니다.")

    summary_df = load_summary_data()

    st.subheader("📊 지역별 충전소 수")
    fig1 = px.bar(summary_df, x="region", y="station_count", title="시도별 충전소 수", text_auto=True)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("✅ 전기차 대비 충전소 보급률 TOP 5")
    top5 = summary_df.sort_values("보급률(%)", ascending=False).head(5)
    st.dataframe(top5[["region", "station_count", "vehicle_count", "보급률(%)"]])

    st.subheader("⚠️ 보급률 낮은 지역 TOP 5")
    bottom5 = summary_df.sort_values("보급률(%)", ascending=True).head(5)
    st.dataframe(bottom5[["region", "station_count", "vehicle_count", "보급률(%)"]])

    st.subheader("📈 지역별 보급률 차트")
    fig2 = px.bar(
        summary_df.sort_values("보급률(%)", ascending=False),
        x="region",
        y="보급률(%)",
        title="충전소 보급률",
        text_auto=True,
        color="보급률(%)",
        color_continuous_scale="YlGnBu"
    )
    st.plotly_chart(fig2, use_container_width=True)

# ---------- Page 2: 충전소 조회 ----------
elif page == "📍 지역별 충전소 조회":
    st.title("📍 동별 전기차 충전소 조회")
    df = load_all_address_data()

    cities = sorted(df["시"].dropna().unique())
    selected_city = st.selectbox("시 선택", cities)

    if selected_city:
        gu_list = sorted(df[df["시"] == selected_city]["구"].dropna().unique())
        selected_gu = st.selectbox("구 선택", gu_list)

        if selected_gu:
            dong_list = sorted(df[(df["시"] == selected_city) & (df["구"] == selected_gu)]["동"].dropna().unique())
            selected_dong = st.selectbox("동 선택", dong_list)

            if selected_dong:
                filtered = df[(df["시"] == selected_city) & (df["구"] == selected_gu) & (df["동"] == selected_dong)]

                st.markdown(f"### 🔌 {selected_city} {selected_gu} {selected_dong} 충전소 목록")
                stat_names = filtered["statNm"].tolist()
                selected_statNm = st.selectbox("충전소 선택", stat_names)

                if selected_statNm:
                    statId = filtered[filtered["statNm"] == selected_statNm]["statId"].values[0]
                    detail = load_station_detail(statId)

                    st.markdown("### 📋 충전소 상세 정보")
                    st.write(f"**이름:** {detail['statNm']}")
                    st.write(f"**주소:** {detail['addr']}")
                    st.write(f"**위도/경도:** {detail['lat']}, {detail['lng']}")
                    st.write(f"**운영기관:** {detail['busiNm']}")
                    st.write(f"**설치년도:** {detail['year']}")
