import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime
import threading
from queue import Queue
import random
from collections import deque

# ==================== 心跳模拟器类 ====================
class HeartbeatSimulator:
    """无人机心跳包模拟器"""
    
    def __init__(self, interval=1.0, packet_loss_rate=0):
        """
        初始化心跳模拟器
        
        Args:
            interval: 心跳发送间隔(秒)
            packet_loss_rate: 丢包率 (0-1)
        """
        self.interval = interval
        self.packet_loss_rate = packet_loss_rate
        self.sequence = 0
        self.running = False
        self.heartbeat_queue = Queue()
        self.thread = None
        
    def start(self):
        """启动心跳模拟"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._generate_heartbeats, daemon=True)
        self.thread.start()
        
    def stop(self):
        """停止心跳模拟"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _generate_heartbeats(self):
        """生成心跳包的后台线程"""
        while self.running:
            # 模拟丢包
            should_send = random.random() > self.packet_loss_rate
            
            if should_send:
                self.sequence += 1
                heartbeat_packet = {
                    'sequence': self.sequence,
                    'timestamp': datetime.now(),
                    'packet_id': f"HB_{self.sequence:04d}"
                }
                self.heartbeat_queue.put(heartbeat_packet)
            
            # 等待下一个心跳
            time.sleep(self.interval)
    
    def get_heartbeat(self):
        """
        获取最新的心跳包（非阻塞）
        
        Returns:
            心跳包字典或None
        """
        if not self.running:
            return None
        
        try:
            # 非阻塞获取
            heartbeat = self.heartbeat_queue.get_nowait()
            return heartbeat
        except:
            return None

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="无人机心跳监测系统",
    page_icon="🚁",
    layout="wide"
)

# ==================== 初始化Session State ====================
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.heartbeat_data = deque(maxlen=200)  # 存储心跳数据
    st.session_state.last_received_time = None
    st.session_state.is_connected = True
    st.session_state.simulator = None
    st.session_state.running = False
    st.session_state.packet_loss_count = 0
    st.session_state.last_sequence = 0
    st.session_state.start_time = None

# ==================== 标题 ====================
st.title("🚁 无人机通信心跳监测可视化系统")
st.markdown("---")

# ==================== 侧边栏控制 ====================
with st.sidebar:
    st.header("⚙️ 控制面板")
    
    # 模拟参数设置
    st.subheader("📡 通信参数设置")
    heartbeat_interval = st.number_input(
        "心跳发送间隔 (秒)",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="无人机发送心跳包的频率"
    )
    
    timeout_threshold = st.number_input(
        "连接超时阈值 (秒)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="超过此时间未收到心跳包则判定为掉线"
    )
    
    # 故障模拟
    st.subheader("🔧 故障模拟测试")
    simulate_packet_loss = st.checkbox("启用丢包模拟", value=False)
    if simulate_packet_loss:
        loss_rate = st.slider("丢包率 (%)", 0, 100, 20, help="模拟网络丢包情况")
    else:
        loss_rate = 0
    
    st.markdown("---")
    
    # 控制按钮
    st.subheader("🎮 系统控制")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 启动监测", type="primary", use_container_width=True):
            if not st.session_state.running:
                # 初始化模拟器
                st.session_state.simulator = HeartbeatSimulator(
                    interval=heartbeat_interval,
                    packet_loss_rate=loss_rate / 100 if simulate_packet_loss else 0
                )
                st.session_state.simulator.start()
                st.session_state.running = True
                st.session_state.heartbeat_data.clear()
                st.session_state.last_received_time = datetime.now()
                st.session_state.is_connected = True
                st.session_state.packet_loss_count = 0
                st.session_state.last_sequence = 0
                st.session_state.start_time = datetime.now()
                st.success("✅ 系统已启动")
                time.sleep(0.1)
                st.rerun()
    
    with col2:
        if st.button("⏹️ 停止监测", use_container_width=True):
            if st.session_state.simulator:
                st.session_state.simulator.stop()
            st.session_state.running = False
            st.warning("⚠️ 系统已停止")
            time.sleep(0.1)
            st.rerun()
    
    st.markdown("---")
    
    # 状态指示
    st.subheader("📊 系统状态")
    if st.session_state.running:
        st.success("🟢 监测运行中")
        if st.session_state.start_time:
            runtime = (datetime.now() - st.session_state.start_time).seconds
            st.info(f"运行时间: {runtime // 60}:{runtime % 60:02d}")
    else:
        st.error("🔴 监测已停止")
    
    # 使用说明
    with st.expander("📖 使用说明"):
        st.markdown("""
        **功能说明:**
        1. 点击「启动监测」开始接收心跳
        2. 可调整心跳间隔和超时阈值
        3. 可开启丢包模拟测试系统稳定性
        4. 实时图表展示通信状态
        
        **状态说明:**
        - 🟢 绿色: 连接正常
        - 🔴 红色: 连接超时
        - 延迟>100ms需关注网络状况
        """)

