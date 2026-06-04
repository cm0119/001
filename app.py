import streamlit as st
import pandas as pd
import altair as alt
import random
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 页面配置
st.set_page_config(
    page_title="无人机心跳监测系统",
    page_icon="🛸",
    layout="wide"
)

# 初始化会话状态
def init_session_state():
    """初始化session_state中的所有变量"""
    if 'received_heartbeats' not in st.session_state:
        # 存储已接收的心跳包记录，每个元素为字典: {'seq': int, 'time': datetime}
        st.session_state.received_heartbeats = []
    if 'drone_seq' not in st.session_state:
        # 无人机发送序号，每次刷新自动递增
        st.session_state.drone_seq = 1
    if 'last_received_time' not in st.session_state:
        # 上次成功接收心跳的时间戳（秒）
        st.session_state.last_received_time = None

init_session_state()

# 设置自动刷新（每秒触发一次，模拟无人机每秒发送心跳包）
# 关键参数: interval=1000ms, key保证唯一，limit限制最大刷新次数
refresh_count = st_autorefresh(interval=1000, key="drone_heartbeat_refresh", limit=None)

# 侧边栏配置
st.sidebar.title("⚙️ 系统配置")
st.sidebar.markdown("---")

# 丢包模拟开关
packet_loss_enabled = st.sidebar.checkbox("启用丢包模拟 (演示掉线检测)", value=False)

if packet_loss_enabled:
    loss_rate = st.sidebar.slider("丢包概率 (%)", min_value=0, max_value=100, value=30, step=5)
    loss_rate_decimal = loss_rate / 100.0
else:
    loss_rate_decimal = 0.0

# 清空历史按钮
if st.sidebar.button("🧹 清空心跳历史"):
    st.session_state.received_heartbeats = []
    st.session_state.drone_seq = 1
    st.session_state.last_received_time = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(
    "**工作原理**\n\n"
    "- 无人机每秒自动发送一个心跳包（序号连续递增）\n"
    "- 地面站模拟接收，可设置丢包率来演示网络不稳定\n"
    "- 若超过3秒未收到任何心跳包，系统判定连接超时并报警\n"
    "- 折线图展示实际收到的心跳包序号随时间变化情况"
)

# 主界面布局
st.title("🛸 无人机通信心跳监测可视化")
st.markdown("实时模拟无人机心跳包发送与地面站接收状态")

# 核心逻辑: 每次页面刷新(即每秒)模拟无人机发送一个心跳包
# 地面站根据丢包设置决定是否成功接收此包

# 当前无人机待发送的序号
current_drone_seq = st.session_state.drone_seq

# 模拟丢包判定: 是否接收本次心跳
is_received = True
if packet_loss_enabled and loss_rate_decimal > 0:
    if random.random() < loss_rate_decimal:
        is_received = False

# 如果接收成功，则将心跳包记录到历史中
if is_received:
    now_time = datetime.now()
    heartbeat_record = {
        'seq': current_drone_seq,
        'time': now_time
    }
    st.session_state.received_heartbeats.append(heartbeat_record)
    # 更新最近接收时间戳
    st.session_state.last_received_time = now_time.timestamp()
else:
    # 丢包: 不记录心跳包，仅控制台不做输出，用户界面可显示提示
    pass

# 无人机序号始终递增（模拟无人机持续发送，不管地面是否收到）
st.session_state.drone_seq += 1

# 掉线检测: 判断距离上次接收心跳的时间是否超过3秒
connection_timeout = False
time_since_last = None
if st.session_state.last_received_time is not None:
    current_timestamp = datetime.now().timestamp()
    time_since_last = current_timestamp - st.session_state.last_received_time
    if time_since_last > 3.0:
        connection_timeout = True
else:
    # 从未收到过心跳包，显示未连接
    connection_timeout = True

# 显示关键指标
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("无人机累计发送包数", st.session_state.drone_seq - 1)
with col2:
    received_count = len(st.session_state.received_heartbeats)
    st.metric("地面站接收包数", received_count)
with col3:
    if st.session_state.last_received_time is not None and not connection_timeout:
        st.metric("距离上次心跳", f"{time_since_last:.2f} 秒")
    else:
        st.metric("距离上次心跳", "无数据")
with col4:
    if connection_timeout:
        st.error("⚠️ 连接超时！超过3秒未收到心跳包")
    else:
        st.success("✅ 连接正常")

# 显示最近一次心跳信息
if st.session_state.received_heartbeats:
    last_heartbeat = st.session_state.received_heartbeats[-1]
    last_seq = last_heartbeat['seq']
    last_time = last_heartbeat['time'].strftime("%Y-%m-%d %H:%M:%S")
    st.info(f"📡 最新心跳: 序号 {last_seq} | 接收时间 {last_time}")
else:
    st.warning("尚未收到任何心跳包，等待无人机发送...")

# 可视化: 折线图展示心跳包序号随时间变化
if st.session_state.received_heartbeats:
    # 构建DataFrame用于绘图
    df_heartbeats = pd.DataFrame(st.session_state.received_heartbeats)
    # 确保时间列是datetime类型
    df_heartbeats['time'] = pd.to_datetime(df_heartbeats['time'])
    
    # 使用Altair绘制折线图
    chart = alt.Chart(df_heartbeats).mark_line(point=True, color='steelblue').encode(
        x=alt.X('time:T', title='接收时间', axis=alt.Axis(format='%H:%M:%S')),
        y=alt.Y('seq:Q', title='心跳包序号', scale=alt.Scale(zero=False)),
        tooltip=['seq', 'time']
    ).properties(
        title='心跳包序号随时间变化趋势',
        height=400
    ).interactive()
    
    st.altair_chart(chart, use_conta
    with st.expander("📋 查看详细心跳数据列表"):
        display_df = df_heartbeats.copy()
        display_df['time'] = display_df['time'].dt.strftime("%Y-%m-%d %H:%M:%S")
        display_df.rename(columns={'seq': '序号', 'time': '接收时间'}, inplace=True)
        st.dataframe(display_df, use_container_width=True)
