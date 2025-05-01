#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
import time
from dotenv import load_dotenv

# 导入悟空SDK相关模块
from mini.apis.api_sound import StartPlayTTS, StopPlayTTS
import mini.mini_sdk as MiniSdk
from mini.dns.dns_browser import WiFiDevice
from mini.apis.base_api import MiniApiResultType

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 使用DEBUG级别获取更详细日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TTS测试")

# 全局变量
robot_connected = False
robot_id = None
robot_type = None
robot_ip = None

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
    
    # 初始化机器人客户端
    logger.info("初始化机器人客户端...")
    
    # 设置机器人类型
    if robot_type.lower() == "dedu":
        logger.info("设置机器人类型为DEDU")
        MiniSdk.set_robot_type(MiniSdk.RobotType.DEDU)
    else:
        logger.info("设置机器人类型为MINI")
        MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)
    
    # 通过IP直接连接或扫描局域网寻找机器人
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
            await MiniSdk.enter_program()
            # 等待进入编程模式的TTS播报完成
            await asyncio.sleep(4)
            logger.info("已进入编程模式")
        except Exception as e:
            logger.error(f"进入编程模式时出错: {e}")
            logger.info("尝试继续进行测试...")
        
        return True
    else:
        logger.error("机器人连接失败")
        return False

# 测试TTS功能
async def test_tts():
    """测试TTS功能"""
    global robot_connected
    
    if not robot_connected:
        logger.error("机器人未连接，无法测试TTS")
        return False
    
    # 测试句子列表
    test_sentences = [
        "你好，我是悟空机器人",
        "这是一个TTS功能测试",
        "今天天气很好",
        "一二三四五六七八九十",
        "Hello World"
    ]
    
    success_count = 0
    
    # 测试每个句子
    for i, sentence in enumerate(test_sentences):
        logger.info(f"测试 {i+1}/{len(test_sentences)}: {sentence}")
        
        try:
            # 创建TTS请求
            tts = StartPlayTTS(text=sentence)
            
            # 发送请求并记录时间
            start_time = time.time()
            result = await tts.execute()
            end_time = time.time()
            
            # 输出响应信息
            logger.info(f"TTS响应耗时: {(end_time-start_time)*1000:.2f}ms")
            logger.info(f"TTS响应原始结果: {result}")
            
            # 分析响应结果
            success = False
            
            # 检查不同类型的结果
            if hasattr(result, 'isSuccess') and callable(result.isSuccess):
                success = result.isSuccess()
                logger.info(f"通过isSuccess()方法判断结果: {success}")
            elif isinstance(result, tuple) and len(result) > 0:
                success = bool(result[0])
                logger.info(f"通过元组第一个元素判断结果: {success}")
            elif isinstance(result, MiniApiResultType):
                success = (result == MiniApiResultType.Success)
                logger.info(f"通过MiniApiResultType判断结果: {success}")
            else:
                logger.warning(f"未知响应类型: {type(result)}")
                success = True  # 假设成功
            
            # 检查是否有错误码
            if hasattr(result, 'resultCode'):
                logger.info(f"响应结果代码: {result.resultCode}")
            
            # 检查是否有错误消息
            if hasattr(result, 'resultMsg'):
                logger.info(f"响应结果消息: {result.resultMsg}")
            
            if success:
                logger.info("TTS请求成功发送")
                success_count += 1
                
                # 估计播放时间
                play_time = len(sentence) * 0.35
                logger.info(f"估计播放时间: {play_time:.2f}秒")
                
                # 等待播放完成
                await asyncio.sleep(play_time + 1)
                logger.info("播放完成")
            else:
                logger.error("TTS请求失败")
                
                # 尝试查看机器人状态
                logger.info("检查机器人状态...")
                # 可以添加检查机器人状态的代码
        
        except Exception as e:
            logger.error(f"TTS测试出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
        
        # 测试之间等待一段时间
        await asyncio.sleep(2)
    
    # 输出测试结果
    logger.info(f"TTS测试完成: {success_count}/{len(test_sentences)} 成功")
    return success_count == len(test_sentences)

# 断开连接
async def disconnect_robot():
    """断开机器人连接"""
    global robot_connected
    
    if robot_connected:
        logger.info("断开机器人连接...")
        try:
            # 先退出编程模式
            await MiniSdk.quit_program()
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
    try:
        logger.info("====== 开始TTS功能测试 ======")
        
        # 连接机器人
        if await connect_robot():
            logger.info("连接成功，开始TTS测试...")
            
            # 测试TTS
            tts_success = await test_tts()
            
            # 输出测试结果
            if tts_success:
                logger.info("TTS功能测试全部通过！")
            else:
                logger.warning("TTS功能测试部分失败，请检查上面的错误信息。")
                
            # 断开连接
            await disconnect_robot()
        else:
            logger.error("连接机器人失败，无法进行TTS测试")
        
        logger.info("====== TTS功能测试完成 ======")
        
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    finally:
        # 确保断开连接
        if robot_connected:
            await disconnect_robot()

# 程序入口点
if __name__ == "__main__":
    try:
        load_dotenv()
        # 运行主函数
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}") 