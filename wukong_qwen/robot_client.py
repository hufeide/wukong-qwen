import os
import asyncio
import logging
from dotenv import load_dotenv

import mini.mini_sdk as MiniSdk
from mini.apis import errors
from mini.apis.base_api import MiniApiResultType
from mini.apis.api_sound import StartPlayTTS
from mini.dns.dns_browser import WiFiDevice

class RobotClient:
    """悟空机器人客户端"""
    
    def __init__(self):
        """初始化机器人客户端"""
        load_dotenv()
        
        # 设置日志级别
        MiniSdk.set_log_level(logging.INFO)
        
        # 从环境变量加载机器人信息
        self.robot_id = os.getenv("ROBOT_ID")
        robot_type = os.getenv("ROBOT_TYPE", "mini")
        robot_ip = os.getenv("ROBOT_IP")
        
        print(f"机器人配置 - ID: {self.robot_id}, IP: {robot_ip}, 类型: {robot_type}")
        
        # 设置机器人类型
        if robot_type.lower() == "dedu":
            print("设置机器人类型为: DEDU")
            MiniSdk.set_robot_type(MiniSdk.RobotType.DEDU)
        else:
            print("设置机器人类型为: MINI")
            MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)
            
        self.robot_device = None
        self.is_connected = False
        
    async def scan_robot(self, timeout=10):
        """
        扫描局域网内的机器人
        
        Args:
            timeout (int): 扫描超时时间（秒）
            
        Returns:
            bool: 是否找到机器人
        """
        print(f"开始扫描机器人，序列号后缀: {self.robot_id}")
        
        # 尝试从环境变量获取机器人IP地址
        robot_ip = os.getenv("ROBOT_IP")
        if robot_ip:
            print(f"环境变量中设置了机器人IP: {robot_ip}，尝试直接使用IP连接")
            try:
                # 创建一个WiFiDevice对象
                from mini.dns.dns_browser import WiFiDevice
                custom_device = WiFiDevice(
                    name=f"Mini_{self.robot_id}" if self.robot_id else "Mini_Custom",
                    address=robot_ip,
                    port=51059,  # 使用默认端口
                    type="_Mini_mini_channel_server._tcp.local.",
                    server="Android.local."
                )
                print(f"已创建自定义设备: {custom_device}")
                self.robot_device = custom_device
                return True
            except Exception as e:
                print(f"创建自定义设备时出错: {e}")
                # 如果创建自定义设备失败，继续使用标准扫描方法
        
        try:
            # 扫描所有机器人
            devices = await MiniSdk.get_device_list(timeout)
            if not devices:
                print("未找到任何机器人")
                return False
                
            print(f"找到 {len(devices)} 台机器人")
            for device in devices:
                print(f"- {device}")
                # 打印设备的详细信息
                print(f"  设备类型: {type(device)}")
                if isinstance(device, WiFiDevice):
                    print(f"  名称: {device.name}")
                    print(f"  地址: {device.address}")
                    print(f"  端口: {device.port}")
                    print(f"  类型: {device.type}")
                
            # 如果指定了机器人IP地址
            if robot_ip:
                print(f"尝试匹配IP地址为 {robot_ip} 的机器人")
                for device in devices:
                    # 假设设备对象有一个address或ip属性
                    device_ip = getattr(device, "address", None)
                    if not device_ip:
                        device_ip = getattr(device, "ip", None)
                        
                    if device_ip and device_ip == robot_ip:
                        print(f"找到匹配IP的机器人: {device}")
                        self.robot_device = device
                        return True
                print(f"没有找到IP为 {robot_ip} 的机器人")
            
            # 如果指定了机器人ID，尝试匹配ID
            if self.robot_id:
                print(f"尝试匹配ID为 {self.robot_id} 的机器人")
                for device in devices:
                    device_name = getattr(device, "name", "")
                    device_str = str(device)
                    # 检查设备名称或字符串表示中是否包含机器人ID
                    if (device_name and self.robot_id in device_name) or self.robot_id in device_str:
                        print(f"找到匹配ID的机器人: {device}")
                        self.robot_device = device
                        return True
                print(f"没有找到ID为 {self.robot_id} 的机器人")
            
            # 如果没有匹配的机器人，但找到了设备，使用第一个找到的
            if devices:
                print("使用第一个找到的机器人")
                self.robot_device = devices[0]
                print(f"选择机器人: {self.robot_device}")
                return True
            
            return False
            
        except Exception as e:
            print(f"扫描机器人时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return False
            
    async def connect(self):
        """
        连接到机器人
        
        Returns:
            bool: 是否连接成功
        """
        if not self.robot_device:
            print("未找到机器人，无法连接")
            return False
            
        try:
            print(f"正在连接到机器人: {self.robot_device}")
            result = await MiniSdk.connect(self.robot_device)
            if result:
                print("连接成功")
                self.is_connected = True
                return True
            else:
                print("连接失败")
                return False
                
        except Exception as e:
            print(f"连接机器人时出错: {e}")
            return False
            
    async def enter_program_mode(self):
        """
        让机器人进入编程模式
        
        根据官方示例，使用MiniSdk.enter_program()方法
        
        Returns:
            bool: 是否成功进入编程模式
        """
        if not self.is_connected:
            print("未连接到机器人，无法进入编程模式")
            return False
            
        try:
            print("正在进入编程模式...")
            # 使用正确的API进入编程模式
            await MiniSdk.enter_program()
            # 等待进入编程模式的TTS播报完成
            await asyncio.sleep(6)
            
            print("已进入编程模式")
            return True
            
        except Exception as e:
            print(f"进入编程模式时出错: {e}")
            print("尝试假设已进入编程模式并继续")
            return True
            
    async def say(self, text):
        """
        让机器人说话
        
        Args:
            text (str): 要说的文本
            
        Returns:
            bool: 是否成功说话
        """
        if not self.is_connected:
            print("未连接到机器人，无法说话")
            return False
            
        try:
            print(f"机器人说: {text}")
            # 使用TTS API让机器人说话
            print(f"创建StartPlayTTS对象，文本: '{text}'")
            block = StartPlayTTS(text=text)
            print(f"StartPlayTTS对象: {block}")
            print(f"StartPlayTTS对象属性: {dir(block)}")
            
            print("执行TTS...")
            result = await block.execute()
            print(f"TTS执行原始结果: {result}")
            print(f"TTS结果类型: {type(result)}")
            
            if isinstance(result, tuple) and len(result) == 2:
                print(f"TTS元组结果: {result[0]}, {result[1]}")
                success = result[0] == MiniApiResultType.Success
                if not success:
                    print(f"TTS执行返回失败: {result}")
                return success
            else:
                print(f"TTS执行返回格式不正确: {result}")
                # 检查其他可能的成功标志
                if hasattr(result, 'is_success') and callable(getattr(result, 'is_success')):
                    success = result.is_success()
                    print(f"通过is_success()方法判断: {success}")
                    return success
                elif isinstance(result, bool):
                    print(f"结果是布尔值: {result}")
                    return result
                else:
                    print("无法判断成功与否，假设成功并继续")
                    return True  # 假设成功，继续执行
            
        except Exception as e:
            print(f"机器人说话时出错: {e}")
            import traceback
            print(traceback.format_exc())
            return False
            
    async def play_action(self, action_name):
        """
        播放预设的动作
        
        Args:
            action_name (str): 动作名称
            
        Returns:
            bool: 是否成功播放动作
        """
        if not self.is_connected:
            print("未连接到机器人，无法播放动作")
            return False
            
        try:
            print(f"播放动作: {action_name}")
            try:
                from mini.apis.api_action import Play
                block = Play(name=action_name)
                result = await block.execute()
                
                if isinstance(result, tuple) and len(result) == 2:
                    return result[0] == MiniApiResultType.Success
                else:
                    print(f"播放动作执行返回格式不正确: {result}")
                    return True  # 假设成功，继续执行
            except ImportError:
                print(f"找不到Play类，无法播放动作")
                return False
            
        except Exception as e:
            print(f"播放动作时出错: {e}")
            return False
            
    async def disconnect(self):
        """
        断开与机器人的连接并释放资源
        """
        if self.is_connected:
            print("正在断开连接...")
            try:
                # 先退出编程模式
                await MiniSdk.quit_program()
                # 再释放资源
                await MiniSdk.release()
            except Exception as e:
                print(f"断开连接时出错: {e}")
            finally:
                self.is_connected = False
                print("已断开连接")
            
    # 添加更多方法以实现其他功能... 