"""
Datadeal GUI - Streamlit界面
用于霍尔效应和电阻数据处理

运行方式: streamlit run datadeal_app.py
"""

import streamlit as st
import os
import sys
import shutil
import zipfile
import io
import json
import traceback
from io import StringIO
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# 设置工作目录并导入datadeal
script_dir = Path(__file__).parent.resolve()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

# 导入datadeal模块
import datadeal

# ============== Log Capture ==============

@contextmanager
def capture_stdout():
    """捕获stdout输出的上下文管理器"""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        yield sys.stdout
    finally:
        sys.stdout = old_stdout


# 配置文件路径
CONFIG_FILE = os.path.join(datadeal.workdir, "datadeal_config.json")

# 页面配置
st.set_page_config(
    page_title="Datadeal - 数据处理工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .step-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .warning-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stButton>button {
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background: linear-gradient(120deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)

# ============== Config File Functions ==============

def save_config(config_data):
    """保存配置到JSON文件"""
    config_data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    return True

def load_config():
    """加载上次的配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def get_default_config():
    """获取默认配置"""
    return {
        'interval_input': '14:20',
        'length': 1.0,
        'width': 1.0,
        'height': 1.0,
        'data_type': 'R',
        'run_twoband': False,
        'run_rh': True,
        'rh_low': 0.0,
        'rh_high': 14.0,
        'data_file': '',
        'last_updated': ''
    }

# 初始化session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False
if 'fitting_done' not in st.session_state:
    st.session_state.fitting_done = False
if 'needs_type_input' not in st.session_state:
    st.session_state.needs_type_input = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'config_loaded' not in st.session_state:
    st.session_state.config_loaded = False
if 'log_output' not in st.session_state:
    st.session_state.log_output = ""

def add_message(msg, msg_type="info"):
    """添加消息到消息列表"""
    st.session_state.messages.append({"text": msg, "type": msg_type})

def show_messages():
    """显示所有消息"""
    for msg in st.session_state.messages:
        if msg["type"] == "error":
            st.error(msg["text"])
        elif msg["type"] == "warning":
            st.warning(msg["text"])
        elif msg["type"] == "success":
            st.success(msg["text"])
        else:
            st.info(msg["text"])

def reset_state():
    """重置状态"""
    st.session_state.step = 1
    st.session_state.processing_done = False
    st.session_state.fitting_done = False
    st.session_state.needs_type_input = False
    st.session_state.messages = []
    st.session_state.config_loaded = False

def get_dat_files_in_workdir():
    """获取工作目录下的所有.dat文件"""
    return [f for f in os.listdir(datadeal.workdir) if f.endswith('.dat')]

def clear_dat_files():
    """清除工作目录下的所有.dat文件"""
    dat_files = get_dat_files_in_workdir()
    for f in dat_files:
        try:
            os.remove(os.path.join(datadeal.workdir, f))
        except Exception as e:
            pass
    return len(dat_files)

def clear_data_folder():
    """清除data文件夹"""
    if os.path.exists(datadeal.workdirdata):
        shutil.rmtree(datadeal.workdirdata)
        return True
    return False

def clear_fit_folder():
    """清除fit文件夹"""
    if os.path.exists(datadeal.workdirfit):
        shutil.rmtree(datadeal.workdirfit)
        return True
    return False

def create_results_zip():
    """创建包含data/, fit/, alldata.png, config.json的zip文件"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 添加data文件夹
        if os.path.exists(datadeal.workdirdata):
            for root, dirs, files in os.walk(datadeal.workdirdata):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('data', os.path.relpath(file_path, datadeal.workdirdata))
                    zip_file.write(file_path, arcname)
        
        # 添加fit文件夹
        if os.path.exists(datadeal.workdirfit):
            for root, dirs, files in os.walk(datadeal.workdirfit):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('fit', os.path.relpath(file_path, datadeal.workdirfit))
                    zip_file.write(file_path, arcname)
        
        # 添加alldata.png
        alldata_path = os.path.join(datadeal.workdir, "alldata.png")
        if os.path.exists(alldata_path):
            zip_file.write(alldata_path, "alldata.png")
        
        # 添加配置文件
        if os.path.exists(CONFIG_FILE):
            zip_file.write(CONFIG_FILE, "datadeal_config.json")
    
    # 返回bytes而不是BytesIO对象
    return zip_buffer.getvalue()


# 主标题
st.markdown('<h1 class="main-header">📊 Datadeal 数据处理工具</h1>', unsafe_allow_html=True)
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.header("📋 处理状态")
    
    # 显示当前步骤
    steps = [
        ("1️⃣", "检查文件夹", st.session_state.step >= 1),
        ("2️⃣", "配置参数", st.session_state.step >= 2),
        ("3️⃣", "数据处理", st.session_state.processing_done),
        ("4️⃣", "拟合分析", st.session_state.fitting_done),
    ]
    
    for icon, name, done in steps:
        if done:
            st.success(f"{icon} {name} ✅")
        else:
            st.info(f"{icon} {name}")
    
    st.markdown("---")
    
    # 文件管理区域
    st.header("📁 文件管理")
    
    # 上传数据文件
    st.markdown("### 📤 上传数据文件")
    uploaded_file = st.file_uploader(
        "选择.dat文件上传",
        type=['dat'],
        help="上传原始数据文件到工作目录",
        key="dat_uploader"
    )
    
    if uploaded_file is not None:
        # 检查是否是新上传的文件
        uploaded_name = uploaded_file.name
        if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != uploaded_name:
            # 保存上传的文件
            save_path = os.path.join(datadeal.workdir, uploaded_name)
            with open(save_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            st.session_state.last_uploaded_file = uploaded_name
            st.success(f"✅ 已上传: {uploaded_name}")
            st.rerun()
        else:
            st.success(f"✅ 当前文件: {uploaded_name}")
    
    # 显示当前.dat文件
    dat_files = get_dat_files_in_workdir()
    if dat_files:
        st.markdown("### 📄 当前数据文件")
        for f in dat_files:
            st.text(f"  📄 {f}")
    
    st.markdown("---")
    
    # 清理按钮
    st.markdown("### 🗑️ 清理选项")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("清除.dat", use_container_width=True, help="删除工作目录下所有.dat文件"):
            count = clear_dat_files()
            st.success(f"已删除 {count} 个文件")
            st.rerun()
    with col_c2:
        if st.button("清除data", use_container_width=True, help="删除data文件夹"):
            if clear_data_folder():
                st.success("data已清除")
            st.rerun()
    
    if st.button("🗑️ 清除fit文件夹", use_container_width=True):
        if clear_fit_folder():
            st.success("fit已清除")
        datadeal.ensure_folders()
        st.rerun()
    
    if st.button("🔄 重新开始", use_container_width=True):
        reset_state()
        st.rerun()
    
    st.markdown("---")
    
    # 下载结果
    st.markdown("### 📥 下载结果")
    
    # 检查是否有可下载的内容
    has_data = os.path.exists(datadeal.workdirdata) and os.listdir(datadeal.workdirdata)
    has_fit = os.path.exists(datadeal.workdirfit) and os.listdir(datadeal.workdirfit)
    has_alldata = os.path.exists(os.path.join(datadeal.workdir, "alldata.png"))
    
    if has_data or has_fit or has_alldata:
        # 使用按钮触发生成zip，避免动态文件名问题
        if st.button("🔄 准备下载文件", use_container_width=True):
            st.session_state.zip_data = create_results_zip()
            st.session_state.zip_filename = f"datadeal_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            st.session_state.zip_ready = True
        
        if st.session_state.get('zip_ready', False):
            st.download_button(
                label="📦 点击下载 (ZIP)",
                data=st.session_state.zip_data,
                file_name=st.session_state.zip_filename,
                mime="application/zip",
                use_container_width=True
            )
            st.success(f"✅ 文件已准备: {st.session_state.zip_filename}")
        
        # 显示包含内容
        contents = []
        if has_data:
            contents.append("data/")
        if has_fit:
            contents.append("fit/")
        if has_alldata:
            contents.append("alldata.png")
        st.caption(f"将包含: {', '.join(contents)}")
    else:
        st.info("暂无可下载的结果")
    
    st.markdown("---")
    st.caption("by fuyang ヽ(°∀°)ﾉ")

# 主内容区
col1, col2 = st.columns([2, 1])

with col1:
    # Step 1: 检查文件夹状态
    if st.session_state.step == 1:
        st.subheader("📁 Step 1: 检查工作目录")
        
        data_exists = datadeal.check_data_folder()
        fit_exists = datadeal.check_fit_folder()
        
        if data_exists:
            st.warning("⚠️ 已有data文件夹，如需处理原始数据请删除该文件夹重新运行程序。")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📈 跳过处理，直接拟合", use_container_width=True):
                    st.session_state.step = 4
                    st.session_state.processing_done = True
                    st.rerun()
            with col_b:
                if st.button("🗑️ 清除data文件夹并继续", use_container_width=True):
                    clear_data_folder()
                    datadeal.ensure_folders()
                    add_message("data文件夹已清除", "success")
                    st.rerun()
        else:
            st.success("✅ 工作目录就绪，可以开始处理数据")
            
            # 检查dat文件
            dat_files = datadeal.get_data_files()
            
            if len(dat_files) == 0:
                st.error("❌ 未找到.dat数据文件")
                st.info("💡 请使用左侧边栏的「上传数据文件」功能上传数据")
            elif len(dat_files) > 1:
                st.warning(f"⚠️ 发现多个.dat文件 ({len(dat_files)}个)，请只保留一个")
                for f in dat_files:
                    st.text(f"  📄 {os.path.basename(f)}")
                st.info("💡 使用左侧边栏的「清除.dat」可删除所有文件后重新上传")
            else:
                st.info(f"📄 数据文件: **{os.path.basename(dat_files[0])}**")
                
                if st.button("➡️ 下一步: 配置参数", use_container_width=True):
                    datadeal.ensure_folders()
                    st.session_state.step = 2
                    st.session_state.selected_file = dat_files[0]
                    st.rerun()
        
        show_messages()
    
    # Step 2: 配置参数
    elif st.session_state.step == 2:
        st.subheader("⚙️ Step 2: 配置处理参数")
        
        # 加载上次配置
        saved_config = load_config()
        if saved_config and not st.session_state.config_loaded:
            st.session_state.config_loaded = True
            st.info(f"💾 发现上次配置 (更新于: {saved_config.get('last_updated', '未知')})")
        
        st.info(f"📄 数据文件: **{os.path.basename(st.session_state.get('selected_file', ''))}**")
        
        # 加载配置按钮 - 直接设置widget的session_state值
        if saved_config:
            if st.button("📂 加载上次配置", use_container_width=True):
                # 直接设置各个widget的key值
                st.session_state.interval_input_field = saved_config.get('interval_input', '14:20')
                st.session_state.length_field = float(saved_config.get('length', 1.0))
                st.session_state.width_field = float(saved_config.get('width', 1.0))
                st.session_state.height_field = float(saved_config.get('height', 1.0))
                st.success("✅ 配置已加载！")
                st.rerun()
        
        # 初始化widget默认值（如果还没有设置）
        # 优先使用保存的值（从Step 3返回时）
        if 'interval_input_field' not in st.session_state:
            st.session_state.interval_input_field = st.session_state.get('saved_interval', '14:20')
        if 'length_field' not in st.session_state:
            st.session_state.length_field = st.session_state.get('saved_length', 1.0)
        if 'width_field' not in st.session_state:
            st.session_state.width_field = st.session_state.get('saved_width', 1.0)
        if 'height_field' not in st.session_state:
            st.session_state.height_field = st.session_state.get('saved_height', 1.0)
        
        # 内插分段
        st.markdown("### 📐 内插分段设置")
        interval_input = st.text_input(
            "格式: '范围:间隔'，多个分段用逗号隔开, 例如 '4:20' 表示在0-4T范围内使用20Oe的间隔",
            placeholder="示例: 4:20, 14:100",
            help="例如 '4:20' 表示在0-4T范围内使用20Oe的间隔",
            key="interval_input_field"
        )
        
        # 解析并显示
        intervals = datadeal.parse_intervals(interval_input)
        st.caption(f"解析结果: {intervals}")
        
        # 样品尺寸
        st.markdown("### 📏 样品尺寸 (cm)")
        col_l, col_w, col_h = st.columns(3)
        with col_l:
            length = st.number_input("长度 L(cm)", min_value=0.000001, format="%.6f", key="length_field")
        with col_w:
            width = st.number_input("宽度 W(cm)", min_value=0.000001, format="%.6f", key="width_field")
        with col_h:
            height = st.number_input("高度 H(cm)", min_value=0.000001, format="%.6f", key="height_field")
        
        abc = f"{length},{width},{height}"
        
        if length == 1.0 and width == 1.0 and height == 1.0:
            st.caption("⚡ 尺寸全为1时，输出为电阻(Ω)而非电阻率(Ω·cm)")
        else:
            st.caption(f"📐 将输出电阻率(Ω·cm)，abc = {abc}")
        
        # 数据类型选择（如果需要）
        if st.session_state.needs_type_input:
            st.markdown("### 📊 数据类型选择")
            st.warning("⚠️ 检测到只有三列数据，请选择数据类型")
            data_type_options = ["R (电阻)", "H (霍尔)"]
            data_type = st.radio(
                "选择数据类型:",
                data_type_options,
                horizontal=True
            )
            st.session_state.data_type = "R" if "R" in data_type else "H"
        
        st.markdown("---")
        
        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("⬅️ 返回", use_container_width=True):
                st.session_state.step = 1
                st.rerun()
        with col_next:
            if st.button("🚀 开始处理", use_container_width=True, type="primary"):
                st.session_state.intervals = intervals
                st.session_state.abc = abc
                
                # 保存当前输入值到session_state（用于在返回时恢复）
                st.session_state.saved_interval = interval_input
                st.session_state.saved_length = length
                st.session_state.saved_width = width
                st.session_state.saved_height = height
                
                # 保存配置
                config_to_save = {
                    'interval_input': interval_input,
                    'length': length,
                    'width': width,
                    'height': height,
                    'data_type': st.session_state.get('data_type', 'R'),
                    'data_file': os.path.basename(st.session_state.get('selected_file', ''))
                }
                save_config(config_to_save)
                
                st.session_state.step = 3
                st.rerun()
    
    # Step 3: 数据处理
    elif st.session_state.step == 3:
        st.subheader("⚙️ Step 3: 数据处理中...")
        
        with st.spinner("正在处理数据，请稍候..."):
            try:
                data_type = st.session_state.get('data_type', None)
                
                # 捕获stdout输出到日志
                with capture_stdout() as captured:
                    success, msg, needs_type = datadeal.deal_with_params(
                        st.session_state.selected_file,
                        st.session_state.intervals,
                        st.session_state.abc,
                        data_type=data_type,
                        show_plot=False
                    )
                
                # 追加日志
                log_content = captured.getvalue()
                if log_content:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    st.session_state.log_output += f"\n[{timestamp}] === 数据处理 ===\n{log_content}"
                
                if needs_type:
                    st.session_state.needs_type_input = True
                    # 保留当前输入的值，不要重置
                    # 这些值已经在 session_state 中了，通过 key 参数
                    st.session_state.step = 2
                    st.rerun()
                elif success:
                    st.session_state.processing_done = True
                    add_message(msg, "success")
                    st.session_state.step = 4
                    st.rerun()
                else:
                    add_message(msg, "error")
                    st.session_state.step = 2
                    st.rerun()
            except Exception as e:
                error_details = traceback.format_exc()
                add_message(f"处理出错: {e}\n\n详细信息:\n{error_details}", "error")
                # 同时输出到日志区域
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.log_output += f"\n[{timestamp}] === 错误 ===\n{error_details}"
                st.session_state.step = 2
                st.rerun()
    
    # Step 4: 拟合
    elif st.session_state.step == 4:
        st.subheader("📈 Step 4: 数据拟合")
        
        if st.session_state.processing_done:
            st.success("✅ 数据处理已完成")
        
        fit_exists = datadeal.check_fit_folder()
        if fit_exists:
            st.warning("⚠️ fit文件夹已有数据，如需重新分析请删除fit文件夹")
            if st.button("🗑️ 清除fit文件夹"):
                clear_fit_folder()
                datadeal.ensure_folders()
                add_message("fit文件夹已清除", "success")
                st.rerun()
        
        # 加载配置
        saved_config = load_config()
        default_config = get_default_config()
        if saved_config:
            default_config.update(saved_config)
        
        st.markdown("### 🔬 拟合选项")
        
        # 双带拟合
        run_twoband = st.checkbox("执行双带拟合", value=default_config.get('run_twoband', False), key="run_twoband_cb")
        
        if datadeal.loop:
            st.warning("⚠️ 检测到loop数据，不建议使用双带拟合")
        
        # RH拟合
        run_rh = st.checkbox("执行RH线性拟合", value=default_config.get('run_rh', True), key="run_rh_cb")
        
        if run_rh:
            st.markdown("#### RH拟合范围")
            col_low, col_high = st.columns(2)
            with col_low:
                rh_low = st.number_input("下限 (T)", value=float(default_config.get('rh_low', 0.0)), min_value=0.0, key="rh_low_field")
            with col_high:
                rh_high = st.number_input("上限 (T)", value=float(default_config.get('rh_high', 14.0)), min_value=0.0, key="rh_high_field")
        else:
            rh_low, rh_high = 0.0, 14.0
        
        st.markdown("---")
        
        if st.button("🚀 开始拟合", use_container_width=True, type="primary"):
            # 保存拟合配置
            config_to_update = load_config() or get_default_config()
            config_to_update.update({
                'run_twoband': run_twoband,
                'run_rh': run_rh,
                'rh_low': rh_low,
                'rh_high': rh_high
            })
            save_config(config_to_update)
            
            with st.spinner("正在进行拟合分析..."):
                results = []
                
                # 双带拟合
                if run_twoband:
                    with capture_stdout() as captured:
                        success, msg, files = datadeal.fitprocess_with_params(run_fit=True)
                    log_content = captured.getvalue()
                    if log_content:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.log_output += f"\n[{timestamp}] === 双带拟合 ===\n{log_content}"
                    results.append(("双带拟合", success, msg, files))
                
                # RH拟合
                if run_rh:
                    with capture_stdout() as captured:
                        success, msg, files = datadeal.fitRHprocess_with_params(
                            run_fit=True, 
                            fit_range=(rh_low, rh_high)
                        )
                    log_content = captured.getvalue()
                    if log_content:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        st.session_state.log_output += f"\n[{timestamp}] === RH拟合 ===\n{log_content}"
                    results.append(("RH拟合", success, msg, files))
                
                # 显示结果
                for name, success, msg, files in results:
                    if success:
                        add_message(f"{name}: {msg}", "success")
                    else:
                        add_message(f"{name}: {msg}", "error")
                
                st.session_state.fitting_done = True
                st.session_state.fit_results = results
                st.rerun()
        
        show_messages()
        
        # 显示结果
        if st.session_state.fitting_done and hasattr(st.session_state, 'fit_results'):
            st.markdown("---")
            st.subheader("📊 拟合结果")
            
            for name, success, msg, files in st.session_state.fit_results:
                if success and files:
                    with st.expander(f"📈 {name} 图像 ({len(files)}个)", expanded=True):
                        for f in files:
                            if os.path.exists(f):
                                st.image(f, caption=os.path.basename(f))
            
            # 完成提示
            st.markdown("---")
            st.success("🎉 处理完成！使用左侧边栏的「下载结果」按钮可打包下载所有结果。")

with col2:
    # 右侧显示日志和图像
    st.subheader("📋 处理日志")
    
    # 显示日志输出
    if st.session_state.log_output:
        st.text_area(
            "程序输出",
            value=st.session_state.log_output,
            height=300,
            key="log_display",
            disabled=True
        )
    else:
        st.info("暂无日志输出")
    
    # 清除日志按钮
    if st.session_state.log_output:
        if st.button("🗑️ 清除日志", use_container_width=True):
            st.session_state.log_output = ""
            st.rerun()
    
    st.markdown("---")
    st.subheader("🖼️ 生成图像")
    
    # 显示alldata.png（如果存在）
    alldata_path = os.path.join(datadeal.workdir, "alldata.png")
    if os.path.exists(alldata_path):
        st.image(alldata_path, caption="alldata.png - 数据总览")
    
    # 显示fit文件夹中的图像
    if os.path.exists(datadeal.workdirfit):
        png_files = [f for f in os.listdir(datadeal.workdirfit) if f.endswith('.png')]
        if png_files:
            st.markdown("### 拟合图像")
            for png in sorted(png_files)[:5]:  # 限制显示数量
                img_path = os.path.join(datadeal.workdirfit, png)
                with st.expander(png):
                    st.image(img_path)
            if len(png_files) > 5:
                st.caption(f"还有 {len(png_files) - 5} 个图像未显示...")

