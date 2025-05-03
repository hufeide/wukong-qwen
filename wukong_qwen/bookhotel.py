# To run this code, make sure:
# 1. Have installed "alphamini" and "ibm-watson" Python modules
# 2. Changes to your IBM Watson Assistant parameters:
#       a. API key 
#       b. Assistant URL 
#       c. Assistant ID
# 3. Alpha Mini serial number

# Follow through the code below to see where are the changes needed. 

import asyncio
from typing import Callable
import mini.mini_sdk as MiniSdk
from mini.apis.api_observe import ObserveSpeechRecognise as OriginalObserveSpeechRecognise
from mini.apis.api_sound import StartPlayTTS
from mini.apis.api_action import PlayAction, PlayActionResponse
from mini.dns.dns_browser import WiFiDevice
from mini.apis.base_api import MiniApiResultType
from mini.pb2.codemao_speechrecognise_pb2 import SpeechRecogniseResponse
import json
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import logging
import pyaudio
from dashscope.audio.asr import TranslationRecognizerRealtime, TranslationRecognizerCallback, TranscriptionResult, TranslationResult

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# 新的 ObserveSpeechRecognise 类
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
                # logger.info(f"request id: {request_id}")
                # logger.info(f"usage: {usage}")
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

authenticator = IAMAuthenticator(
    '2mLWS_yLl13ZgCy7WT_G6YFXJmCskbUUEb078vTIfZ2O')
assistant = AssistantV2(
    version='2020-09-24',
    authenticator=authenticator
)

assistant.set_service_url('https://api.us-south.assistant.watson.cloud.ibm.com/')

async def test_play_action(y):
    
    # action_name: The action name can be obtained with GetActionList API: http://docs.ubtrobot.com/alphamini/python-sdk-en/mini.apis.api_action.html#mini.apis.api_action.GetActionList


    block: PlayAction = PlayAction(action_name=y)
    # response: PlayActionResponse
    
    (resultType, response) = await block.execute()
    

    print(f'test_play_action result:{response}')
    assert resultType == MiniApiResultType.Success, 'test_play_action timetout'
    assert response is not None and isinstance(response, PlayActionResponse), 'test_play_action result unavailable'
    assert response.isSuccess, 'play_action failed'
    return response

async def test_connect(dev: WiFiDevice) -> bool:
    """Connect the device
    Connect the specified device
    Args:
        dev (WiFiDevice): Specified device object WiFiDevice
    Returns:
        bool: Whether the connection is successful
    """
    return await MiniSdk.connect(dev)

async def shutdown():
    """Disconnect and release resources"""
    try:
        global observe
        if observe:
            observe.stop()
            await asyncio.sleep(0.1)  # Add small delay for cleanup

        await MiniSdk.quit_program()
        await MiniSdk.release()

        # Proper task cancellation
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Explicitly close transports
        if observe and observe._is_listening:
            observe._is_listening = False
            if observe.stream:
                observe.stream.close()
            if observe.mic:
                observe.mic.terminate()

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        # Ensure loop closure
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()


async def test_get_device_by_name():
    """Search for devices based on the suffix of the robot serial number
    To search for the robot with the specified serial number (behind the robot's butt), you can just enter the tail character of the serial number, any length, it is recommended that more than 5 characters can be matched accurately, and the timeout is 10 seconds
    Returns:
        WiFiDevice: Contains robot name, ip, port and other information
    """
    result: WiFiDevice = await MiniSdk.get_device_by_name("020863", 10)
    print(f"test_get_device_by_name result:{result}")
    return result

async def test_start_run_program():
    """Enter programming mode 
    Make the robot enter the programming mode, wait for the response result, and delay 6 seconds, let the robot finish "Enter the programming mode"
    Returns:
        None:
    """
    await MiniSdk.enter_program()
    asyncio.create_task(__tts("Hello guest?"))
    asyncio.create_task(test_play_action("action_014"))


observe = None
main_loop = None
task_queue = asyncio.Queue(maxsize=1)  # 新增任务队列
is_speaking = False  # 新增播放状态标志
# 唤醒词
WAKE_WORD = "小狗"

# 新增工作协程
# 在全局变量区域添加
tts_worker_task = None  # 新增队列工作协程引用

async def tts_worker():
    global is_speaking
    while True:
        text = await task_queue.get()
        is_speaking = True
        try:
            # 增加队列锁机制
            if task_queue.qsize() > 3:  # 控制队列最大长度
                async with task_queue._queue.mutex:  # 使用内部队列的锁
                    task_queue._queue.clear()
                logger.warning("队列过载，已清空旧消息")
            # 播放前停止语音识别
            if observe and observe._is_listening:
                observe.stop()
                logger.info("播放前关闭语音识别")

            block = StartPlayTTS(text=text)
            result_type, response = await block.execute()
            
            # 添加播放完成延迟（避免残留声波被识别）
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"播放异常: {e}")
        finally:
            is_speaking = False
            task_queue.task_done()
            # 播放完成后重启语音识别
            if observe and not observe._is_listening:
                observe.start()
                logger.info("播放完成重启语音识别")
            logger.info("队列任务处理完成")

