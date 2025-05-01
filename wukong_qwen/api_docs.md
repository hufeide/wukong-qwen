# 悟空机器人API文档

## 基本API

### 语音识别相关

`ObserveSpeechRecognise` 类用于监听语音识别。

主要方法：
- `start()`: 开始监听语音输入（非异步方法）
- `stop()`: 停止监听
- `set_handler(callback)`: 设置处理语音识别结果的回调函数

### 语音合成相关

`StartPlayTTS` 类用于让机器人说话。

```python
tts = StartPlayTTS(text="要说的文本")
result = await tts.execute()
```

返回值是一个元组 `(MiniApiResultType, data)`，其中 `MiniApiResultType.Success` 表示成功。

### 机器人连接相关

```python
# 设置机器人类型
MiniSdk.set_robot_type(MiniSdk.RobotType.MINI)  # 或 MiniSdk.RobotType.DEDU

# 获取设备列表
devices = await MiniSdk.get_device_list(timeout)

# 连接设备
result = await MiniSdk.connect(device)

# 进入编程模式
await MiniSdk.enter_program()

# 退出编程模式
await MiniSdk.quit_program()

# 断开连接和释放资源
await MiniSdk.release()
```

## 语音监听原理

`ObserveSpeechRecognise` 类负责接收机器人的语音识别结果。语音识别发生在机器人内部，机器人会将识别结果通过网络发送给程序。

语音监听的工作流程：
1. 创建 `ObserveSpeechRecognise` 对象
2. 使用 `set_handler()` 设置回调函数
3. 调用 `start()` 开始监听
4. 回调函数将在有语音识别结果时被调用

注意：语音识别是在机器人内部进行的，而非在电脑上。机器人会自动监听周围环境的语音，当检测到人说话时进行识别，然后将识别结果通过网络发送给程序。

### 示例回调函数

```python
async def on_asr_result(text):
    """处理语音识别结果的回调函数"""
    if not text:
        return
    
    print(f"识别到语音: {text}")
    # 处理逻辑...
``` 