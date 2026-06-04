import streamlit as st
import pandas as pd
import altair as alt
import time
from datetime import datetime

# 页面配置
st.set_page_config(page_title="无人机心跳监测系统", page_icon="🛸", layout="wide")

# ---------- 初始化会话状态 ----------
if "heartbeat_log" not in st.session_state:
    st.session_state.heartbeat_log = []      # 存储已接收的心跳包 [{"seq": int, "time": datetime}]
if "drone_seq" not in st.session_state:
    st.session_state.drone_seq = 1           # 无人机待发送的序号
if "last_recv_time" not in st.session_state:
    st.session_state.last_recv_time = None   # 上次收到心跳的时间戳（秒）
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()  # 上次页面刷新的时间（控制每秒发送一次）

# ---------- 核心心跳逻辑（每秒执行一次）----------
current_time = time.time()
# 距离上次刷新超过1秒，才发送一个新的心跳包（模拟每秒一次）
if current_time - st.session_state.last_update >= 1.0:
    # 无人机发送一个心跳包（序号递增）
    send_seq = st.session_state.drone_seq
    send_time = datetime.now()
    
    # 模拟地面站接收：这里假设总是成功接收（若需要演示掉线，可在此增加随机丢包逻辑）
    # 为了满足作业“3秒没收到就报警”，我们保持可靠接收，超时只会发生在程序启动后前三秒未收到任何包。
    # 但为了演示超时效果，可以增加一个侧边栏开关模拟丢包。
    # 这里提供标准版（无丢包），但依然能检测超时（例如初始状态或者清空历史后）。
    receive_success = True   # 始终接收
    
    if receive_success:
        st.session_state.heartbeat_log.append({"seq": send_seq, "time": send_time})
        st.session_state.last_recv_time = send_time.timestamp()
    
    # 无人机序号递增
    st.session_state.drone_seq += 1
    # 更新最后刷新时间
    st.session_state.last_update = current_time

# 强制页面每秒自动刷新（使用 st.empty + time.sleep 会阻塞，改用 st.rerun 配合 st_autorefresh 更简单）
# 但 st_autorefresh 需要额外包，这里使用 st.empty + 定时刷新技巧：在底部加一个自动刷新的 meta 标签
# Streamlit 原生不支持自动刷新，推荐使用 streamlit_autorefresh 组件。为了减少依赖，我们使用 JavaScript 注入实现每秒刷新。
# 为了代码稳定且无额外依赖，采用 <meta> 标签实现自动刷新。
st.markdown(
    """
    <meta http-equiv="refresh" content="1">
    """,
    unsafe_allow_html=True
)

# ---------- 掉线检测 ----------
connection_ok = True
time_since_last = None
if st.session_state.last_recv_time is not None:
    elapsed = time.time() - st.session_state.last_recv_time
    time_since_last = elapsed
    if elapsed > 3.0:
        connection_ok = False
else:
    connection_ok = False  # 从未收到过心跳

# ---------- UI 布局 ----------
st.title("🛸 无人机通信心跳监测可视化")
st.markdown("模拟无人机每秒发送心跳包（含序号和时间），地面站接收并监测连接状态。")

# 指标展示
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("无人机已发送包数", st.session_state.drone_seq - 1)
with col2:
    st.metric("地面站接收包数", len(st.session_state.heartbeat_log))
with col3:
    if time_since_last is not None:
        st.metric("距离上次心跳", f"{time_since_last:.2f} 秒")
    else:
        st.metric("距离上次心跳", "无数据")
with col4:
    if connection_ok:
        st.success("✅ 连接正常")
    else:
        st.error("⚠️ 连接超时！超过3秒未收到心跳包")

# 显示最新心跳信息
if st.session_state.heartbeat_log:
    last = st.session_state.heartbeat_log[-1]
    st.info(f"📡 最新心跳 → 序号: {last['seq']}  |  接收时间: {last['time'].strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning("⏳ 等待接收心跳包...")

# 折线图：心跳序号随时间变化
if len(st.session_state.heartbeat_log) >= 2:
    df = pd.DataFrame(st.session_state.heartbeat_log)
    df["time"] = pd.to_datetime(df["time"])
    chart = alt.Chart(df).mark_line(point=True, color="#1f77b4").encode(
        x=alt.X("time:T", title="接收时间", axis=alt.Axis(format="%H:%M:%S")),
        y=alt.Y("seq:Q", title="心跳包序号", scale=alt.Scale(zero=False)),
        tooltip=["seq", "time"]
    ).properties(height=400, title="心跳包序号变化趋势").interactive()
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("📊 收到至少2个心跳包后，折线图将自动显示。")

# 数据明细表格
with st.expander("📋 查看所有心跳记录明细"):
    if st.session_state.heartbeat_log:
        df_display = pd.DataFrame(st.session_state.heartbeat_log).copy()
        df_display["time"] = df_display["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df_display.columns = ["序号", "接收时间"]
        st.dataframe(df_display, use_container_width=True)
    else:
        st.write("暂无记录")

# 侧边栏：清空历史
st.sidebar.title("⚙️ 控制面板")
if st.sidebar.button("🗑️ 清空所有心跳记录"):
    st.session_state.heartbeat_log = []
    st.session_state.drone_seq = 1
    st.session_state.last_recv_time = None
    st.session_state.last_update = time.time()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(
    "**工作原理**\n\n"
    "- 无人机每秒自动发送一个心跳包（序号递增）\n"
    "- 地面站实时接收并记录\n"
    "- 若连续3秒未收到任何心跳包，系统判定掉线并报警\n"
    "- 折线图展示成功接收的序号随时间变化\n\n"
    "**注意**：本模拟默认网络稳定、不丢包。若要测试掉线场景，可清空历史观察初始状态，或手动断开网络（开发者工具中限制网络速度）。"
)
