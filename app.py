import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time
import threading
import datetime
from typing import List, Dict, Optional
from queue import Queue

# ==================== 心跳模拟器类 ====================

class DroneHeartbeatSimulator:
    """无人机心跳包模拟器，模拟每秒发送心跳包，包含序号和时间戳"""
    
    def __init__(self):
        self.heartbeat_data: List[Dict] = []  # 存储心跳数据
        self.is_running = False
        self.sequence_number = 0
        self.last_heartbeat_time = None
        self.is_connected = True
        self.callback = None
        
    def set_callback(self, callback):
        """设置心跳接收回调函数"""
        self.callback = callback
        
    def generate_heartbeat(self) -> Dict:
        """生成一个心跳包"""
        self.sequence_number += 1
        current_time = datetime.datetime.now()
        
        heartbeat = {
            "sequence": self.sequence_number,
            "timestamp": current_time.strftime("%H:%M:%S"),
            "full_timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "status": "online" if self.is_connected else "offline"
        }
        
        self.heartbeat_data.append({
            "sequence": self.sequence_number,
            "timestamp": current_time,
            "status": "online"
        })
        
        self.last_heartbeat_time = current_time
        self.is_connected = True
        
        return heartbeat
    
    def check_connection(self):
        """检查连接状态，3秒没收到心跳则超时"""
        while self.is_running:
            if self.last_heartbeat_time:
                time_since_last = (datetime.datetime.now() - self.last_heartbeat_time).total_seconds()
                if time_since_last > 3 and self.is_connected:
                    self.is_connected = False
                    # 记录掉线事件
                    offline_event = {
                        "sequence": self.sequence_number,
                        "timestamp": datetime.datetime.now(),
                        "status": "offline",
                        "offline_time": time_since_last
                    }
                    self.heartbeat_data.append(offline_event)
                    if self.callback:
                        self.callback("offline", time_since_last)
            time.sleep(0.5)  # 每0.5秒检查一次
    
    def start_simulator(self, interval: float = 1.0):
        """启动心跳模拟器，每秒发送一次心跳"""
        self.is_running = True
        self.sequence_number = 0
        self.last_heartbeat_time = datetime.datetime.now()
        
        # 启动连接检查线程
        check_thread = threading.Thread(target=self.check_connection, daemon=True)
        check_thread.start()
        
        # 主循环：每秒发送心跳
        while self.is_running:
            heartbeat = self.generate_heartbeat()
            if self.callback:
                self.callback("heartbeat", heartbeat)
            
            time.sleep(interval)
    
    def stop_simulator(self):
        """停止模拟器"""
        self.is_running = False
    
    def get_data_for_visualization(self) -> tuple:
        """获取用于可视化的数据"""
        sequences = []
        times = []
        statuses = []
        
        for record in self.heartbeat_data:
            if "timestamp" in record:
                sequences.append(record["sequence"])
                times.append(record["timestamp"])
                statuses.append(1 if record.get("status") == "online" else 0)
        
        return sequences, times, statuses
    
    def get_recent_data(self, limit: int = 50) -> List[Dict]:
        """获取最近的心跳数据"""
        return self.heartbeat_data[-limit:]


# ==================== 心跳监测器类 ====================

