#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import time
from dotenv import load_dotenv

# 导入悟空SDK相关模块
from mini.apis.api_sound import StartPlayTTS, StopPlayTTS
from mini.apis.api_observe import ObserveSpeechRecognise
import mini.mini_sdk as MiniSdk
from mini.dns.dns_browser import WiFiDevice
from mini.apis.base_api import MiniApiResultType
from mini.pb2.codemao_speechrecognise_pb2 import SpeechRecogniseResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("语音识别测试")

# 全局变量
robot_connected = False
robot_id = None
robot_type = None
robot_ip = None
voice_listener = None
running = True
sentence_pause_timeout = 1.0  # 句子停顿超时（秒）
current_sentence = ""  # 当前收集的句子
last_speech_time = 0  # 上次接收语音时间
sentence_timeout_task = None  # 句子超时任务
is_tts_playing = False  # TTS是否正在播放

# 连接机器人
async def connect_robot():
    """连接到悟空机器人"""
    global robot_connected, robot_id, robot_type, robot_ip
    
    # 加载环境变量
    load_dotenv()
    
    # 获取机器人配置
    robot_id = os.getenv("ROBOT_ID")
    robot_type = os.getenv("ROBOT_TYPE", "mini")
    robot_ip = os.getenv("ROBOT_IP")
    
    logger.info(f"机器人配置: ID={robot_id}, 类型={robot_type}, IP={robot_ip}")
    
    # 设置机器人类型
    if robot_type.lower() == "dedu":
        logger.info("设置机器人类型为DEDU")
        MiniSdk.set_robot_type(MiniSdk.RobotType.DEDU)
    else:
        logger.info("设置机器人类型为MINI")
        MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)
    
    # 通过IP直接连接机器人
    if robot_ip:
        # 直接通过IP连接
        logger.info(f"尝试通过IP连接机器人: {robot_ip}")
        try:
            # 创建WiFiDevice对象
            device_name = f"Mini_030006KFK18082700{robot_id}" if robot_id else "Mini_Device"
            device = WiFiDevice(
                name=device_name,
                address=robot_ip,
                port=51059,  # 使用默认端口
                s_type="_Mini_mini_channel_server._tcp.local.",
                server="Android.local."
            )
            logger.info(f"已创建WiFiDevice: {device}")
            
            # 连接设备
            logger.info("连接设备...")
            result = await MiniSdk.connect(device)
            logger.info(f"连接结果: {result}")
            robot_connected = result
        except Exception as e:
            logger.error(f"创建设备对象或连接时出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    else:
        # 扫描网络寻找机器人
        logger.info("扫描网络寻找机器人...")
        try:
            devices = await MiniSdk.get_device_list(10)
            logger.info(f"发现设备: {devices}")
            
            # 检查是否找到设备
            if not devices:
                logger.error("未发现机器人设备，请检查网络连接")
                return False
            
            # 查找匹配ID的设备
            target_device = None
            
            if robot_id:
                # 通过ID查找设备
                logger.info(f"通过ID查找设备: {robot_id}")
                for device in devices:
                    device_name = getattr(device, "name", "")
                    logger.info(f"检查设备: {device_name}")
                    
                    if device_name and robot_id in device_name:
                        logger.info(f"找到匹配设备: {device_name}")
                        target_device = device
                        break
            
            # 如果未找到指定ID的设备，使用第一个设备
            if not target_device and devices:
                target_device = devices[0]
                logger.info(f"使用第一个发现的设备: {target_device}")
            
            # 连接设备
            if target_device:
                result = await MiniSdk.connect(target_device)
                logger.info(f"连接结果: {result}")
                robot_connected = result
            else:
                logger.error("未找到可用设备")
                return False
        except Exception as e:
            logger.error(f"扫描和连接过程中出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    # 确认连接状态
    if robot_connected:
        logger.info("机器人连接成功！")
        
        # 进入编程模式
        logger.info("进入编程模式...")
        try:
            result = await MiniSdk.enter_program()
            logger.info(f"进入编程模式结果: {result}")
            # 等待进入编程模式的TTS播报完成
            await asyncio.sleep(3)
            logger.info("已进入编程模式")
        except Exception as e:
            logger.error(f"进入编程模式时出错: {e}")
            logger.info("尝试继续进行测试...")
        
        return True
    else:
        logger.error("机器人连接失败")
        return False

# 设置语音识别
async def setup_speech_recognition():
    """设置语音识别，使用事件驱动模式"""
    global voice_listener
    
    try:
        logger.info("初始化语音识别...")
        
        # 创建语音识别对象
        voice_listener = ObserveSpeechRecognise()
        
        # 设置回调处理函数
        voice_listener.set_handler(on_speech_result)
        
        # 启动语音识别
        start_result = voice_listener.start()
        logger.info(f"语音识别启动结果: {start_result}")
        
        # 等待语音识别服务启动
        await asyncio.sleep(1)
        
        # 无需轮询，事件驱动模式下回调函数会自动处理语音识别结果
        logger.info("语音识别准备就绪，进入事件驱动监听模式")
        
        return True
    except Exception as e:
        logger.error(f"语音识别初始化失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

# 暂停语音识别
def pause_speech_recognition():
    """暂停语音识别服务"""
    global voice_listener, is_tts_playing
    
    if voice_listener:
        try:
            is_tts_playing = True
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
    global voice_listener, is_tts_playing
    
    if voice_listener:
        try:
            logger.info("TTS播放结束，恢复语音识别服务")
            voice_listener.start()
            is_tts_playing = False
            return True
        except Exception as e:
            logger.error(f"恢复语音识别服务失败: {e}")
            return False
    return False

# 语音识别结果回调函数
def on_speech_result(msg: SpeechRecogniseResponse):
    """处理语音识别结果的回调函数"""
    global current_sentence, last_speech_time, sentence_timeout_task
    
    # 记录接收时间
    current_time = time.time()
    last_speech_time = current_time
    
    logger.info(f"收到语音识别消息: {msg}")
    
    # 提取文本内容
    text = str(msg.text) if hasattr(msg, 'text') else None
    
    if not text:
        logger.warning("无法从语音识别结果中提取文本内容")
        return
    
    logger.info(f"识别到的文本: '{text}'")
    
    # 添加到当前句子
    append_to_current_sentence(text)

# 添加文本到当前句子
def append_to_current_sentence(text):
    """添加新的文本片段到当前收集的句子"""
    global current_sentence, sentence_timeout_task
    
    # 添加空格和新文本
    if current_sentence:
        current_sentence += " " + text
    else:
        current_sentence = text
    
    logger.info(f"当前累积句子: '{current_sentence}'")
    
    # 取消现有的超时任务
    if sentence_timeout_task and not sentence_timeout_task.done():
        sentence_timeout_task.cancel()
    
    # 设置新的句子超时任务
    sentence_timeout_task = asyncio.create_task(process_sentence_after_timeout())

# 句子超时后处理
async def process_sentence_after_timeout():
    """等待指定时间后处理当前累积的句子"""
    global current_sentence
    
    try:
        # 等待句子停顿超时
        await asyncio.sleep(sentence_pause_timeout)
        
        # 检查是否有累积的句子
        if current_sentence:
            logger.info(f"句子停顿超时({sentence_pause_timeout}秒)，处理句子: '{current_sentence}'")
            
            # 处理句子
            await process_sentence(current_sentence)
            
            # 清空当前句子
            current_sentence = ""
            
    except asyncio.CancelledError:
        # 任务被取消，这是正常的
        pass
    except Exception as e:
        logger.error(f"处理句子超时任务出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

# 处理完整句子
async def process_sentence(text):
    """处理完整的句子，并通过TTS返回响应"""
    
    logger.info(f"处理完整句子: '{text}'")
    
    # 简单示例：根据输入内容生成响应
    response = generate_response(text)
    
    # 使用TTS播放响应
    await say_text(response)
    
    logger.info(f"已处理句子并播放响应: '{response}'")

# 生成响应
def generate_response(text):
    """根据输入生成简单响应"""
    text_lower = text.lower()
    
    # 示例响应规则
    if "你好" in text_lower or "hello" in text_lower:
        return "你好，我是语音助手，很高兴为你服务"
    
    elif "天气" in text_lower:
        return "今天天气晴朗，温度25度，适合外出活动"
    
    elif "时间" in text_lower:
        current_time = time.strftime("%H:%M", time.localtime())
        return f"现在的时间是{current_time}"
    
    elif "日期" in text_lower:
        current_date = time.strftime("%Y年%m月%d日", time.localtime())
        return f"今天是{current_date}"
    
    elif "笑话" in text_lower:
        return "一只狗走进一家酒吧，酒保问：'你会说话？'，狗说：'当然，我还会点酒呢'"
    
    elif "退出" in text_lower or "结束" in text_lower or "停止" in text_lower:
        # 设置退出标志
        global running
        running = False
        return "好的，程序即将退出，再见"
    
    else:
        return f"我听到了你说的'{text}'，请告诉我你需要什么帮助"

# 使用TTS播放文本
async def say_text(text):
    """使用TTS播放文本"""
    global is_tts_playing
    
    if not text or not text.strip():
        logger.warning("尝试播放空文本，已忽略")
        return
    
    if not robot_connected:
        logger.error("机器人未连接，无法播放TTS")
        return
    
    # 暂停语音识别，避免识别自己的声音
    pause_speech_recognition()
    
    logger.info(f"开始TTS播放: {text}")
    
    try:
        # 确保停止任何可能正在进行的TTS播放
        try:
            stop_tts = StopPlayTTS()
            await stop_tts.execute()
            logger.info("已停止之前的TTS播放")
            # 短暂等待确保停止完成
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"停止之前的TTS播放时出错: {e}")
        
        # 创建并发送TTS请求
        tts = StartPlayTTS(text=text)
        result = await tts.execute()
        
        # 输出原始响应结果用于调试
        logger.info(f"TTS响应: {result}")
        
        # 判断是否成功
        success = False
        if hasattr(result, 'isSuccess') and callable(result.isSuccess):
            success = result.isSuccess()
        elif isinstance(result, tuple) and len(result) > 0:
            success = bool(result[0])
        elif isinstance(result, MiniApiResultType):
            success = (result == MiniApiResultType.Success)
        else:
            success = True  # 假设成功
        
        if success:
            logger.info("TTS请求成功发送")
            
            # 估计播放时间 (汉字约500ms, 英文和数字约250ms)
            # 优化基础缓冲时间，根据文本长度动态调整
            base_time = 1.0  # 基础缓冲时间
            char_time = 0.25  # 每个字符的播放时间（稍微减少每字符时间）
            play_time = len(text) * char_time + base_time
            
            logger.info(f"估计TTS播放时间: {play_time:.2f}秒")
            
            # 等待播放完成
            await asyncio.sleep(play_time)
            logger.info("TTS播放完成")
            
            # 主动停止TTS播放，确保播放完全结束
            try:
                stop_tts = StopPlayTTS()
                await stop_tts.execute()
                logger.info("已主动停止TTS播放")
            except Exception as e:
                logger.warning(f"主动停止TTS播放时出错: {e}")
        else:
            logger.error("TTS请求失败")
            
    except Exception as e:
        logger.error(f"TTS播放出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    finally:
        # 短暂等待，确保TTS完全停止
        logger.info("等待0.5秒确保TTS完全停止")
        await asyncio.sleep(0.5)
        
        # 恢复语音识别
        resume_speech_recognition()
        
        # 加入日志确认已经恢复语音识别
        logger.info(f"已处理句子并播放响应: '{text}'")

# 断开连接
async def disconnect_robot():
    """断开机器人连接"""
    global robot_connected, voice_listener
    
    try:
        # 停止语音识别
        if voice_listener:
            try:
                voice_listener.stop()
                logger.info("语音识别已停止")
            except Exception as e:
                logger.error(f"停止语音识别时出错: {e}")
    except Exception as e:
        logger.error(f"处理语音识别器时出错: {e}")
    
    if robot_connected:
        logger.info("断开机器人连接...")
        try:
            # 先退出编程模式
            await MiniSdk.quit_program()
            logger.info("已退出编程模式")
            
            # 再释放资源
            await MiniSdk.release()
            robot_connected = False
            logger.info("机器人连接已断开")
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")
    
    return True

# 主函数
async def main():
    """主函数"""
    global running
    
    try:
        logger.info("====== 开始语音识别测试 ======")
        logger.info("无唤醒词模式：直接说话即可被识别")
        logger.info(f"句子停顿超时：{sentence_pause_timeout}秒")
        logger.info("TTS播放期间会暂停语音识别，避免识别自己的声音")
        
        # 连接机器人
        if await connect_robot():
            logger.info("机器人连接成功，开始语音识别测试...")
            
            # 设置语音识别
            if await setup_speech_recognition():
                logger.info("语音识别设置成功")
                
                # 播放欢迎语
                await say_text("语音识别测试开始，请直接对我说话，无需唤醒词")
                
                # 保持程序运行
                while running:
                    await asyncio.sleep(1)
                
                logger.info("程序运行结束")
            else:
                logger.error("语音识别设置失败")
        else:
            logger.error("连接机器人失败")
        
        logger.info("====== 语音识别测试完成 ======")
        
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    finally:
        # 确保断开连接
        await disconnect_robot()

# 程序入口点
if __name__ == "__main__":
    try:
        # 运行主函数
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}") 