# 在全局变量区域修改队列初始化
task_queue = asyncio.Queue(maxsize=1)  # 改为长度1的队列

async def __tts(x):
    logger.info(f"{x}")
    global observe
    if observe and observe._is_listening:
        # 清空队列并放入最新消息
        while not task_queue.empty():
            task_queue.get_nowait()
            task_queue.task_done()
            
        task_queue.put_nowait(x)
        logger.info(f"已更新播放队列，当前内容: {x}")

    else:
        logger.warning("语音识别未开启，忽略播报请求")

import time
async def test_speech_recognise():
    global observe, main_loop
    # 在函数外部创建会话
    session = assistant.create_session(assistant_id='b197f077-ca47-44ca-9ea2-fcf0f9215a8e').get_result()
    value = session["session_id"]
    logger.info(f"已创建新会话: {value}")

    observe = ObserveSpeechRecognise()
    main_loop = asyncio.get_event_loop()

    async def handler(msg):
        global observe, main_loop, is_speaking
        try:
            current_time = time.time()
            # 新增语句缓冲区（保存最近3秒的语句片段）
            if not hasattr(handler, "buffer"):
                handler.buffer = []
                handler.last_processed = 0
            
            # 缓冲处理逻辑
            handler.buffer.append({'text': msg, 'time': current_time})
            
            # 过滤过期片段（保留最近2秒）
            handler.buffer = [m for m in handler.buffer if current_time - m['time'] < 2]
            
            # 合并缓冲内容（取时间最近的完整语句）
            combined_text = max(
                (m['text'] for m in handler.buffer if len(m['text'].split()) >= 3 or any(c in m['text'] for c in ['?', '!', '.'])),
                default=None,
                key=lambda x: handler.buffer.index(next(m for m in handler.buffer if m['text'] == x))
            )
        
            if not combined_text:
                logger.info("缓冲中未形成完整语句")
                return
                
            # 防重检测（处理合并后的完整语句）
            if hasattr(handler, "last_msg") and combined_text == handler.last_msg:
                if current_time - handler.last_processed < 5:
                    logger.warning("忽略重复完整语句")
                    return
        
            handler.last_msg = combined_text
            handler.last_processed = current_time
            handler.buffer.clear()  # 处理成功后清空缓冲

            if WAKE_WORD in msg:
                # 唤醒词处理逻辑
                logger.info("检测到唤醒词，准备新对话")
                observe.stop()
                while not task_queue.empty():
                    task_queue.get_nowait()
                await asyncio.sleep(0.5)
                observe.start()
                return

            # 消息处理核心逻辑
            response = assistant.message(
                assistant_id='b197f077-ca47-44ca-9ea2-fcf0f9215a8e',
                session_id=value,  # 使用外部创建的会话ID
                input={'message_type': 'text', 'text': str(combined_text).replace(WAKE_WORD, "")},
                environment_id='cfd00a9d-88d3-4b9b-a5f5-8e5893df9d4b'
            ).get_result()

            # 新增响应内容去重
            text = ' '.join([item["text"] for item in response["output"]["generic"] if "text" in item])
            if not text:
                return
            
            # 检查最近5条消息是否重复
            recent_msgs = getattr(handler, "recent_msgs", [])
            if text in recent_msgs:
                logger.info("忽略重复响应内容")
                return
            recent_msgs = [text] + recent_msgs[:4]  # 保持最近5条记录
            handler.recent_msgs = recent_msgs

            # 创建并行任务（新增队列去重检查）
            if text not in [task.get_name() for task in asyncio.all_tasks()]:
                action_tasks = [__tts(text)]
                
            # 优化动作触发逻辑
            keyword_actions = {
                "day": "action_019",
                "time": "Surveillance_006",
                "confirm": "action_012",
                "safe": "action_018"
            }
            action_tasks.extend(
                test_play_action(action)
                for keyword, action in keyword_actions.items()
                if keyword in text.lower()
            )

            # await asyncio.gather(*action_tasks)
            for task in action_tasks:
                await task  # 改为顺序执行而非并行
            logger.info("所有任务执行完成")

        except Exception as e:
            logger.error(f"处理消息异常: {str(e)}")
            observe.start()  # 异常后重新启动监听

    # 同步处理器保持简单
    def sync_handler(msg):
        if main_loop and not main_loop.is_closed():
            asyncio.run_coroutine_threadsafe(handler(msg), main_loop)

    observe.set_handler(sync_handler)
    observe.start()
    logger.info("语音监听已启动")


if __name__ == '__main__':
    MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(tts_worker())  # 取消注释
        device: WiFiDevice = loop.run_until_complete(test_get_device_by_name())
        if device:
            loop.run_until_complete(test_connect(device))
            loop.run_until_complete(test_start_run_program())
            loop.run_until_complete(test_speech_recognise())
            loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        loop.run_until_complete(shutdown())
        loop.close()