class HeartbeatMonitor:
    """心跳监测器，管理数据流和UI更新"""
    
    def __init__(self):
        self.simulator = DroneHeartbeatSimulator()
        self.simulator.set_callback(self.on_heartbeat_event)
        self.heartbeat_log = []
        self.alert_messages = []
        self.running = False
        self.thread = None
        
    def on_heartbeat_event(self, event_type, data):
        """处理心跳事件"""
        if event_type == "heartbeat":
            self.heartbeat_log.append({
                "序号": data["sequence"],
                "时间": data["timestamp"],
                "完整时间戳": data["full_timestamp"],
                "状态": "✅ 在线"
            })
            # 只保留最近100条记录
            if len(self.heartbeat_log) > 100:
                self.heartbeat_log = self.heartbeat_log[-100:]
                
        elif event_type == "offline":
            alert_msg = f"⚠️ 连接超时！已 {data:.1f} 秒未收到心跳包"
            self.alert_messages.append({
                "时间": datetime.datetime.now().strftime("%H:%M:%S"),
                "警告": alert_msg
            })
            if len(self.alert_messages) > 20:
                self.alert_messages = self.alert_messages[-20:]
    
    def start(self):
        """启动模拟器"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_simulator, daemon=True)
            self.thread.start()
    
    def run_simulator(self):
        """在后台线程运行模拟器"""
        self.simulator.start_simulator(interval=1.0)
    
    def stop(self):
        """停止模拟器"""
        self.running = False
        if self.simulator:
            self.simulator.stop_simulator()
    
    def get_dataframe(self):
        """获取心跳数据DataFrame"""
        if self.heartbeat_log:
            df = pd.DataFrame(self.heartbeat_log)
            # 添加序号作为x轴
            df["显示序号"] = range(1, len(df) + 1)
            return df
        return pd.DataFrame()
    
    def get_alert_dataframe(self):
        """获取警告数据DataFrame"""
        if self.alert_messages:
            return pd.DataFrame(self.alert_messages)
        return pd.DataFrame()


# ==================== Streamlit UI ====================

# 配置页面
st.set_page_config(
    page_title="无人机心跳监测系统",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🚁 无人机心跳监测可视化系统")
    st.markdown("---")
    
    # 初始化session state
    if 'monitor' not in st.session_state:
        st.session_state.monitor = HeartbeatMonitor()
        st.session_state.is_monitoring = False
        st.session_state.auto_scroll = True
    
    monitor = st.session_state.monitor
    
    # 侧边栏控制面板
    with st.sidebar:
        st.header("🎮 控制面板")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ 启动监测", use_container_width=True):
                if not st.session_state.is_monitoring:
                    monitor.start()
                    st.session_state.is_monitoring = True
                    st.rerun()
        
        with col2:
            if st.button("⏹️ 停止监测", use_container_width=True):
                if st.session_state.is_monitoring:
                    monitor.stop()
                    st.session_state.is_monitoring = False
                    st.rerun()
        
        st.markdown("---")
        
        # 状态显示
        st.subheader("📡 系统状态")
        if st.session_state.is_monitoring:
            st.success("🟢 监测运行中")
        else:
            st.error("🔴 监测已停止")
        
        st.markdown("---")
        
        # 配置信息
        st.subheader("⚙️ 配置信息")
        st.info("""
        - 心跳频率: 1次/秒
        - 超时阈值: 3秒
        - 数据保留: 最近100条
        """)
        
        st.markdown("---")
        
        # 自动滚动开关
        st.session_state.auto_scroll = st.checkbox("自动滚动", value=st.session_state.auto_scroll)
        
        # 清除按钮
        if st.button("🗑️ 清除历史数据", use_container_width=True):
            monitor.heartbeat_log = []
            monitor.alert_messages = []
            st.rerun()
    
    # 主内容区域 - 三个选项卡
    tab1, tab2, tab3 = st.tabs(["📊 实时监控图表", "📋 心跳数据日志", "⚠️ 告警记录"])
    
    with tab1:
        # 图表区域
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 心跳序号变化趋势")
            
            df = monitor.get_dataframe()
            
            if not df.empty:
                # 使用plotly创建折线图
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df["显示序号"],
                    y=df["序号"],
                    mode='lines+markers',
                    name='心跳序号',
                    line=dict(color='#00b4d8', width=2),
                    marker=dict(size=6, color='#0077b6'),
                    hovertemplate='序号: %{y}<br>时间: %{text}<extra></extra>',
                    text=df["时间"]
                ))
                
                fig.update_layout(
                    title="心跳序号随时间变化",
                    xaxis_title="心跳次数",
                    yaxis_title="心跳序号",
                    hovermode='x unified',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=400
                )
                
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("等待接收心跳数据...点击「启动监测」开始")
        
        with col2:
            st.subheader("🔄 实时状态")
            
            if not df.empty:
                latest = df.iloc[-1]
                st.metric("最新心跳序号", latest["序号"])
                st.metric("接收心跳总数", len(df))
                
                # 连接状态指示器
                st.markdown("### 连接状态")
                if st.session_state.is_monitoring:
                    # 检查最后一条记录的时间
                    last_time = latest["时间"]
                    st.success(f"✅ 在线\n最后心跳: {last_time}")
                else:
                    st.warning("⏸️ 监测已暂停")
            else:
                st.info("暂无数据")
        
        # 心跳频率分析
        if not df.empty:
            st.subheader("📊 心跳频率分析")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总心跳数", len(df))
            with col2:
                st.metric("最新序号", df["序号"].iloc[-1] if not df.empty else 0)
            with col3:
                st.metric("数据完整性", "100%" if len(df) == df["序号"].iloc[-1] else "检查中")
    
    with tab2:
        st.subheader("📋 心跳数据日志")
        
        df = monitor.get_dataframe()
        if not df.empty:
            # 反转显示，最新的在上面
            display_df = df[["序号", "时间", "完整时间戳", "状态"]].copy()
            display_df = display_df.iloc[::-1].reset_index(drop=True)
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400,
                column_config={
                    "序号": st.column_config.NumberColumn("序号", width="small"),
                    "时间": st.column_config.TextColumn("时间", width="small"),
                    "完整时间戳": st.column_config.TextColumn("完整时间戳", width="medium"),
                    "状态": st.column_config.TextColumn("状态", width="small")
                }
            )
        else:
            st.info("暂无心跳数据")
    
    with tab3:
        st.subheader("⚠️ 告警记录")
        
        alert_df = monitor.get_alert_dataframe()
        if not alert_df.empty:
            # 反转显示
            alert_df = alert_df.iloc[::-1].reset_index(drop=True)
            
            st.dataframe(
                alert_df,
                use_container_width=True,
                height=300,
                column_config={
                    "时间": st.column_config.TextColumn("告警时间", width="small"),
                    "警告": st.column_config.TextColumn("告警内容", width="large")
                }
            )
            
            # 如果有告警，显示红色警告框
            if len(alert_df) > 0:
                latest_alert = alert_df.iloc[0]
                st.error(f"🚨 最新告警 [{latest_alert['时间']}]: {latest_alert['警告']}")
        else:
            st.success("✅ 暂无告警记录，系统运行正常")
    
    # 自动刷新
    if st.session_state.is_monitoring:
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__":
    main()