# ==================== 主内容区 ====================
col1, col2 = st.columns([2, 1])

# 更新心跳数据
if st.session_state.running and st.session_state.simulator:
    # 获取新心跳包
    heartbeat_packet = st.session_state.simulator.get_heartbeat()
    
    if heartbeat_packet:
        current_time = datetime.now()
        sequence_num = heartbeat_packet['sequence']
        
        # 检测丢包（序号不连续）
        if st.session_state.last_sequence > 0:
            gap = sequence_num - st.session_state.last_sequence - 1
            if gap > 0:
                st.session_state.packet_loss_count += gap
        
        st.session_state.last_sequence = sequence_num
        
        # 计算延迟（毫秒）
        delay_ms = (current_time - heartbeat_packet['timestamp']).total_seconds() * 1000
        
        # 更新连接状态
        was_connected = st.session_state.is_connected
        
        # 重置最后接收时间
        st.session_state.last_received_time = current_time
        
        # 如果之前是断连状态，现在恢复
        if not st.session_state.is_connected:
            st.session_state.is_connected = True
            st.success("✅ 连接已恢复")
        
        # 添加数据
        st.session_state.heartbeat_data.append({
            'sequence': sequence_num,
            'send_time': heartbeat_packet['timestamp'],
            'receive_time': current_time,
            'delay_ms': delay_ms,
            'packet_id': heartbeat_packet['packet_id']
        })
    
    # 检查超时（仅当有数据后才开始检查）
    if st.session_state.last_received_time and len(st.session_state.heartbeat_data) > 0:
        current_time = datetime.now()
        time_diff = (current_time - st.session_state.last_received_time).total_seconds()
        
        if time_diff > timeout_threshold and st.session_state.is_connected:
            st.session_state.is_connected = False
            st.error(f"🚨 连接超时！已 {time_diff:.1f} 秒未收到心跳包")
    
    # ==================== 左侧：可视化图表 ====================
    with col1:
        st.subheader("📈 实时监控图表")
        
        if len(st.session_state.heartbeat_data) > 0:
            # 创建DataFrame
            df = pd.DataFrame(list(st.session_state.heartbeat_data))
            
            # 创建子图
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=(
                    "<b>📊 心跳序号趋势图</b>",
                    "<b>⏱️ 接收延迟监控 (ms)</b>",
                    "<b>🔗 连接状态</b>"
                ),
                vertical_spacing=0.12,
                row_heights=[0.4, 0.35, 0.25]
            )
            
            # 1. 序号变化图
            fig.add_trace(
                go.Scatter(
                    x=df['receive_time'],
                    y=df['sequence'],
                    mode='lines+markers',
                    name='心跳序号',
                    line=dict(color='#00CED1', width=2),
                    marker=dict(size=6, color='#00CED1', symbol='circle'),
                    hovertemplate='<b>序号: %{y}</b><br>时间: %{x|%H:%M:%S}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # 2. 延迟图
            # 添加阈值线
            fig.add_hline(y=100, line_dash="dash", line_color="orange", 
                         annotation_text="警告阈值(100ms)", row=2, col=1)
            
            fig.add_trace(
                go.Scatter(
                    x=df['receive_time'],
                    y=df['delay_ms'],
                    mode='lines+markers',
                    name='延迟',
                    line=dict(color='#FF6B6B', width=2),
                    marker=dict(size=6, color='#FF6B6B', symbol='circle'),
                    fill='tozeroy',
                    fillcolor='rgba(255, 107, 107, 0.2),
                    hovertemplate='<b>延迟: %{y:.1f}ms</b><br>时间: %{x|%H:%M:%S}<extra></extra>'
                ),
                row=2, col=1
            )
            
            # 3. 连接状态图
            # 创建状态数据
            status_data = []
            status_colors = []
            for i, row in df.iterrows():
                # 简化显示，只显示最近的状态
                status_data.append(1)
                status_colors.append('green')
            
            # 添加当前连接状态
            current_status_time = datetime.now()
            current_status = 1 if st.session_state.is_connected else 0
            
            fig.add_trace(
                go.Scatter(
                    x=list(df['receive_time']) + [current_status_time],
                    y=[1] * len(df) + [current_status],
                    mode='lines+markers',
                    name='连接状态',
                    line=dict(color='green' if st.session_state.is_connected else 'red', width=3),
                    marker=dict(
                        size=10,
                        color='green' if st.session_state.is_connected else 'red',
                        symbol='circle'
                    ),
                    hovertemplate='<b>状态: %{text}</b><br>时间: %{x|%H:%M:%S}<extra></extra>',
                    text=['在线'] * len(df) + (['在线'] if st.session_state.is_connected else ['离线'])
                ),
                row=3, col=1
            )
            
            # 更新布局
            fig.update_layout(
                height=700,
                showlegend=True,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            # 更新坐标轴
            fig.update_xaxes(title_text="时间", row=3, col=1, showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(title_text="序号", row=1, col=1, showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(title_text="延迟 (ms)", row=2, col=1, showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(title_text="状态", tickvals=[0, 1], ticktext=['离线', '在线'], row=3, col=1, range=[-0.5, 1.5])
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 原始数据表格（可折叠）
            with st.expander("📋 查看详细数据"):
                st.dataframe(
                    df[['sequence', 'delay_ms', 'packet_id', 'receive_time']].tail(20),
                    use_container_width=True,
                    column_config={
                        'sequence': '序号',
                        'delay_ms': st.column_config.NumberColumn('延迟(ms)', format='%.2f'),
                        'packet_id': '数据包ID',
                        'receive_time': st.column_config.DatetimeColumn('接收时间', format='HH:mm:ss')
                    }
                )
        else:
            st.info("⏳ 等待接收心跳数据...")
            st.info("提示: 点击「启动监测」开始接收数据")
    
    # ==================== 右侧：信息面板 ====================
    with col2:
        st.subheader("📡 实时信息")
        
        if len(st.session_state.heartbeat_data) > 0:
            latest = st.session_state.heartbeat_data[-1]
            
            # 关键指标卡片
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("最新序号", latest['sequence'], 
                         delta=latest['sequence'] - st.session_state.last_sequence if st.session_state.last_sequence > 0 else None)
            with col_b:
                delay_color = "normal" if latest['delay_ms'] < 100 else "inverse"
                st.metric("最新延迟", f"{latest['delay_ms']:.1f}ms", 
                         delta_color="off")
            with col_c:
                st.metric("丢包次数", st.session_state.packet_loss_count)
            
            st.markdown("---")
            
            # 连接状态
            st.subheader("🔌 连接状态")
            if st.session_state.is_connected:
                st.success("### ✅ 在线")
                st.caption("通信链路正常")
            else:
                st.error("### ❌ 离线")
                st.warning("⚠️ 无人机已掉线，请检查通信链路")
            
            # 统计信息
            st.subheader("📊 统计信息")
            df_stats = pd.DataFrame(list(st.session_state.heartbeat_data))
            
            total_packets = len(df_stats)
            avg_delay = df_stats['delay_ms'].mean()
            max_delay = df_stats['delay_ms'].max()
            min_delay = df_stats['delay_ms'].min()
            
            # 计算接收率
            expected_packets = int((datetime.now() - st.session_state.start_time).total_seconds() / heartbeat_interval) if st.session_state.start_time else 1
            receive_rate = (total_packets / max(expected_packets, 1)) * 100
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.metric("总接收包数", total_packets)
                st.metric("平均延迟", f"{avg_delay:.1f}ms")
                st.metric("最小延迟", f"{min_delay:.1f}ms")
            with metric_col2:
                st.metric("期望包数", max(expected_packets, 1))
                st.metric("最大延迟", f"{max_delay:.1f}ms")
                st.metric("接收率", f"{receive_rate:.1f}%")
            
            st.markdown("---")
            
            # 时间信息
            st.subheader("⏰ 时间信息")
            st.caption(f"启动时间: {st.session_state.start_time.strftime('%H:%M:%S') if st.session_state.start_time else '--'}")
            st.caption(f"最后接收: {latest['receive_time'].strftime('%H:%M:%S')}")
            if st.session_state.last_received_time:
                time_since_last = (datetime.now() - st.session_state.last_received_time).total_seconds()
                st.caption(f"距上次接收: {time_since_last:.2f}秒")
                if time_since_last > 1:
                    st.progress(min(time_since_last / timeout_threshold, 1.0))
            
            # 警报信息
            if not st.session_state.is_connected:
                st.markdown("---")
                st.error(f"🚨 **连接超时警告**\n\n已超过 {timeout_threshold} 秒未收到心跳包！")
        else:
            st.info("暂无数据，请启动系统")
            st.info("💡 提示: 点击左侧「启动监测」按钮开始")
    
    # 自动刷新
    time.sleep(0.1)
    st.rerun()

else:
    with col1:
        st.info("👈 **请在左侧面板点击「启动监测」开始**")
        
        # 展示示例图表
        st.subheader("📊 预览示例")
        
        # 创建示例数据图表
        fig_example = make_subplots(rows=2, cols=1)
        
        # 示例序号图
        example_sequences = list(range(1, 21))
        example_times = pd.date_range(end=datetime.now(), periods=20, freq='S')
        
        fig_example.add_trace(
            go.Scatter(
                x=example_times,
                y=example_sequences,
                mode='lines+markers',
                name='示例数据',
                line=dict(color='#00CED1', width=2),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        fig_example.add_trace(
            go.Scatter(
                x=example_times,
                y=[random.randint(10, 50) for _ in range(20)],
                mode='lines+markers',
                name='示例延迟',
                line=dict(color='#FF6B6B', width=2),
                marker=dict(size=6)
            ),
            row=2, col=1
        )
        
        fig_example.update_layout(height=400, title_text="启动后将显示实时数据")
        fig_example.update_xaxes(title_text="时间")
        fig_example.update_yaxes(title_text="序号", row=1, col=1)
        fig_example.update_yaxes(title_text="延迟(ms)", row=2, col=1)
        
        st.plotly_chart(fig_example, use_container_width=True)
        
    with col2:
        st.info("⚙️ **配置说明**")
        st.markdown("""
        ### 快速开始:
        1. 调整左侧参数（可选）
        2. 点击「启动监测」
        3. 观察实时图表和数据
        
        ### 功能特点:
        - ✅ 实时心跳监测
        - ✅ 自动掉线检测
        - ✅ 延迟统计分析
        - ✅ 丢包率统计
        - ✅ 可视化图表展示
        
        ### 参数建议:
        - **正常场景**: 间隔1秒，超时3秒
        - **弱网场景**: 间隔2秒，超时5秒
        - **测试场景**: 可开启丢包模拟
        """)

# ==================== 页脚 ====================
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col2:
    st.caption("🚁 无人机心跳监测系统 v1.0 | 基于 Streamlit 构建")
