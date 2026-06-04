"""
无人机心跳监测可视化系统
稳定版本 - 确保在 Streamlit Cloud 上正常运行
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
import datetime
from typing import Dict, List
from collections import deque

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 心跳数据管理类 ====================

class HeartbeatManager:
    """心跳数据管理器 - 简化版本，避免线程问题"""
    
    def __init__(self):
        self.heartbeat_data = []  # 存储心跳数据
        self.alerts = []  # 存储告警信息
        self.last_heartbeat_time = None
        self.sequence_counter = 0
        self.is_connected = False
        
    def add_heartbeat(self):
        """添加一个心跳包"""
        self.sequence_counter += 1
        current_time = datetime.datetime.now()
        
        heartbeat = {
            "序号": self.sequence_counter,
            "时间": current_time.strftime("%H:%M:%S"),
            "完整时间戳": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "状态": "在线"
        }
        
        self.heartbeat_data.append(heartbeat)
        
        # 只保留最近100条记录
        if len(self.heartbeat_data) > 100:
            self.heartbeat_data = self.heartbeat_data[-100:]
        
        # 更新最后心跳时间
        self.last_heartbeat_time = current_time
        self.is_connected = True
        
        return heartbeat
    
    def check_connection(self):
        """检查连接状态"""
        if self.last_heartbeat_time is not None:
            time_since_last = (datetime.datetime.now() - self.last_heartbeat_time).total_seconds()
            
            if time_since_last > 3 and self.is_connected:
                self.is_connected = False
                alert = {
                    "时间": datetime.datetime.now().strftime("%H:%M:%S"),
                    "警告": f"⚠️ 连接超时！已 {time_since_last:.1f} 秒未收到心跳包",
                    "类型": "超时告警"
                }
                self.alerts.append(alert)
                
                # 只保留最近20条告警
                if len(self.alerts) > 20:
                    self.alerts = self.alerts[-20:]
                
                return True
        return False
    
    def clear_data(self):
        """清除所有数据"""
        self.heartbeat_data = []
        self.alerts = []
        self.sequence_counter = 0
        self.last_heartbeat_time = None
        self.is_connected = False
    
    def get_dataframe(self):
        """获取数据框"""
        if self.heartbeat_data:
            df = pd.DataFrame(self.heartbeat_data)
            if not df.empty:
                df["显示序号"] = range(1, len(df) + 1)
            return df
        return pd.DataFrame()
    
    def get_alerts_dataframe(self):
        """获取告警数据框"""
        if self.alerts:
            return pd.DataFrame(self.alerts)
        return pd.DataFrame()


# ==================== 主应用 ====================

def init_session_state():
    """初始化会话状态"""
    if 'manager' not in st.session_state:
        st.session_state.manager = HeartbeatManager()
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False
    if 'auto_increment' not in st.session_state:
        st.session_state.auto_increment = False
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()


def main():
    # 页面配置
    st.set_page_config(
        page_title="无人机心跳监测系统",
        page_icon="🚁",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化
    init_session_state()
    
    # 标题
    st.title("🚁 无人机心跳监测可视化系统")
    st.markdown("---")
    
    # ==================== 侧边栏 ====================
    with st.sidebar:
        st.header("🎮 控制面板")
        
        # 控制按钮
        col1, col2 = st.columns(2)
        
        with col1:
            start_clicked = st.button("▶️ 启动监测", use_container_width=True, type="primary")
            if start_clicked:
                st.session_state.is_running = True
                st.session_state.auto_increment = True
                st.rerun()
        
        with col2:
            stop_clicked = st.button("⏹️ 停止监测", use_container_width=True)
            if stop_clicked:
                st.session_state.is_running = False
                st.session_state.auto_increment = False
                st.rerun()
        
        st.markdown("---")
        
        # 手动添加心跳按钮
        if st.button("💓 手动发送心跳", use_container_width=True):
            st.session_state.manager.add_heartbeat()
            st.rerun()
        
        # 清除数据按钮
        if st.button("🗑️ 清除所有数据", use_container_width=True):
            st.session_state.manager.clear_data()
            st.rerun()
        
        st.markdown("---")
        
        # 状态显示
        st.subheader("📡 系统状态")
        
        if st.session_state.is_running:
            st.success("🟢 自动监测运行中")
        else:
            st.info("🔵 手动模式")
        
        # 连接状态
        manager = st.session_state.manager
        if manager.last_heartbeat_time:
            time_since = (datetime.datetime.now() - manager.last_heartbeat_time).total_seconds()
            if time_since <= 3:
                st.success(f"✅ 连接正常\n最后心跳: {time_since:.1f}秒前")
            else:
                st.error(f"❌ 连接异常\n已断开: {time_since:.1f}秒")
        else:
            st.warning("⏳ 等待心跳...")
        
        st.markdown("---")
        
        # 配置信息
        st.subheader("⚙️ 系统配置")
        st.info("""
        - 📡 心跳频率: 1次/秒
        - ⏰ 超时阈值: 3秒
        - 💾 数据保留: 100条
        - 🚨 告警保留: 20条
        """)
        
        # 统计信息
        if manager.heartbeat_data:
            st.markdown("---")
            st.subheader("📊 统计信息")
            st.metric("总心跳数", len(manager.heartbeat_data))
            st.metric("最新序号", manager.sequence_counter)
            st.metric("告警次数", len(manager.alerts))
    
    # ==================== 主内容区域 ====================
    
    # 自动心跳逻辑
    if st.session_state.auto_increment and st.session_state.is_running:
        current_time = time.time()
        # 每秒添加一个心跳
        if current_time - st.session_state.last_update >= 1.0:
            st.session_state.manager.add_heartbeat()
            st.session_state.last_update = current_time
            st.rerun()
    
    # 检查连接状态
    if st.session_state.manager.heartbeat_data:
        st.session_state.manager.check_connection()
    
    # 创建选项卡
    tab1, tab2, tab3 = st.tabs(["📊 实时监控", "📋 数据日志", "⚠️ 告警中心"])
    
    # Tab 1: 实时监控
    with tab1:
        st.subheader("📈 心跳序号变化趋势")
        
        df = st.session_state.manager.get_dataframe()
        
        if not df.empty:
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 折线图 - 心跳序号
            ax1.plot(df["显示序号"], df["序号"], 'b-o', linewidth=2, markersize=4, alpha=0.7)
            ax1.set_xlabel("心跳次数", fontsize=11)
            ax1.set_ylabel("心跳序号", fontsize=11)
            ax1.set_title("心跳序号变化趋势", fontsize=13, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.set_facecolor('#f8f9fa')
            
            # 标注最后一点
            last_x = df["显示序号"].iloc[-1]
            last_y = df["序号"].iloc[-1]
            ax1.annotate(f'最新: {last_y}', 
                        xy=(last_x, last_y), 
                        xytext=(10, 10), 
                        textcoords='offset points',
                        fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
            
            # 柱状图 - 心跳频率（每10个一组）
            if len(df) >= 10:
                df['分组'] = (df['显示序号'] - 1) // 10
                freq_stats = df.groupby('分组').size().reset_index(name='计数')
                ax2.bar(freq_stats['分组'] * 10, freq_stats['计数'], width=8, alpha=0.7, color='green')
                ax2.set_xlabel("心跳次数区间", fontsize=11)
                ax2.set_ylabel("心跳数量", fontsize=11)
                ax2.set_title("心跳分布统计（每10次一组）", fontsize=13, fontweight='bold')
                ax2.grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            
            # 实时指标卡片
            st.subheader("📊 实时指标")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总心跳数", len(df), delta=None)
            with col2:
                st.metric("当前序号", df["序号"].iloc[-1], 
                         delta=df["序号"].iloc[-1] - df["序号"].iloc[-2] if len(df) > 1 else 0)
            with col3:
                last_time = df["时间"].iloc[-1]
                st.metric("最后心跳时间", last_time)
            with col4:
                # 计算心跳频率
                if len(df) > 1:
                    time_diff = (datetime.datetime.strptime(df["完整时间戳"].iloc[-1], "%Y-%m-%d %H:%M:%S") -
                               datetime.datetime.strptime(df["完整时间戳"].iloc[-2], "%Y-%m-%d %H:%M:%S")).total_seconds()
                    freq = f"{1/time_diff:.1f} Hz" if time_diff > 0 else "N/A"
                    st.metric("心跳频率", freq)
                else:
                    st.metric("心跳频率", "等待数据")
        else:
            st.info("📭 暂无数据，请点击「启动监测」或「手动发送心跳」开始")
            
            # 显示占位图
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.text(0.5, 0.5, '等待数据...\n点击左侧按钮开始监测', 
                   ha='center', va='center', fontsize=16, color='gray')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            st.pyplot(fig)
            plt.close(fig)
    
    # Tab 2: 数据日志
    with tab2:
        st.subheader("📋 详细心跳记录")
        
        df = st.session_state.manager.get_dataframe()
        if not df.empty:
            # 添加筛选器
            col1, col2 = st.columns([1, 3])
            with col1:
                show_count = st.selectbox("显示条数", ["全部", "最近20条", "最近50条"])
            
            # 根据选择显示数据
            if show_count == "最近20条":
                display_df = df.tail(20).iloc[::-1]
            elif show_count == "最近50条":
                display_df = df.tail(50).iloc[::-1]
            else:
                display_df = df.iloc[::-1]
            
            # 显示数据表
            st.dataframe(
                display_df[["序号", "时间", "完整时间戳", "状态"]],
                use_container_width=True,
                height=400,
                column_config={
                    "序号": st.column_config.NumberColumn("序号", width="small"),
                    "时间": st.column_config.TextColumn("时间", width="small"),
                    "完整时间戳": st.column_config.TextColumn("完整时间戳", width="medium"),
                    "状态": st.column_config.TextColumn("状态", width="small")
                }
            )
            
            # 下载按钮
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 下载数据为 CSV",
                data=csv,
                file_name=f"heartbeat_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("暂无心跳记录")
    
    # Tab 3: 告警中心
    with tab3:
        st.subheader("⚠️ 告警记录")
        
        alert_df = st.session_state.manager.get_alerts_dataframe()
        
        if not alert_df.empty:
            # 告警统计
            st.warning(f"🚨 当前共有 {len(alert_df)} 条告警记录")
            
            # 显示告警列表
            for idx, alert in alert_df.iterrows():
                if alert["类型"] == "超时告警":
                    st.error(f"🕒 {alert['时间']} - {alert['警告']}")
                else:
                    st.warning(f"🕒 {alert['时间']} - {alert['警告']}")
            
            # 清空告警按钮
            if st.button("清空告警记录", use_container_width=True):
                st.session_state.manager.alerts = []
                st.rerun()
        else:
            st.success("✅ 暂无告警记录，系统运行正常")
            st.balloons()
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        🚁 无人机心跳监测系统 | 心跳频率: 1次/秒 | 超时阈值: 3秒
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
