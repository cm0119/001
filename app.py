import streamlit as st
import time
from datetime import datetime
import pandas as pd

# 初始化页面配置
st.set_page_config(page_title="无人机心跳监测系统", layout="wide")
st.title("✈️ 无人机通信心跳监测可视化平台")

# 全局状态缓存：心跳数据、最后接收时间
if "heart_data" not in st.session_state:
    st.session_state.heart_data = []
if "last_recv_time" not in st.session_state:
    st.session_state.last_recv_time = time.time()
if "seq_num" not in st.session_state:
    st.session_state.seq_num = 1

# 侧边栏控制
with st.sidebar:
    st.header("控制面板")
    run_flag = st.checkbox("启动无人机心跳发送", value=False)
    simulate_offline = st.checkbox("模拟无人机掉线（停止发包）", value=False)
    timeout_thresh = st.number_input("掉线超时阈值(秒)", value=3, min_value=1)

alert_box = st.empty()  # 告警弹窗容器
chart_box = st.empty()  # 折线图容器
data_table = st.empty() # 原始数据表容器

# 心跳主循环
if run_flag:
    while True:
        now_ts = time.time()
        now_dt = datetime.now().strftime("%H:%M:%S")
        
        if not simulate_offline:
            # 生成心跳包：序号+当前时间
            pkg_seq = st.session_state.seq_num
            pkg_time = now_dt
            st.session_state.heart_data.append({"包序号": pkg_seq, "接收时间": pkg_time, "时间戳": now_ts})
            st.session_state.last_recv_time = now_ts
            st.session_state.seq_num += 1
            alert_box.success(f"✅ 正常收到心跳包｜序号:{pkg_seq}｜时间:{pkg_time}")
        else:
            # 掉线检测：超过阈值告警
            gap = now_ts - st.session_state.last_recv_time
            if gap > timeout_thresh:
                alert_box.error(f"⚠️ 连接超时！已{round(gap,1)}秒未收到心跳，无人机掉线！")
        
        # 数据可视化渲染
        df = pd.DataFrame(st.session_state.heart_data)
        with chart_box:
            st.subheader("心跳包序号时序折线图")
            st.line_chart(df, x="接收时间", y="包序号")
        with data_table:
            st.dataframe(df[["包序号","接收时间"]], use_container_width=True)
        
        time.sleep(1) # 每秒1次心跳
