#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的多进程管理器
避免序列化问题，提供基本的多进程功能
"""

import multiprocessing
import time
import logging
import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simple_multiprocess.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SimpleTask:
    """简单任务格式"""
    task_type: str
    task_id: str
    data: Any
    uid: str
    case_name: str = None  # 病例名称，用于reasoning任务
    timestamp: float = 0.0

@dataclass
class SimpleResult:
    """简单结果格式"""
    task_id: str
    result: Any
    status: str
    timestamp: float

def worker_process(task_queue, result_queue):
    """工作进程函数"""
    logger.info(f"工作进程 {os.getpid()} 启动")
    
    # 在工作进程中加载scripts.xlsx
    scripts_data = None
    scripts_file = "scripts.xlsx"
    try:
        import pandas as pd
        if os.path.exists(scripts_file):
            scripts_data = pd.read_excel(scripts_file)
            logger.info(f"工作进程 {os.getpid()} 成功加载脚本文件，包含 {len(scripts_data)} 个病例")
        else:
            logger.warning(f"工作进程 {os.getpid()} 脚本文件不存在: {scripts_file}")
    except Exception as e:
        logger.error(f"工作进程 {os.getpid()} 加载脚本文件失败: {str(e)}")
    
    def get_case_data(case_name):
        """根据病例名称获取数据"""
        if scripts_data is None:
            return None
        try:
            case_data = scripts_data[scripts_data['case'] == case_name]
            if not case_data.empty:
                return case_data.iloc[0].to_dict()
            else:
                logger.warning(f"未找到病例: {case_name}")
                return None
        except Exception as e:
            logger.error(f"获取病例数据失败: {str(e)}")
            return None
    
    while True:
        try:
            # 获取任务
            task = task_queue.get()
            if task is None:  # 结束信号
                break
            
            logger.info(f"工作进程 {os.getpid()} 处理任务: {task.task_id}, 类型: {task.task_type}")
            
            # 模拟处理时间
            time.sleep(2)
            
            # 根据任务类型生成结果
            if task.task_type == "speech":
                # 根据音频文件名确定病例
                audio_file = task.data
                audio_filename = os.path.basename(audio_file) if isinstance(audio_file, str) else str(audio_file)
                
                if "吴女士" in audio_filename:
                    case_name = "吴女士"
                elif "王女士" in audio_filename:
                    case_name = "王女士"
                elif "张先生" in audio_filename:
                    case_name = "张先生"
                else:
                    case_name = None
                
                if not case_name:
                    result = f"无法识别音频文件对应的病例: {audio_filename}"
                    logger.warning(result)
                else:
                    # 获取病例数据
                    case_data = get_case_data(case_name)
                    if case_data is None:
                        result = f"未找到病例 {case_name} 的数据"
                        logger.warning(result)
                    else:
                        # 返回对话文本
                        dialogue = case_data.get('dialogue', '对话内容未找到')
                        result = f"=== {case_name} 的对话记录 ===\n\n{dialogue}"
                        logger.info(f"工作进程 {os.getpid()} 为病例 {case_name} 返回对话文本")
                        
            elif task.task_type == "reasoning":
                # 使用传递的病例名称或从文本中推断
                case_name = task.case_name
                if not case_name:
                    # 尝试从文本中推断病例名称
                    text = str(task.data)
                    if "吴女士" in text:
                        case_name = "吴女士"
                    elif "王女士" in text:
                        case_name = "王女士"
                    elif "张先生" in text:
                        case_name = "张先生"
                
                if not case_name:
                    result = "无法确定病例名称，请先进行语音转录"
                    logger.warning(result)
                else:
                    # 获取病例数据
                    case_data = get_case_data(case_name)
                    if case_data is None:
                        result = f"未找到病例 {case_name} 的数据"
                        logger.warning(result)
                    else:
                        # 返回推理文本
                        reasoning = case_data.get('reasoning', '推理内容未找到')
                        result = f"=== {case_name} 的医疗推理 ===\n\n{reasoning}"
                        logger.info(f"工作进程 {os.getpid()} 为病例 {case_name} 返回推理文本")
            else:
                result = f"未知任务类型: {task.task_type}"
                logger.warning(result)
            
            # 发送结果
            simple_result = SimpleResult(
                task_id=task.task_id,
                result=result,
                status="success",
                timestamp=time.time()
            )
            
            result_queue.put(simple_result)
            logger.info(f"工作进程 {os.getpid()} 完成任务: {task.task_id}")
            
        except Exception as e:
            logger.error(f"工作进程 {os.getpid()} 处理任务失败: {str(e)}", exc_info=True)
            # 发送错误结果
            error_result = SimpleResult(
                task_id=task.task_id if 'task' in locals() else "unknown",
                result=f"处理失败: {str(e)}",
                status="error",
                timestamp=time.time()
            )
            result_queue.put(error_result)
    
    logger.info(f"工作进程 {os.getpid()} 退出")

class SimpleTaskScheduler:
    """简单任务调度器"""
    
    def __init__(self, num_workers: int = 2):
        self.num_workers = num_workers
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.workers = []
        self.pending_tasks: Dict[str, SimpleTask] = {}
        self.completed_tasks: Dict[str, SimpleResult] = {}
        self.task_counter = 0
        
        # 启动工作进程
        self._start_workers()
        
        # 启动结果监控线程
        self._start_result_monitor()
        
        logger.info(f"简单任务调度器启动，工作进程数: {num_workers}")
    
    def _start_workers(self):
        """启动工作进程"""
        for i in range(self.num_workers):
            worker = multiprocessing.Process(
                target=worker_process,
                args=(self.task_queue, self.result_queue)
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"启动工作进程 {i+1}: PID {worker.pid}")
    
    def _start_result_monitor(self):
        """启动结果监控线程"""
        import threading
        
        def monitor_results():
            while True:
                try:
                    # 检查结果队列
                    if not self.result_queue.empty():
                        result = self.result_queue.get_nowait()
                        
                        # 更新任务状态
                        if result.task_id in self.pending_tasks:
                            del self.pending_tasks[result.task_id]
                        
                        self.completed_tasks[result.task_id] = result
                        logger.info(f"任务 {result.task_id} 完成，状态: {result.status}")
                    
                    time.sleep(0.1)  # 短暂休眠
                    
                except Exception as e:
                    logger.error(f"结果监控出错: {str(e)}")
                    time.sleep(1)  # 出错时增加休眠时间
        
        monitor_thread = threading.Thread(target=monitor_results, daemon=True)
        monitor_thread.start()
        logger.info("结果监控线程已启动")
    
    def submit_task(self, task_type: str, data: Any, uid: str, case_name: str = None) -> str:
        """提交任务"""
        self.task_counter += 1
        task_id = f"{task_type}_{uid}_{self.task_counter}_{int(time.time() * 1000)}"
        
        task = SimpleTask(
            task_type=task_type,
            task_id=task_id,
            data=data,
            uid=uid,
            case_name=case_name,
            timestamp=time.time()
        )
        
        # 添加到待处理任务
        self.pending_tasks[task_id] = task
        
        # 提交到队列
        self.task_queue.put(task)
        
        logger.info(f"任务已提交: {task_id}, 病例: {case_name}")
        return task_id
    
    def get_task_result(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 0.2
    ) -> Optional[SimpleResult]:
        """
        获取任务结果

        Args:
            task_id: 任务ID
            timeout: 最长等待时间（秒）。为None时不阻塞，直接返回当前已知状态
            poll_interval: 轮询间隔
        """
        if timeout is None:
            return self.completed_tasks.get(task_id)
        
        end_time = time.time() + timeout
        while time.time() < end_time:
            result = self.completed_tasks.get(task_id)
            if result:
                return result
            time.sleep(poll_interval)
        
        # 超时后再尝试获取一次，确保错过的瞬间也能返回
        return self.completed_tasks.get(task_id)
    
    def shutdown(self):
        """关闭调度器"""
        logger.info("正在关闭简单任务调度器...")
        
        # 发送结束信号给所有工作进程
        for _ in self.workers:
            self.task_queue.put(None)
        
        # 等待所有工作进程结束
        for worker in self.workers:
            worker.join(timeout=5)
            if worker.is_alive():
                worker.terminate()
                worker.join()
        
        logger.info("简单任务调度器已关闭")

# 全局调度器实例
_global_simple_scheduler = None

def get_simple_scheduler() -> SimpleTaskScheduler:
    """获取全局简单调度器实例"""
    global _global_simple_scheduler
    if _global_simple_scheduler is None:
        _global_simple_scheduler = SimpleTaskScheduler(num_workers=2)
        
        # 注册信号处理器
        import signal
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在关闭系统...")
            if _global_simple_scheduler:
                _global_simple_scheduler.shutdown()
            os._exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    return _global_simple_scheduler



