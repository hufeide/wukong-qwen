#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import signal
import sys
import time
from dotenv import load_dotenv
import concurrent.futures
import json

from deepseek_client_simple import DeepSeekClient
import mini.mini_sdk as MiniSdk
from mini.apis.api_sound import StartPlayTTS, StopPlayTTS
# from mini.apis.api_observe import ObserveSpeechRecognise
from mini.dns.dns_browser import WiFiDevice
from mini.apis.base_api import MiniApiResultType

import pyaudio
import dashscope
from dashscope.audio.asr import *
import asyncio
import logging
from typing import Callable

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")


logger = logging.getLogger("ObserveSpeechRecognise")

class ObserveSpeechRecognise:
    def __init__(self):
        """
        初始化 ObserveSpeechRecognise 类，创建回调函数存储变量和标记监听状态的变量。
        同时初始化 pyaudio 和 dashscope 相关变量。
        """
        self._callback: Callable = None
        self._is_listening = False
        self._simulated_task = None
        self.mic = None
        self.stream = None
        self.translator = None
        self.audio_stream_task = None

    def set_handler(self, callback: Callable):
        """
        设置语音识别结果的回调处理函数。

        :param callback: 处理语音识别结果的回调函数
        """
        self._callback = callback

    def start(self):
        """
        开始监听语音识别结果。使用 dashscope 进行真实语音识别。

        :return: 监听是否成功启动
        """
        if self._callback is None:
            logger.error("未设置回调函数，无法启动监听")
            return False
        if not self._is_listening:
            self._is_listening = True
            try:
                self._start_real_recognition()
                logger.info("语音识别监听已启动")
                return True
            except Exception as e:
                logger.error(f"启动真实语音识别失败，尝试启动模拟模式: {e}")
                self._simulated_task = asyncio.create_task(self._simulate_speech_recognition())
                logger.info("已切换到模拟语音识别模式")
                return True
        return False

    def stop(self):
        """
        停止监听语音识别结果。
        """
        if self._is_listening:
            if self.audio_stream_task:
                self.audio_stream_task.cancel()
            if self.translator:
                self.translator.stop()
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.mic:
                self.mic.terminate()
            self._is_listening = False
            logger.info("语音识别监听已停止")

    async def _simulate_speech_recognition(self):
        """
        模拟机器人进行语音识别并发送结果给回调函数。
        实际使用时需要替换为与机器人通信的真实逻辑。
        """
        simulated_results = [
            "你好",
            "今天天气怎么样",
            "帮我播放音乐"
        ]
        index = 0
        try:
            while self._is_listening:
                if index < len(simulated_results):
                    result = simulated_results[index]
                    logger.info(f"模拟接收到语音识别结果: {result}")
                    if self._callback:
                        self._callback(result)
                    index += 1
                await asyncio.sleep(3)  # 每3秒模拟一次识别结果
        except asyncio.CancelledError:
            logger.info("模拟语音识别任务已取消")

    def _start_real_recognition(self):
        """
        启动真实的语音识别，使用 dashscope 和 pyaudio。
        """
        class Callback(TranslationRecognizerCallback):
            def __init__(self, outer):
                super().__init__()
                self.outer = outer

            def on_open(self) -> None:
                self.outer.mic = pyaudio.PyAudio()
                self.outer.stream = self.outer.mic.open(
                    format=pyaudio.paInt16, channels=1, rate=16000, input=True
                )
                logger.info("TranslationRecognizerCallback open.")

            def on_close(self) -> None:
                if self.outer.stream:
                    self.outer.stream.stop_stream()
                    self.outer.stream.close()
                if self.outer.mic:
                    self.outer.mic.terminate()
                self.outer.stream = None
                self.outer.mic = None
                logger.info("TranslationRecognizerCallback close.")

            def on_event(
                self,
                request_id,
                transcription_result: TranscriptionResult,
                translation_result: TranslationResult,
                usage,
            ) -> None:
                logger.info(f"request id: {request_id}")
                logger.info(f"usage: {usage}")
                if transcription_result is not None:
                    text = transcription_result.text
                    if text:
                        logger.info(f"transcription: {text}")
                        if self.outer._callback:
                            self.outer._callback(text)

        self.translator = TranslationRecognizerRealtime(
            model="gummy-realtime-v1",
            format="pcm",
            sample_rate=16000,
            transcription_enabled=True,
            translation_enabled=True,
            translation_target_languages=["en"],
            callback=Callback(self),
        )
        self.translator.start()

        async def audio_stream_task():
            while self._is_listening and self.stream:
                try:
                    data = self.stream.read(3200, exception_on_overflow=False)
                    self.translator.send_audio_frame(data)
                except Exception as e:
                    logger.error(f"读取音频数据时出错: {e}")
                await asyncio.sleep(0.01)

        self.audio_stream_task = asyncio.create_task(audio_stream_task())

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deepseek语音助手")
logging.basicConfig(
    level=logging.INFO,  # You can adjust the level as needed
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Set the logging level for specific loggers
logging.getLogger('mini.channels.websocket_client').setLevel(logging.ERROR)
logging.getLogger('websockets.client').setLevel(logging.INFO)

# 全局变量
deepseek_client = None
voice_listener = None
running = True
simulation_mode = False
robot_connected = False
listen_task = None
reminder_task = None
tts_in_progress = False  # 标记TTS是否在进行中
current_tts_task = None  # 当前正在执行的TTS任务
conversation_history = []  # 对话历史记录，用于维护上下文
max_history_length = 5  # 保留的最大对话轮数
ignore_wake_during_tts = os.getenv("IGNORE_WAKE_DURING_TTS", "true").lower() == "true"  # 在TTS播放期间是否忽略语音输入
processing_locked = False  # 是否处于处理锁定状态，锁定期间不响应新命令
processing_lock_time = int(os.getenv("PROCESSING_LOCK_TIME", "3"))  # 处理锁定时间（秒）
min_sentence_length = int(os.getenv("MIN_SENTENCE_LENGTH", "5"))  # 最小句子长度
enable_thinking_feedback = os.getenv("ENABLE_THINKING_FEEDBACK", "false").lower() == "true"  # 是否显示处理中反馈
max_speech_buffer_size = int(os.getenv("MAX_SPEECH_BUFFER_SIZE", "10"))  # 语音缓冲区最大条目数
speech_buffer = []  # 语音缓冲区
speech_buffer_timeout = int(os.getenv("SPEECH_BUFFER_TIMEOUT", "5"))  # 语音缓冲区超时时间（秒）
enable_periodic_reminder = os.getenv("ENABLE_PERIODIC_REMINDER", "false").lower() == "true"  # 是否启用定期提醒
reminder_interval_minutes = int(os.getenv("REMINDER_INTERVAL_MINUTES", "10"))  # 定期提醒间隔时间（分钟）
ENABLE_INTERRUPTION = os.getenv("ENABLE_INTERRUPTION", "true").lower() == "true"  # 是否允许打断，默认允许

# TTS播放相关配置
# TTS播放后额外等待时间
tts_wait_time_after_play = float(os.getenv("TTS_WAIT_TIME_AFTER_PLAY", "0.5"))
# 每个字符的估计播放时间
tts_char_time = float(os.getenv("TTS_CHAR_TIME", "0.25"))
# TTS播放基础时间
tts_base_time = float(os.getenv("TTS_BASE_TIME", "1.0"))

# 语音片段合并相关配置
speech_fragments = []  # 语音片段缓冲区，用于收集连续的语音片段
fragment_merge_timeout = float(os.getenv("FRAGMENT_MERGE_TIMEOUT", "1.5"))  # 语音片段合并超时时间（秒）
last_fragment_time = 0  # 上一次接收到语音片段的时间
fragment_merge_task = None  # 片段合并超时任务
enable_fragment_merge = os.getenv("ENABLE_FRAGMENT_MERGE", "true").lower() == "true"  # 是否启用语音片段合并功能
max_wait_fragments = int(os.getenv("MAX_WAIT_FRAGMENTS", "5"))  # 最多等待的片段数
fragment_processing_lock = False  # 片段处理锁，防止并发处理片段

# 语句收集相关
current_sentence = ""  # 当前收集的语句
last_speech_time = 0  # 上一次收到语音的时间
sentence_timeout_task = None  # 句子超时任务
sentence_pause_timeout = float(os.getenv("SENTENCE_PAUSE_TIMEOUT", "3.0"))  # 认为句子结束的停顿时间（秒）
sentence_max_wait_time = float(os.getenv("SENTENCE_MAX_WAIT_TIME", "30.0"))  # 句子最长等待时间

# 定义打断关键词
INTERRUPT_KEYWORDS = ["打断", "停止播放"]

async def process_speech_recognition(text):
    """处理语音识别结果的核心逻辑"""
    global current_sentence, conversation_history
    
    if not text or not isinstance(text, str):
        logger.warning("无效的语音输入内容")
        return

    # 文本预处理
    processed_text = text.strip().lower()
    logger.info(f"开始处理语音指令: {processed_text}")
    
    # 检查退出指令
    if any(exit_cmd in processed_text for exit_cmd in ["退出", "结束", "关闭程序"]):
        logger.info("收到退出指令，准备关闭程序...")
        await shutdown()
        return
    
    # 检查打断指令
    if any(interrupt_cmd in processed_text for interrupt_cmd in INTERRUPT_KEYWORDS):
        logger.info("收到打断指令，准备打断TTS播放...")
        if tts_in_progress and ENABLE_INTERRUPTION:
            await interrupt_current_tts()
        else:
            logger.info("当前没有TTS播放或不允许打断")
        return
    
    try:
        # 检查是否为有效指令
        if len(processed_text) < min_sentence_length:
            logger.info(f"指令过短（{len(processed_text)}字符），已忽略")
            return
            
        # 添加到当前处理的句子
        append_to_current_sentence(processed_text)
        
        # 如果已累积足够长度的句子，立即处理
        if len(current_sentence) >= min_sentence_length:
            logger.info("触发立即处理机制")
            await process_sentence_after_timeout()
            
    except Exception as e:
        logger.error(f"语音指令处理异常: {str(e)}")
        import traceback
        logger.error(f"堆栈跟踪: {traceback.format_exc()}")
        await say_text("处理您的请求时出了点问题，请再试一次。")
# 设置处理锁定状态
async def set_processing_lock(status):
    """设置处理锁定状态，并在指定时间后自动解锁"""
    global processing_locked
    
    if status:
        logger.info(f"设置处理锁定状态，{processing_lock_time}秒内不响应新命令")
        processing_locked = True
        
        # 创建自动解锁任务
        asyncio.create_task(auto_unlock_processing())
    else:
        logger.info("解除处理锁定状态")
        processing_locked = False

# 自动解锁处理
async def auto_unlock_processing():
    """处理锁定状态的自动解锁任务"""
    global processing_locked
    
    try:
        # 等待指定的锁定时间
        await asyncio.sleep(processing_lock_time)
        
        # 解除锁定
        processing_locked = False
        logger.info("处理锁定自动解除")
    except Exception as e:
        logger.error(f"自动解锁处理时出错: {e}")
        # 出现异常时也尝试解除锁定
        processing_locked = False
        logger.info("因异常强制解除处理锁定")

# 检查文本是否为完整句子
def is_complete_sentence(text):
    """检查文本是否为相对完整的句子"""
    if not text or not isinstance(text, str):
        return False
    
    # 移除空白字符
    text = text.strip()
    
    # 检查长度是否达到最小句子长度
    if len(text) < min_sentence_length:
        logger.info(f"文本长度不足{min_sentence_length}个字符，判定为不完整句子")
        return False
 
    
    return True

# 语音识别结果回调函数
def on_asr_result(msg):
    """语音识别结果回调函数，事件驱动方式处理语音输入"""
    global current_sentence, last_speech_time, sentence_timeout_task, processing_locked
    
    # 记录接收时间
    current_time = time.time()
    last_speech_time = current_time
    
    logger.info(f"收到语音识别消息: {msg}")
    
    # 如果处于处理锁定状态，不处理新的语音输入
    if processing_locked:
        logger.info("处于处理锁定状态，忽略新的语音输入")
        return
    
    # 提取文本内容
    text = extract_text_from_speech_response(msg)
    
    if not text:
        logger.warning("无法从语音识别结果中提取文本内容")
        return
    
    # 新增：无论任何状态都优先检查打断指令
    # 修改异步任务调用方式
    if any(interrupt_cmd in text.lower() for interrupt_cmd in INTERRUPT_KEYWORDS):
        logger.info("检测到打断指令，立即处理")
        # 使用主事件循环调度协程
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(interrupt_current_tts(), main_event_loop)
        return
    
    # 原有状态检查后移（在打断检查之后）
    if tts_in_progress and ignore_wake_during_tts:
        logger.info("TTS正在播报中，忽略常规语音输入")
        return
    
    logger.info(f"识别到的文本: {text}")
    
    # 修改处理逻辑：无论是否TTS播放都记录语音
    speech_buffer.append({'content': text, 'timestamp': current_time})
    if len(speech_buffer) > max_speech_buffer_size:
        speech_buffer.pop(0)

    # 新增实时处理逻辑（即使TTS正在播放）
    if tts_in_progress:
        # 创建独立任务处理打断可能
        asyncio.create_task(check_immediate_interrupt(text))
    else:
        append_to_current_sentence(text)



# 新增即时打断检查
async def check_immediate_interrupt(text):
    """实时检查打断指令"""
    if any(cmd in text.lower() for cmd in INTERRUPT_KEYWORDS):
        logger.info("实时检测到打断指令")
        # 使用主事件循环调度协程
        if main_event_loop and main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(interrupt_current_tts(), main_event_loop)
            asyncio.run_coroutine_threadsafe(process_speech_result(text), main_event_loop)
        await interrupt_current_tts()
        await process_speech_result(text)
# 提取语音识别结果中的文本
def extract_text_from_speech_response(msg):
    """从各种格式的语音识别结果中提取文本内容"""
    text = None
    
    # 处理对象类型
    if hasattr(msg, 'text'):
        text = msg.text
    elif hasattr(msg, 'Text'):
        text = msg.Text
    
    # 处理字符串类型
    elif isinstance(msg, str):
        # 处理包含text:的字符串格式
        if 'text:' in msg:
            try:
                text_part = msg.split('text:')[1].strip()
                if text_part.startswith('"') and text_part.endswith('"'):
                    text_part = text_part[1:-1]
                
                # 处理Unicode编码
                if '\\u' in text_part:
                    try:
                        text = text_part.encode('latin1').decode('unicode_escape')
                    except Exception as e:
                        logger.warning(f"Unicode解码失败: {e}")
                        text = text_part
                else:
                    text = text_part
            except Exception as e:
                logger.warning(f"解析文本时出错: {e}")
        else:
            # 可能就是纯文本
            text = msg
    
    # 处理字典类型
    elif isinstance(msg, dict):
        if 'text' in msg:
            text = msg['text']
        elif 'Text' in msg:
            text = msg['Text']
    
    # 如果提取到的文本不是字符串类型，尝试转换
    if text and not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            text = None
    
    # 去除空白
    if text:
        text = text.strip()
        # 空字符串视为None
        if not text:
            text = None
    
    return text

# 添加文本到当前句子
def append_to_current_sentence(text):
    """添加新的文本片段到当前收集的句子"""
    global current_sentence, sentence_timeout_task, main_event_loop
    
    # 添加空格和新文本
    if current_sentence:
        current_sentence += " " + text
    else:
        current_sentence = text
    
    logger.info(f"当前累积句子: '{current_sentence}'")
    
    # 取消现有的超时任务
    if sentence_timeout_task and not sentence_timeout_task.done():
        if main_event_loop and main_event_loop.is_running():
            # Directly call the cancel method on the task
            sentence_timeout_task.cancel()
    
    # 设置新的句子超时任务
    if main_event_loop and main_event_loop.is_running():
        # Call the coroutine function to get a coroutine object
        coro = process_sentence_after_timeout()
        sentence_timeout_task = asyncio.run_coroutine_threadsafe(coro, main_event_loop)

# 句子超时后处理
async def process_sentence_after_timeout():
    """等待指定时间后处理当前累积的句子"""
    global current_sentence
    
    try:
        # 等待句子停顿超时
        await asyncio.sleep(sentence_pause_timeout)
        
        # 检查是否有累积的句子
        if current_sentence:
            logger.info(f"句子停顿超时({sentence_pause_timeout}秒)，处理累积句子: '{current_sentence}'")
            
            # 判断句子是否完整
            if is_complete_sentence(current_sentence):
                # 处理句子
                asyncio.create_task(set_processing_lock(True))
                asyncio.create_task(process_speech_result(current_sentence))
            else:
                logger.info(f"累积的句子不满足完整句子要求，忽略")
            
            # 清空当前句子
            current_sentence = ""
    except asyncio.CancelledError:
        # 任务被取消，这是正常的
        pass
    except Exception as e:
        logger.error(f"处理句子超时任务出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

# 设置语音识别
async def setup_speech_recognition():
    """设置语音识别事件处理"""
    global voice_listener
    
    try:
        logger.info("初始化并启动语音识别...")
        
        # 创建语音识别对象
        voice_listener = ObserveSpeechRecognise()
        
        # 设置回调处理函数
        voice_listener.set_handler(on_asr_result)
        
        # 启动语音识别
        start_result = voice_listener.start()
        logger.info(f"语音识别启动结果: {start_result}")
        
        # 等待语音识别服务启动
        await asyncio.sleep(1)
        
        # 无需轮询，事件驱动模式下回调函数会自动处理语音输入
        logger.info("语音识别准备就绪，进入事件驱动监听模式")
        
        # 仅返回，不再持续循环
        return True
    except Exception as e:
        logger.error(f"语音识别初始化失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

# 暂停语音识别
def pause_speech_recognition():
    """暂停语音识别服务"""
    global voice_listener, tts_in_progress
    
    if voice_listener:
        try:
            tts_in_progress = True
            logger.info("TTS播放开始，暂停语音识别服务")
            voice_listener.stop()
            return True
        except Exception as e:
            logger.error(f"暂停语音识别服务失败: {e}")
            return False
    return False

# 恢复语音识别
def resume_speech_recognition():
    """恢复语音识别服务"""
    global voice_listener, tts_in_progress
    
    if voice_listener:
        try:
            logger.info("TTS播放结束，恢复语音识别服务")
            voice_listener.start()
            tts_in_progress = False
            return True
        except Exception as e:
            logger.error(f"恢复语音识别服务失败: {e}")
            return False
    return False

# 打断当前TTS播放
async def interrupt_current_tts():
    """打断当前正在进行的TTS播放"""
    global tts_in_progress, current_tts_task
    
    logger.info("打断当前TTS播放...")
    
    try:
        # 停止TTS播放
        stop_tts = StopPlayTTS()
        await stop_tts.execute()
        
        # 如果有正在执行的TTS任务，取消它
        if current_tts_task and not current_tts_task.done():
            current_tts_task.cancel()
            try:
                await current_tts_task
            except asyncio.CancelledError:
                pass
        
        # 重置TTS状态
        tts_in_progress = False
        current_tts_task = None
        
        # 恢复语音识别
        resume_speech_recognition()
        
        # 播放短暂的提示音或反馈，表示打断成功
        logger.info("TTS播放已打断")
        
    except Exception as e:
        logger.error(f"打断TTS播放出错: {e}")

# 使用TTS播放文本
async def say_text(text, interrupt_existing=False):
    """使用TTS播放文本"""
    global tts_in_progress, current_tts_task, speech_buffer
    
    if not text or not text.strip():
        logger.warning("尝试播放空文本，已忽略")
        return
    
    # 如果需要打断现有TTS且允许打断
    if interrupt_existing and tts_in_progress and ENABLE_INTERRUPTION:
        await interrupt_current_tts()
    
    # 如果TTS正在进行中且不打断，则返回
    if tts_in_progress and not (interrupt_existing and ENABLE_INTERRUPTION):
        logger.warning("TTS正在进行中，已忽略新的播放请求")
        return
    
    # 暂停语音识别，避免识别自己的声音
    # pause_speech_recognition()
    interrupt_listener = asyncio.create_task(listen_for_interruptions())
    logger.info(f"开始TTS播放: {text}")
    tts_in_progress = True
    # 清空语音缓冲区
    speech_buffer = []
    
    try:
        # 确保停止任何可能正在进行的TTS播放
        
        # if tts_in_progress:
        #     
        #     try:
        #         await stop_tts.execute()
        #         logger.info("已停止之前的TTS播放")
        #         await asyncio.sleep(0.5)
        #     except asyncio.TimeoutError:
        #         logger.error("停止TTS播放超时")
                # 短暂等待确保停止完成          
        # except Exception as e:
            # continue
        # logger.warning(f"停止之前的TTS播放时出错: {e}")
        
        # 在TTS播放前，让先前的识别结果都被处理完毕
        try:
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.warning("等待操作被取消")
        except Exception as e:
            logger.error(f"等待操作出错: {e}")
        
        # 检查机器人状态
        if not robot_connected:
            logger.error("机器人未连接，无法播放TTS")
            return
            
        # 检查是否为模拟模式
        if simulation_mode:
            logger.info("模拟模式：假装播放TTS")
            await asyncio.sleep(len(text) * 0.1)  # 模拟播放时间
            logger.info("模拟TTS播放完成")
            return
        
        # 打印详细的TTS请求信息
        logger.info(f"发送TTS请求: text={text}, 机器人ID={os.getenv('ROBOT_ID')}, 机器人类型={os.getenv('ROBOT_TYPE')}")
        
        # 创建并发送TTS请求
        tts = StartPlayTTS(text=text)
        result = await tts.execute()
        
        # 输出原始响应结果用于调试
        logger.info(f"原始TTS响应: {result}")
        
        # 判断是否成功
        success = False
        if hasattr(result, 'isSuccess') and callable(result.isSuccess):
        # if result[0] == MiniApiResultType.Success:
            success = True
            logger.info(f"TTS响应isSuccess方法返回: {success}")
        elif isinstance(result, tuple) and len(result) > 0:
            # 假设元组第一个元素是成功状态指示
            success = bool(result[0])
            logger.info(f"TTS响应元组第一个元素: {result[0]}")
        else:
            # 默认假设成功，因为我们无法确定
            success = True
            logger.warning(f"无法确定TTS结果状态，假设成功: {result}")
        
        if success:
            logger.info("TTS请求成功发送")
            
            # 等待TTS完全播放完成，这里使用比较保守的方法
            # 在复杂的实现中，可以考虑使用回调或事件来获取播放完成通知
            try:
                # 等待TTS完成播放
                # 这里我们会等待一个完整的TTS请求完成
                # 不再使用估算的播放时间，而是等待另一个stopTTS来确认TTS完成
                # 可以尝试添加超时机制
                stop_tts = StopPlayTTS()
                await asyncio.wait_for(stop_tts.execute(), timeout=10)
                logger.info("TTS播放完成，已停止")
            except asyncio.TimeoutError:
                logger.error("等待TTS播放完成超时")
            except Exception as e:
                logger.error(f"停止TTS播放出错: {e}")
        else:
            logger.error(f"TTS请求失败: {result}")
            
            # 尝试分析错误原因
            if hasattr(result, 'resultCode') and hasattr(result, 'resultMsg'):
                logger.error(f"错误代码: {result.resultCode}, 错误消息: {result.resultMsg}")
                
            # 可以尝试重新发送一次请求
            logger.info("尝试重新发送TTS请求...")
            retry_tts = StartPlayTTS(text=text)
            retry_result = await retry_tts.execute()
            logger.info(f"重试TTS响应: {retry_result}")
            
    except Exception as e:
        logger.error(f"TTS播放出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    finally:
        # 短暂等待，确保TTS完全停止
        logger.info(f"等待额外{tts_wait_time_after_play}秒确保TTS完全停止")
        await asyncio.sleep(tts_wait_time_after_play)
        interrupt_listener.cancel()
        # 恢复语音识别
        resume_speech_recognition()
        
        # 重置TTS状态
        tts_in_progress = False
        current_tts_task = None
        
        # 添加日志确认TTS播放和处理已完成
        logger.info(f"已处理语音输入并播放响应: '{text}'")
        
        # 处理在TTS期间积累的语音识别结果
        await process_speech_buffer()


# 新增打断监听函数
async def listen_for_interruptions():
    """持续监听打断指令"""
    global tts_in_progress
    while tts_in_progress:
        # 检查缓冲区中的最新语音输入
        if speech_buffer:
            latest_item = speech_buffer[-1]
            text = latest_item['content'].lower()
            
            # 检查打断关键词
            if any(cmd in text for cmd in INTERRUPT_KEYWORDS):
                logger.info("检测到打断指令，立即停止TTS")
                await interrupt_current_tts()
                # 处理新的语音输入
                await process_speech_result(text)
                return
        await asyncio.sleep(0.1)  # 每100ms检查一次
# 处理TTS期间积累的语音识别结果
async def process_speech_buffer():
    """处理TTS期间积累的语音识别结果"""
    global speech_buffer
    
    if not speech_buffer:
        return
        
    current_time = time.time()
    logger.info(f"TTS结束，处理积累的{len(speech_buffer)}条语音识别结果")
    
    # 过滤并只保留最近speech_buffer_timeout秒内的消息
    valid_buffer = []
    expired_count = 0
    
    for item in speech_buffer:
        if current_time - item['timestamp'] <= speech_buffer_timeout:
            valid_buffer.append(item)
        else:
            expired_count += 1
    
    if expired_count > 0:
        logger.info(f"丢弃{expired_count}条超过{speech_buffer_timeout}秒的过期语音识别结果")
    
    logger.info(f"保留{len(valid_buffer)}条有效语音识别结果进行处理")
    
    # 复制并清空缓冲区
    buffer_copy = valid_buffer.copy()
    speech_buffer = []
    
    # 处理保留的语音识别结果
    for item in buffer_copy:
        process_speech_recognition(item['content'])
        # 短暂等待，避免处理过快
        await asyncio.sleep(0.1)

# 处理语音识别结果
async def process_speech_result(text):
    """处理语音识别结果"""
    global conversation_history
    
    if not text:
        logger.warning("尝试处理空文本，已忽略")
        return
    
    logger.info(f"处理语音输入: {text}")
    
    # 如果启用了思考反馈，先播放"我想想"
    if enable_thinking_feedback and robot_connected and not simulation_mode:
        thinking_task = asyncio.create_task(say_text("我想想"))
        # 等待思考提示播放完成，但不阻塞太久，最多等待1秒
        try:
            await asyncio.wait_for(thinking_task, timeout=1.0)
        except asyncio.TimeoutError:
            logger.info("思考提示播放超时，继续处理请求")
    
    try:
        # 向DeepSeek V3发送请求
        logger.info(f"向DeepSeek V3发送请求...")
        
        if conversation_history:
            # 如果有对话历史，使用它进行请求
            response = await deepseek_client.get_response_with_history(conversation_history + [{"role": "user", "content": text}])
        else:
            # 否则进行新的请求
            response = await deepseek_client.get_response(text)
        
        logger.info(f"DeepSeek V3响应: {response}")
        
        # 更新对话历史
        conversation_history.append({"role": "user", "content": text})
        conversation_history.append({"role": "assistant", "content": response})
        
        # 限制对话历史长度
        if len(conversation_history) > max_history_length * 2:
            conversation_history = conversation_history[-max_history_length * 2:]
        
        # 使用机器人TTS播放响应
        logger.info(f"机器人回复: {response}")
        if robot_connected and not simulation_mode:
            # 等待思考提示播放完成
            await say_text(response)
            
    except Exception as e:
        logger.error(f"处理语音识别结果时出错: {e}")
        
        # 如果连接到机器人，给出错误提示
        if robot_connected and not simulation_mode:
            await say_text("抱歉，我遇到了问题，无法处理您的请求。")
    finally:
        # 确保处理锁定状态在消息处理完成后解除
        # 这是额外的保障措施，通常会由自动解锁任务处理
        # 不使用await，因为set_processing_lock会创建新的解锁任务
        asyncio.create_task(set_processing_lock(False))

# 用于测试的模拟语音输入函数
async def simulate_speech_input():
    """模拟语音输入，用于测试"""
    global running
    
    test_inputs = [
        "你好，你是谁？",
        "今天天气怎么样？",
        "讲个笑话吧",
        "你能做什么？",
        "退出程序"
    ]
    
    for test_input in test_inputs:
        if not running:
            break
            
        logger.info(f"模拟语音输入: {test_input}")
        on_asr_result(test_input)
        
        # 等待足够的时间以完成对话
        await asyncio.sleep(10)
        
    running = False

# 程序清理函数
async def shutdown():
    """关闭程序，清理资源"""
    global running, voice_listener, robot_connected, listen_task, reminder_task, command_timeout_task
    
    logger.info("开始关闭程序...")
    running = False
    
    # 等待1秒，让任务有机会结束
    await asyncio.sleep(1)
    
    # 停止并清理任务
    try:
        logger.info("停止语音监听...")
        if voice_listener:
            try:
                voice_listener.stop()
                logger.info("语音监听已停止")
            except Exception as e:
                logger.error(f"停止语音监听时出错: {e}")
    except Exception as e:
        logger.error(f"处理语音监听器时出错: {e}")
    
    # 断开机器人连接
    if robot_connected:
        try:
            logger.info("退出编程模式...")
            await MiniSdk.quit_program()
            
            logger.info("断开机器人连接...")
            await MiniSdk.release()
            
            robot_connected = False
            logger.info("机器人连接已断开")
        except Exception as e:
            logger.error(f"断开机器人连接时出错: {e}")
    
    # 取消异步任务
    for task_name, task in [
        ("listen_task", listen_task), 
        ("reminder_task", reminder_task),
        ("command_timeout_task", command_timeout_task)
    ]:
        if task and not task.done():
            try:
                logger.info(f"取消{task_name}...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"{task_name}已取消")
            except Exception as e:
                logger.error(f"取消{task_name}时出错: {e}")
    
    logger.info("程序关闭完成")

# 键盘中断处理函数
def keyboard_interrupt_handler(signal, frame):
    """处理键盘中断"""
    logger.info("接收到中断信号，程序将退出")
    asyncio.create_task(shutdown())
    sys.exit(0)

# 注册信号处理函数
signal.signal(signal.SIGINT, keyboard_interrupt_handler)

# 定期提醒用户
async def periodic_reminder():
    """定期提醒用户"""
    global running, robot_connected
    
    # 检查是否启用定期提醒
    if not enable_periodic_reminder:
        logger.info("定期提醒功能已禁用")
        return
    
    # 第一次等待较长时间，避免刚开始就提醒
    await asyncio.sleep(60)
    
    # 将分钟转换为秒
    reminder_interval = reminder_interval_minutes * 60
    count = 0
    
    logger.info(f"启动定期提醒服务，间隔时间: {reminder_interval_minutes}分钟")
    
    while running:
        if not robot_connected:
            await asyncio.sleep(10)
            continue
            
        count += 1
        try:
            # 随机选择提醒语
            reminders = [
                "有什么需要帮助的，随时告诉我",
                "我随时待命，有问题可以直接提问",
                "我是您的智能助手，有需要可以直接说出来"
            ]
            reminder = reminders[count % len(reminders)]
            
            logger.info(f"播放定期提醒: {reminder}")
            await say_text(reminder)
            
        except Exception as e:
            logger.error(f"播放定期提醒时出错: {e}")
            
        # 等待到下一次提醒
        await asyncio.sleep(reminder_interval)

async def main():
    global robot_connected, voice_listener, running, reminder_task, deepseek_client, main_event_loop
    
    # Initialize main_event_loop
    main_event_loop = asyncio.get_running_loop()
    
    logger.info("========== 启动deepseek语音助手 ==========")
    logger.info(f"打断功能状态: {'已启用' if ENABLE_INTERRUPTION else '未启用'}")
    logger.info(f"TTS期间忽略语音输入: {'已启用' if ignore_wake_during_tts else '未启用'}")
    logger.info(f"语句停顿超时时间: {sentence_pause_timeout}秒")
    logger.info(f"语句最长等待时间: {sentence_max_wait_time}秒")
    logger.info(f"TTS播放后等待时间: {tts_wait_time_after_play}秒")
    logger.info(f"TTS每字符播放时间: {tts_char_time}秒")
    logger.info(f"TTS基础播放时间: {tts_base_time}秒")
    logger.info(f"定期提醒功能: {'已启用' if enable_periodic_reminder else '未启用'}")
    if enable_periodic_reminder:
        logger.info(f"定期提醒间隔: {reminder_interval_minutes}分钟")
    
    # 初始化信号处理
    for signal_name in ('SIGINT', 'SIGTERM'):
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(
                getattr(signal, signal_name),
                lambda: asyncio.create_task(shutdown())
            )
            logger.info(f"已注册信号处理程序: {signal_name}")
        except (NotImplementedError, ImportError):
            logger.warning(f"不支持的信号: {signal_name}")
    
    # 从环境变量加载配置
    load_dotenv()
    
    # 获取模拟模式设置
    simulation_mode = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    logger.info(f"模拟模式: {simulation_mode}")
    
    # 初始化DeepSeek客户端
    try:
        logger.info("初始化DeepSeek V3客户端...")
        deepseek_client = DeepSeekClient()
        logger.info("DeepSeek V3客户端初始化成功")
    except Exception as e:
        logger.error(f"DeepSeek V3客户端初始化失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    
    if not simulation_mode:
        # 连接机器人
        robot_id = os.getenv("ROBOT_ID", "00258")
        robot_ip = os.getenv("ROBOT_IP")
        logger.info(f"机器人ID: {robot_id}, IP: {robot_ip}")
        
        if not robot_ip:
            logger.error("未设置机器人IP，无法连接")
            return
            
        # 连接机器人
        logger.info("连接机器人中...")
        
        # 设置机器人类型
        robot_type = os.getenv("ROBOT_TYPE", "mini").lower()
        if robot_type == "dedu":
            logger.info("设置机器人类型为: DEDU")
            MiniSdk.set_robot_type(MiniSdk.RobotType.DEDU)
        else:
            logger.info("设置机器人类型为: MINI")
            MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)
        
        # 扫描机器人
        logger.info("扫描机器人...")
        try:
            # 直接创建WiFiDevice
            device_name = f"Mini_030006KFK18082700{robot_id}"
            device = WiFiDevice(
                name=device_name,
                address=robot_ip,
                port=51014,
                s_type="_Mini_mini_channel_server._tcp.local.",
                server="Android.local."
            )
            logger.info(f"找到设备: {device}")
            
            # 连接设备
            logger.info("连接设备...")
            result = await MiniSdk.connect(device)
            logger.info(f"连接结果: {result}")
            
            if not result:
                logger.error("连接失败")
                return
                
            robot_connected = True
            logger.info("机器人连接成功")
            
            # 进入编程模式
            logger.info("进入编程模式...")
            result = await MiniSdk.enter_program()
            logger.info(f"进入编程模式结果: {result}")
            
            # 等待进入编程模式的播报结束
            await asyncio.sleep(2)
            
            # 设置语音识别，改为事件驱动模式
            speech_recognition_ready = await setup_speech_recognition()
            
            if not speech_recognition_ready:
                logger.error("语音识别初始化失败，程序将退出")
                await shutdown()
                return
            
            # 播放欢迎语
            welcome_text = "你好，我是悟空。"
            await say_text(welcome_text)
            
            # 启动定期提醒任务
            reminder_task = asyncio.create_task(periodic_reminder())
            
            # 保持程序运行
            while running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"连接机器人出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            
            if robot_connected:
                try:
                    await MiniSdk.quit_program()
                    await MiniSdk.release()
                except Exception as e:
                    logger.error(f"断开连接出错: {e}")
                
                robot_connected = False
    else:
        logger.info("模拟模式，不连接实际机器人")
        try:
            # 模拟模式下，启动模拟测试
            asyncio.create_task(simulate_speech_input())
            
            # 保持程序运行
            while running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"模拟模式运行出错: {e}")
    
    logger.info("主函数执行完毕")

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main()) 