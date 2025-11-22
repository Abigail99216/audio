import gradio as gr
import logging
import pandas as pd
import os
import time
import json
from datetime import datetime
from simple_multiprocess_manager import get_simple_scheduler, SimpleTaskScheduler

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('experiment_cheat_multiprocess.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AsyncCheatExperimentFunctions:
    def __init__(self):
        self.scripts_file = "scripts.xlsx"
        self.scripts_data = None
        self.current_case = None
        self._load_scripts()
        
        # 定义固定音频文件路径
        self.audio_files = {
            "patient1": "audio/吴女士.mp3",
            "patient2": "audio/王女士.mp3", 
            "patient3": "audio/张先生.mp3"
        }
        
        # 创建音频目录（如果不存在）
        os.makedirs("audio", exist_ok=True)
        
        # 初始化多进程调度器（延迟初始化）
        self.scheduler = None
        
        logger.info("AsyncCheatExperimentFunctions 初始化完成")
    
    def _get_scheduler(self):
        """获取调度器实例（延迟初始化）"""
        if self.scheduler is None:
            try:
                self.scheduler = get_simple_scheduler()
                logger.info("简单多进程调度器初始化成功")
            except Exception as e:
                logger.error(f"简单多进程调度器初始化失败: {str(e)}")
                self.scheduler = None
        return self.scheduler
    
    def _load_scripts(self):
        """加载Excel脚本文件"""
        try:
            if os.path.exists(self.scripts_file):
                self.scripts_data = pd.read_excel(self.scripts_file)
                logger.info(f"成功加载脚本文件，包含 {len(self.scripts_data)} 个病例")
                logger.info(f"列名: {self.scripts_data.columns.tolist()}")
            else:
                logger.error(f"脚本文件不存在: {self.scripts_file}")
                self.scripts_data = None
        except Exception as e:
            logger.error(f"加载脚本文件失败: {str(e)}")
            self.scripts_data = None
    
    def get_case_data(self, case_name):
        """根据病例名称获取数据"""
        if self.scripts_data is None:
            return None
        
        try:
            case_data = self.scripts_data[self.scripts_data['case'] == case_name]
            if not case_data.empty:
                return case_data.iloc[0].to_dict()
            else:
                logger.warning(f"未找到病例: {case_name}")
                return None
        except Exception as e:
            logger.error(f"获取病例数据失败: {str(e)}")
            return None
    
    def load_patient_audio(self, patient_id):
        """加载指定病人的音频文件"""
        try:
            if patient_id not in self.audio_files:
                logger.error(f"无效的病人ID: {patient_id}")
                return None
            
            audio_path = self.audio_files[patient_id]
            
            # 检查音频文件是否存在
            if not os.path.exists(audio_path):
                logger.warning(f"音频文件不存在: {audio_path}")
                return None
            
            logger.info(f"加载音频文件: {audio_path}")
            return audio_path
            
        except Exception as e:
            logger.error(f"加载音频文件失败: {str(e)}")
            return None
    
    def get_audio_status(self, patient_id):
        """获取音频文件状态"""
        try:
            if patient_id not in self.audio_files:
                return f"无效的病人ID: {patient_id}"
            
            audio_path = self.audio_files[patient_id]
            if os.path.exists(audio_path):
                return f"音频文件已加载: {patient_id}"
            else:
                return f"音频文件不存在: {audio_path}"
                
        except Exception as e:
            return f"检查音频文件状态失败: {str(e)}"
    
    def transcribe_speech(self, audio_file):
        """模拟语音转录，返回预准备的对话文本"""
        try:
            if audio_file is None:
                return "请先选择音频文件"
            
            # 根据音频文件名确定病例
            audio_filename = os.path.basename(audio_file)
            if "吴女士" in audio_filename:
                case_name = "吴女士"
            elif "王女士" in audio_filename:
                case_name = "王女士"
            elif "张先生" in audio_filename:
                case_name = "张先生"
            else:
                return "无法识别音频文件对应的病例"
            
            # 获取病例数据
            case_data = self.get_case_data(case_name)
            if case_data is None:
                return f"未找到病例 {case_name} 的数据"
            
            # 返回对话文本
            dialogue = case_data.get('dialogue', '对话内容未找到')
            self.current_case = case_name
            
            logger.info(f"为病例 {case_name} 返回预准备的对话文本")
            return f"=== {case_name} 的对话记录 ===\n\n{dialogue}"
            
        except Exception as e:
            logger.error(f"转录失败: {str(e)}")
            return f"转录失败: {str(e)}"
    
    def async_transcribe_speech(self, audio_file, uid):
        """异步语音转录功能"""
        try:
            if audio_file is None:
                return "请先选择音频文件"
            
            # 获取调度器实例
            scheduler = self._get_scheduler()
            if scheduler is None:
                logger.warning("多进程调度器不可用，使用同步转录")
                return self.transcribe_speech(audio_file)
            
            # 提交任务到多进程调度器
            task_id = scheduler.submit_task("speech", audio_file, uid)
            logger.info(f"语音转录任务已提交: {task_id}")
            
            # 等待任务完成并获取结果
            max_wait_time = 30  # 最多等待30秒
            result = scheduler.get_task_result(task_id, timeout=max_wait_time)
            if result:
                if result.status == 'success':
                    logger.info(f"转录任务完成: {task_id}")
                    # 根据音频文件名更新当前病例
                    audio_filename = os.path.basename(audio_file)
                    if "吴女士" in audio_filename:
                        self.current_case = "吴女士"
                    elif "王女士" in audio_filename:
                        self.current_case = "王女士"
                    elif "张先生" in audio_filename:
                        self.current_case = "张先生"
                    logger.info(f"更新当前病例为: {self.current_case}")
                    return result.result
                else:
                    logger.error(f"转录任务失败: {result.result}")
                    return f"转录失败: {result.result}"
            
            # 超时，返回任务ID信息
            logger.warning(f"转录任务等待超时: {task_id}")
            return f"语音转录任务已提交，任务ID: {task_id}\n任务处理时间较长，请稍后再试..."
            
        except Exception as e:
            logger.error(f"异步转录失败: {str(e)}")
            return f"异步转录失败: {str(e)}"
    
    def generate_medical_record(self, transcription):
        """生成病历，返回预准备的EHR文本"""
        try:
            if not self.current_case:
                return "请先进行语音转录"
            
            # 获取病例数据
            case_data = self.get_case_data(self.current_case)
            if case_data is None:
                return f"未找到病例 {self.current_case} 的数据"
            
            # 返回EHR文本
            ehr = case_data.get('EHR', '电子病历未找到')
            
            logger.info(f"为病例 {self.current_case} 生成预准备的电子病历")
            return f"=== {self.current_case} 的电子病历 ===\n\n{transcription}\n\n=== 生成的电子病历 ===\n\n{ehr}"
            
        except Exception as e:
            logger.error(f"生成病历失败: {str(e)}")
            return f"生成病历失败: {str(e)}"
    
    def generate_medical_reasoning(self, text):
        """生成医疗推理，返回预准备的推理文本"""
        try:
            if not self.current_case:
                return "请先选择病例"
            
            # 获取病例数据
            case_data = self.get_case_data(self.current_case)
            if case_data is None:
                return f"未找到病例 {self.current_case} 的数据"
            
            # 返回推理文本
            reasoning = case_data.get('reasoning', '推理内容未找到')
            
            logger.info(f"为病例 {self.current_case} 生成预准备的医疗推理")
            return f"=== {self.current_case} 的医疗推理 ===\n\n{reasoning}"
            
        except Exception as e:
            logger.error(f"生成医疗推理失败: {str(e)}")
            return f"生成医疗推理失败: {str(e)}"
    
    def async_medical_reasoning(self, text, uid):
        """异步医疗推理功能"""
        try:
            if not text:
                return "请输入要处理的文本"
            
            # 获取调度器实例
            scheduler = self._get_scheduler()
            if scheduler is None:
                logger.warning("多进程调度器不可用，使用同步推理")
                return self.generate_medical_reasoning(text)
            
            # 获取当前病例名称
            case_name = self.current_case
            if not case_name:
                # 尝试从文本中推断病例名称
                if "吴女士" in text:
                    case_name = "吴女士"
                elif "王女士" in text:
                    case_name = "王女士"
                elif "张先生" in text:
                    case_name = "张先生"
            
            # 提交任务到多进程调度器，传递病例名称
            task_id = scheduler.submit_task("reasoning", text, uid, case_name=case_name)
            logger.info(f"医疗推理任务已提交: {task_id}, 病例: {case_name}")
            
            # 等待任务完成并获取结果
            max_wait_time = 60  # 推理任务允许更长时间
            result = scheduler.get_task_result(task_id, timeout=max_wait_time)
            if result:
                if result.status == 'success':
                    logger.info(f"医疗推理任务完成: {task_id}")
                    return result.result
                else:
                    logger.error(f"医疗推理任务失败: {result.result}")
                    return f"医疗推理失败: {result.result}"
            
            logger.warning(f"医疗推理任务等待超时: {task_id}")
            return f"医疗推理任务已提交，任务ID: {task_id}\n请稍等片刻，推理结果需要较长时间处理..."
            
        except Exception as e:
            logger.error(f"异步医疗推理失败: {str(e)}")
            return f"异步医疗推理失败: {str(e)}"
    
    def get_case_conclusion(self):
        """获取病例结论"""
        try:
            if not self.current_case:
                return "请先选择病例"
            
            # 获取病例数据
            case_data = self.get_case_data(self.current_case)
            if case_data is None:
                return f"未找到病例 {self.current_case} 的数据"
            
            # 返回结论文本
            conclusion = case_data.get('conclusion', '结论未找到')
            
            logger.info(f"为病例 {self.current_case} 获取预准备的结论")
            return f"=== {self.current_case} 的诊断结论 ===\n\n{conclusion}"
            
        except Exception as e:
            logger.error(f"获取结论失败: {str(e)}")
            return f"获取结论失败: {str(e)}"
    
    def save_patient_record(self, name, patient_id, age, gender, chief_complaint, 
                          present_illness, past_history, personal_history, physical_exam, 
                          diagnosis, treatment_plan, uid=None):
        """保存病历记录"""
        try:
            if not name or not patient_id:
                return "患者姓名和ID不能为空"
            
            # 创建病历记录目录
            records_dir = "patient_records"
            os.makedirs(records_dir, exist_ok=True)
            
            # 生成病历文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{records_dir}/record_{patient_id}_{timestamp}.json"
            
            # 构建病历数据
            record_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "uid": str(uid) if uid else "",
                "patient_info": {
                    "name": name,
                    "patient_id": patient_id,
                    "age": age,
                    "gender": gender
                },
                "medical_record": {
                    "chief_complaint": chief_complaint,
                    "present_illness": present_illness,
                    "past_history": past_history,
                    "personal_history": personal_history,
                    "physical_exam": physical_exam,
                    "diagnosis": diagnosis,
                    "treatment_plan": treatment_plan
                }
            }
            
            # 保存为JSON文件
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"病历记录已保存: {filename}")
            return f"病历记录已保存: {filename}"
            
        except Exception as e:
            logger.error(f"保存病历记录失败: {str(e)}")
            return f"保存病历记录失败: {str(e)}"
    
    def get_system_status(self):
        """获取系统状态"""
        try:
            scheduler = self._get_scheduler()
            
            if scheduler is None:
                status = {
                    "调度器状态": "未初始化",
                    "待处理任务": 0,
                    "已完成任务": 0,
                    "工作进程数": 0,
                    "当前时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "备注": "多进程功能不可用，使用同步模式"
                }
            else:
                status = {
                    "调度器状态": "运行中",
                    "待处理任务": len(scheduler.pending_tasks),
                    "已完成任务": len(scheduler.completed_tasks),
                    "工作进程数": scheduler.num_workers,
                    "当前时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            status_text = "=== 系统状态 ===\n"
            for key, value in status.items():
                status_text += f"{key}: {value}\n"
            
            return status_text
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {str(e)}")
            return f"获取系统状态失败: {str(e)}"

# 定义功能访问权限
ACCESS_CODES = {
    "00": [],  # 对照组：无特殊功能
    "01": ["speech", "simple_record"],  # 第一组：语音转录+简单决策记录
    "02": ["speech"],  # 第二组：仅包含语音转录功能
    "03": ["reasoning", "reasoning_record"],  # 第三组：医疗推理+决策记录
    "04": ["reasoning"],  # 第四组：仅包含医疗推理功能
    "05": ["speech", "reasoning", "reasoning_record"],  # 第五组：语音转录+医疗推理+决策记录
    "06": ["speech", "reasoning"]  # 第六组：语音转录+医疗推理
}

def create_interface():
    """创建主界面"""
    with gr.Blocks(title="医疗实验系统 - 多进程版本") as interface:
        # 创建功能实例
        experiment = AsyncCheatExperimentFunctions()
        
        gr.Markdown("# 医疗实验系统")
        gr.Markdown("**请认真扮演医生角色，为病人提供专业的诊疗服务**")
        
        # 新增：全局状态保存当前uid
        current_uid = gr.State()
        
        # 欢迎弹窗
        with gr.Column(visible=True) as welcome_modal:
            with gr.Row():
                gr.HTML("""
                <div style="
                    position: fixed; 
                    top: 0; 
                    left: 0; 
                    width: 100%; 
                    height: 100%; 
                    background-color: rgba(0,0,0,0.5); 
                    z-index: 1000; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center;
                ">
                    <div style="
                        background: white; 
                        padding: 30px; 
                        border-radius: 10px; 
                        max-width: 600px; 
                        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                        text-align: center;
                    ">
                        <h2 style="color: #2c3e50; margin-bottom: 20px;">🏥 欢迎参加医疗AI辅助系统实验</h2>
                        
                        <div style="text-align: left; margin: 20px 0; line-height: 1.6;">
                            <h3 style="color: #34495e;">📋 实验目的</h3>
                            <p>本次实验旨在评估不同AI辅助功能对医生诊疗效率和决策质量的影响。</p>
                            
                            <h3 style="color: #34495e;">🩺 实验场景</h3>
                            <p><strong>您现在是一名门诊医生</strong>，需要为今天的三位病人进行接诊：</p>
                            <ul style="margin-left: 20px;">
                                <li><strong>吴女士、王女士、张先生</strong> - 每位病人都有相应的录音资料</li>
                                <li>请根据您的访问码使用相应的AI辅助功能</li>
                                <li>为每位病人完成诊疗过程并填写完整的电子病历</li>
                                <li>在使用AI推理功能时，请根据实际情况接受或拒绝AI的建议</li>
                            </ul>
                            
                            <h3 style="color: #34495e;">💡 操作提示</h3>
                            <p>• 右侧的病历填写模块始终可用，请为每位病人填写完整信息<br>
                            • 点击"吴女士/王女士/张先生"按钮可播放对应的录音资料<br>
                            • 根据您的组别，系统会提供不同的AI辅助功能<br>
                            • <strong>请认真扮演医生角色，为病人提供专业的诊疗服务</strong></p>
                        </div>
                        
                        <button id="close-welcome" onclick="document.getElementById('close-welcome-gradio').click()" style="
                            background: #3498db; 
                            color: white; 
                            border: none; 
                            padding: 12px 30px; 
                            border-radius: 5px; 
                            cursor: pointer; 
                            font-size: 16px;
                            margin-top: 20px;
                        ">开始实验</button>
                    </div>
                </div>
                
                <script>
                // 添加ESC键关闭弹窗功能
                document.addEventListener('keydown', function(event) {
                    if (event.key === 'Escape') {
                        document.getElementById('close-welcome-gradio').click();
                    }
                });
                </script>
                """)
            
            close_welcome_btn = gr.Button("开始实验", visible=False, elem_id="close-welcome-gradio")
        
        # 主要布局：左侧功能区，右侧病历填写区
        with gr.Row():
            # 左侧：所有功能组件
            with gr.Column(scale=2):
                with gr.Tabs() as tabs:
                    with gr.Tab("功能验证"):
                        with gr.Row():
                            access_code = gr.Textbox(
                                label="请输入访问码",
                                placeholder="请输入00-06之间的数字"
                            )
                            auth_status = gr.Textbox(
                                label="状态",
                                interactive=False
                            )
                    
                    # 音频播放界面（无转录功能的组别使用，放在最前面）
                    with gr.Tab("音频播放", visible=False) as audio_play_tab:
                        gr.Markdown("### 音频播放功能")
                        gr.Markdown("#### 双击选择病人音频")
                        with gr.Row():
                            patient1_btn_play = gr.Button("吴女士", variant="secondary")
                            patient2_btn_play = gr.Button("王女士", variant="secondary")
                            patient3_btn_play = gr.Button("张先生", variant="secondary")
                        
                        current_audio_play = gr.Audio(
                            label="当前音频",
                            type="filepath",
                            interactive=False
                        )
                        
                        gr.Markdown("*注：语音播放完毕后再点击开始转录*")
                    
                    with gr.Tab("语音转录", visible=False) as speech_tab:
                        gr.Markdown("### 语音转录与病历生成功能")
                        gr.Markdown("#### 双击选择病人音频")
                        with gr.Row():
                            patient1_btn = gr.Button("吴女士", variant="secondary")
                            patient2_btn = gr.Button("王女士", variant="secondary")
                            patient3_btn = gr.Button("张先生", variant="secondary")
                        
                        current_audio = gr.Audio(
                            label="当前音频",
                            type="filepath",
                            interactive=False
                        )
                        
                        gr.Markdown("*注：语音播放完毕后再点击开始转录*")
                        
                        with gr.Row():
                            transcribe_btn = gr.Button("开始转录", variant="primary")
                            generate_record_btn = gr.Button("生成病历", variant="secondary")
                        
                        transcription = gr.Textbox(
                            label="转录与病历结果",
                            lines=10,
                            interactive=False
                        )
                        copy_to_clipboard_btn = gr.Button("复制到剪贴板", variant="secondary")
                    
                    with gr.Tab("医疗推理", visible=False) as reasoning_tab:
                        gr.Markdown("### 医疗推理功能")
                        input_text = gr.Textbox(
                            label="输入文本",
                            placeholder="请输入要处理的文本...",
                            lines=5
                        )
                        generate_btn = gr.Button("生成推理", variant="primary")
                        output_text = gr.Textbox(
                            label="推理结果",
                            lines=5,
                            interactive=False
                        )
                        
                        # 01组专用：获取病例结论功能
                        with gr.Column(visible=False) as conclusion_section:
                            get_conclusion_btn = gr.Button("获取病例结论", variant="secondary")
                            conclusion_text = gr.Textbox(
                                label="病例结论",
                                lines=5,
                                interactive=False
                            )
                        
                        # 绑定结论部分的可见性（稍后定义）
                        pass
                    
                    with gr.Tab("决策记录", visible=False) as record_tab:
                        gr.Markdown("### 决策记录功能")
                        with gr.Row():
                            accept_btn = gr.Button("接受分析", variant="success")
                            reject_btn = gr.Button("拒绝分析", variant="stop")
                        
                        history = gr.Dataframe(
                            headers=['时间', '状态', '原因'],
                            label="决策历史",
                            value=[],
                            interactive=False
                        )
                        
                        with gr.Column(visible=False) as reject_box:
                            gr.Markdown("### 请选择拒绝原因")
                            reject_reasons = gr.Radio(
                                choices=["信息不足", "推理不准确", "需要更多分析"],
                                label=""
                            )
                            confirm_reject_btn = gr.Button("确认", variant="secondary")
                    
                    # 新增01组独立决策记录模块
                    with gr.Tab("01组决策记录", visible=False) as group_01_tab:
                        gr.Markdown("### 01组决策记录")
                        input_text_01 = gr.Textbox(
                            label="输入文本",
                            placeholder="请输入要处理的文本...",
                            lines=5
                        )
                        generate_btn_01 = gr.Button("生成结论", variant="primary")
                        output_text_01 = gr.Textbox(
                            label="结论",
                            lines=5,
                            interactive=False
                        )
                        accept_btn_01 = gr.Button("接受结论", variant="success")
                        reject_btn_01 = gr.Button("拒绝结论", variant="stop")
                        with gr.Column(visible=False) as reject_box_01:
                            gr.Markdown("### 请选择拒绝原因")
                            reject_reasons_01 = gr.Radio(
                                choices=["信息不足", "推理不准确", "需要更多分析"],
                                label=""
                            )
                            confirm_reject_btn_01 = gr.Button("确认", variant="secondary")
                    
                    # 系统状态选项卡
                    with gr.Tab("系统状态", visible=True) as status_tab:
                        gr.Markdown("### 系统状态监控")
                        status_btn = gr.Button("刷新状态", variant="secondary")
                        system_status = gr.Textbox(
                            label="系统状态",
                            lines=10,
                            interactive=False,
                            visible=False
                        )
            
            # 右侧：病历填写区
            with gr.Column(scale=1):
                gr.Markdown("### 📋 病历填写")
                with gr.Row():
                    patient_name = gr.Textbox(label="患者姓名", placeholder="请输入患者姓名")
                    patient_id = gr.Textbox(label="患者ID", placeholder="请输入患者ID")
                
                with gr.Row():
                    patient_age = gr.Number(label="年龄", minimum=0, maximum=150, value=0)
                    patient_gender = gr.Radio(choices=["男", "女"], label="性别", value=None)
                
                chief_complaint = gr.Textbox(label="主诉", placeholder="请输入主诉", lines=3)
                present_illness = gr.Textbox(label="现病史", placeholder="请输入现病史", lines=3)
                past_history = gr.Textbox(label="既往史", placeholder="请输入既往史", lines=2)
                personal_history = gr.Textbox(label="个人史", placeholder="请输入个人史", lines=2)
                physical_exam = gr.Textbox(label="体格检查", placeholder="请输入体格检查结果", lines=3)
                diagnosis = gr.Textbox(label="诊断", placeholder="请输入诊断", lines=2)
                treatment_plan = gr.Textbox(label="治疗方案", placeholder="请输入治疗方案", lines=3)
                
                with gr.Row():
                    save_record_btn = gr.Button("保存病历", variant="primary")
                    clear_record_btn = gr.Button("清空表单", variant="secondary")
                
                record_status = gr.Textbox(label="保存状态", interactive=False)
        
        # 功能处理函数
        def validate_access(code):
            """验证访问码并更新界面可见性"""
            try:
                logger.info(f"输入的访问码: {code}")
                if not code.isdigit() or len(code) < 2:
                    logger.warning(f"无效的访问码: {code}")
                    return [
                        "无效的访问码",
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        None,
                        False
                    ]
                group_code = code[:2]
                logger.info(f"提取的组别代码: {group_code}")
                if group_code not in ACCESS_CODES:
                    logger.warning(f"无效的组别代码: {group_code}")
                    return [
                        "无效的访问码",
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        None,
                        False
                    ]
                features = ACCESS_CODES[group_code]
                has_speech = "speech" in features
                has_reasoning = "reasoning" in features
                has_record = "reasoning_record" in features or "simple_record" in features
                is_group_01 = group_code == "01"
                # 对于没有语音转录功能的组别（00、03、04），显示音频播放选项卡
                show_audio_play = group_code in ["00", "03", "04"]
                
                logger.info(f"用户ID: {code}, 访问权限: {features}")
                if is_group_01:
                    return [
                        f"访问码验证成功，获得以下功能：{', '.join(features) if features else '无'}",
                        gr.update(visible=has_speech),
                        gr.update(visible=has_reasoning),
                        gr.update(visible=False),
                        gr.update(visible=show_audio_play),
                        gr.update(visible=True),
                        code,
                        True  # 01组显示结论部分
                    ]
                else:
                    return [
                        f"访问码验证成功，获得以下功能：{', '.join(features) if features else '无'}",
                        gr.update(visible=has_speech),
                        gr.update(visible=has_reasoning),
                        gr.update(visible=has_record),
                        gr.update(visible=show_audio_play),
                        gr.update(visible=False),
                        code,
                        False  # 非01组不显示结论部分
                    ]
            except Exception as e:
                logger.error(f"验证访问码时出错: {str(e)}")
                return [
                    "验证访问码时出错",
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    None,
                    False
                ]
        
        # 创建结论部分的可见性状态
        conclusion_section_visible = gr.State(False)
        
        access_code.submit(
            fn=validate_access,
            inputs=access_code,
            outputs=[auth_status, speech_tab, reasoning_tab, record_tab, audio_play_tab, group_01_tab, current_uid, conclusion_section_visible]
        )
        
        # 绑定音频选择功能
        def load_audio_with_status(patient_id):
            audio_path = experiment.load_patient_audio(patient_id)
            status = experiment.get_audio_status(patient_id)
            return audio_path, status
        
        patient1_btn.click(
            fn=lambda: load_audio_with_status("patient1"),
            outputs=[current_audio, auth_status]
        )
        
        patient2_btn.click(
            fn=lambda: load_audio_with_status("patient2"),
            outputs=[current_audio, auth_status]
        )
        
        patient3_btn.click(
            fn=lambda: load_audio_with_status("patient3"),
            outputs=[current_audio, auth_status]
        )
        
        # 绑定音频播放选项卡的音频选择功能
        patient1_btn_play.click(
            fn=lambda: load_audio_with_status("patient1"),
            outputs=[current_audio_play, auth_status]
        )
        
        patient2_btn_play.click(
            fn=lambda: load_audio_with_status("patient2"),
            outputs=[current_audio_play, auth_status]
        )
        
        patient3_btn_play.click(
            fn=lambda: load_audio_with_status("patient3"),
            outputs=[current_audio_play, auth_status]
        )
        
        # 音频播放完成后的自动转录功能已移除
        # 现在只支持手动点击转录按钮
        
        # 绑定语音转录和病历生成功能
        def delayed_transcribe(audio_file, uid):
            """延迟5秒后转录"""
            import time
            time.sleep(5)
            if uid:
                return experiment.async_transcribe_speech(audio_file, uid)
            else:
                return experiment.transcribe_speech(audio_file)
        
        def delayed_generate_record(audio_file):
            """延迟5秒后生成病历"""
            import time
            time.sleep(5)
            return experiment.generate_medical_record("")  # 这里传入空字符串，因为转录已经在播放完成时完成
        
        transcribe_btn.click(
            fn=delayed_transcribe,
            inputs=[current_audio, current_uid],
            outputs=transcription
        )
        
        generate_record_btn.click(
            fn=delayed_generate_record,
            inputs=current_audio,
            outputs=transcription
        )
        
        # 绑定病历保存功能
        save_record_btn.click(
            fn=experiment.save_patient_record,
            inputs=[
                patient_name, patient_id, patient_age, patient_gender,
                chief_complaint, present_illness, past_history, 
                personal_history, physical_exam, diagnosis, treatment_plan, current_uid
            ],
            outputs=record_status
        )
        
        # 绑定清空表单功能
        def clear_form():
            return ["", "", 0, None, "", "", "", "", "", "", "", "表单已清空"]
        
        clear_record_btn.click(
            fn=clear_form,
            outputs=[
                patient_name, patient_id, patient_age, patient_gender,
                chief_complaint, present_illness, past_history,
                personal_history, physical_exam, diagnosis, treatment_plan, record_status
            ]
        )
        
        # 医疗推理功能
        def delayed_generate_reasoning(text, uid):
            """延迟5秒后生成推理"""
            import time
            time.sleep(5)
            if uid:
                return experiment.async_medical_reasoning(text, uid)
            else:
                return experiment.generate_medical_reasoning(text)
        
        generate_btn.click(
            fn=delayed_generate_reasoning,
            inputs=[input_text, current_uid],
            outputs=output_text
        )
        
        # 获取病例结论功能
        get_conclusion_btn.click(
            fn=experiment.get_case_conclusion,
            outputs=conclusion_text
        )
        
        # 绑定结论部分的可见性
        conclusion_section_visible.change(
            fn=lambda x: gr.update(visible=x),
            inputs=conclusion_section_visible,
            outputs=conclusion_section
        )
        
        # 决策记录功能，所有相关回调增加uid参数
        def on_accept(text, result, uid):
            # 从完整uid中提取组别代码（前2位）
            group_code = uid[:2] if uid and len(uid) >= 2 else uid
            features = ACCESS_CODES.get(group_code, [])
            logger.info(f"on_accept被调用，uid={uid}, group_code={group_code}, features={features}, text长度={len(text) if text else 0}, result长度={len(result) if result else 0}")
            if text:
                if "simple_record" in features:
                    logger.info("使用simple_record保存")
                    # 演示版本：直接返回预准备的结果
                    simple_result = experiment.generate_medical_reasoning(text)
                    logger.info(f"保存simple_record: 接受, {simple_result[:100]}...")
                elif "reasoning_record" in features:
                    logger.info("使用reasoning_record保存")
                    if result:
                        logger.info(f"保存reasoning_record: 接受, {result[:100]}...")
                    else:
                        logger.warning("result为空，无法保存reasoning_record")
                else:
                    logger.warning(f"uid={uid}没有记录功能，features={features}")
                return gr.update(value=[["接受", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "用户接受"]])
            else:
                logger.warning("text为空，无法保存记录")
            return gr.update()
        
        def on_reject(uid):
            """处理拒绝分析"""
            return gr.update(visible=True)
        
        def on_confirm_reject(reason, text, result, uid):
            """处理确认拒绝"""
            if not reason:
                return gr.update(visible=True), gr.update()
            # 从完整uid中提取组别代码（前2位）
            group_code = uid[:2] if uid and len(uid) >= 2 else uid
            features = ACCESS_CODES.get(group_code, [])
            logger.info(f"on_confirm_reject被调用，uid={uid}, group_code={group_code}, features={features}, reason={reason}")
            if "simple_record" in features:
                logger.info("使用simple_record保存拒绝记录")
                simple_result = experiment.generate_medical_reasoning(text)
                logger.info(f"保存simple_record: 拒绝, {reason} - {simple_result[:100]}...")
            elif "reasoning_record" in features:
                logger.info("使用reasoning_record保存拒绝记录")
                logger.info(f"保存reasoning_record: 拒绝, {reason}")
            else:
                logger.warning(f"uid={uid}没有记录功能，features={features}")
            return gr.update(visible=False), gr.update(value=[["拒绝", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason]])
        
        accept_btn.click(
            fn=on_accept,
            inputs=[input_text, output_text, current_uid],
            outputs=history
        )
        
        reject_btn.click(
            fn=on_reject,
            outputs=reject_box
        )
        
        confirm_reject_btn.click(
            fn=on_confirm_reject,
            inputs=[reject_reasons, input_text, output_text, current_uid],
            outputs=[reject_box, history]
        )
        
        # 绑定01组决策记录功能
        def generate_conclusion(text):
            """生成结论（演示版本：返回Excel文件中conclusion列的内容）"""
            try:
                if not experiment.current_case:
                    return "请先选择病例"
                
                # 获取病例数据
                case_data = experiment.get_case_data(experiment.current_case)
                if case_data is None:
                    return f"未找到病例 {experiment.current_case} 的数据"
                
                # 返回conclusion列的内容作为结论
                conclusion = case_data.get('conclusion', '结论内容未找到')
                logger.info(f"为病例 {experiment.current_case} 获取conclusion列内容")
                return f"=== {experiment.current_case} 的诊断结论 ===\n\n{conclusion}"
                
            except Exception as e:
                logger.error(f"获取结论失败: {str(e)}")
                return f"获取结论失败: {str(e)}"
        
        def delayed_generate_conclusion(text):
            """延迟5秒后生成结论"""
            import time
            time.sleep(5)
            return generate_conclusion(text)
        
        generate_btn_01.click(
            fn=delayed_generate_conclusion,
            inputs=[input_text_01],
            outputs=[output_text_01]
        )
        
        def on_accept_01(text, result, uid):
            """处理01组接受结论"""
            # 从完整uid中提取组别代码（前2位）
            group_code = uid[:2] if uid and len(uid) >= 2 else uid
            features = ACCESS_CODES.get(group_code, [])
            logger.info(f"on_accept_01被调用，uid={uid}, group_code={group_code}, features={features}")
            if text and result:
                if "simple_record" in features:
                    logger.info(f"保存simple_record: 接受, {result[:100]}...")
                    return gr.update(value=[["接受", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "用户接受"]])
                else:
                    logger.warning(f"uid={uid}没有simple_record功能，features={features}")
            return gr.update()
        
        def on_reject_01_show():
            return gr.update(visible=True)
        
        def on_confirm_reject_01(reason, text, result, uid):
            # 从完整uid中提取组别代码（前2位）
            group_code = uid[:2] if uid and len(uid) >= 2 else uid
            features = ACCESS_CODES.get(group_code, [])
            logger.info(f"on_confirm_reject_01被调用，uid={uid}, group_code={group_code}, features={features}")
            if not reason:
                return gr.update(visible=True), gr.update()
            if "simple_record" in features:
                logger.info(f"保存simple_record: 拒绝, {reason} - {result[:100]}...")
                return gr.update(visible=False), gr.update(value=[["拒绝", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason]])
            else:
                logger.warning(f"uid={uid}没有simple_record功能，features={features}")
                return gr.update(visible=False), gr.update()
        
        reject_btn_01.click(
            fn=on_reject_01_show,
            outputs=[reject_box_01]
        )
        
        confirm_reject_btn_01.click(
            fn=on_confirm_reject_01,
            inputs=[reject_reasons_01, input_text_01, output_text_01, current_uid],
            outputs=[reject_box_01, history]
        )
        
        accept_btn_01.click(
            fn=on_accept_01,
            inputs=[input_text_01, output_text_01, current_uid],
            outputs=[history]
        )
        
        # 复制到剪贴板功能
        def copy_to_clipboard(text):
            import pyperclip
            try:
                pyperclip.copy(text)
                return "已复制到剪贴板"
            except Exception as e:
                logger.error(f"复制到剪贴板失败: {str(e)}")
                return f"复制失败: {str(e)}"
        
        copy_to_clipboard_btn.click(
            fn=copy_to_clipboard,
            inputs=[transcription],
            outputs=auth_status
        )
        
        # 绑定关闭欢迎弹窗功能
        def close_welcome():
            return gr.update(visible=False)
        
        close_welcome_btn.click(
            fn=close_welcome,
            outputs=[welcome_modal]
        )
        
        # 绑定系统状态查看功能
        def show_system_status():
            status = experiment.get_system_status()
            return gr.update(value=status, visible=True)
        
        status_btn.click(
            fn=show_system_status,
            outputs=[system_status]
        )
        
        logger.info("界面创建完成")
        return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(share=True)
