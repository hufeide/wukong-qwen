# DeepSeek智能语音助手项目

## 需求

- 使用悟空机器人作为语音交互前端
- 支持两种工作模式：
  - **唤醒词模式**：使用"deepseek"等唤醒词激活系统
  - **无唤醒词模式**：直接识别完整句子并处理
- 集成DeepSeek V3 API实现智能对话
- 提供处理过程反馈（"我想想"），提升等待体验
- 仅处理完整句子，避免碎片输入
- 处理过程中不响应新的语音输入
- 提供语音识别结果等待机制，优化交互体验

## 设计

### 技术栈

- 前端：Wukong悟空机器人 Mini
- 后端：Python、DeepSeek API V3
- 通信：悟空SDK、Python-dotenv、aiohttp

### 架构

- 语音输入：悟空SDK语音识别模块
- 对话管理：异步处理、状态管理
- 语音输出：悟空SDK TTS模块
- AI对话：DeepSeek V3 API

## 已完成任务

- [x] 悟空SDK集成
- [x] DeepSeek V3 API集成
- [x] 语音唤醒功能
- [x] 关键词识别与响应
- [x] TTS语音播放
- [x] TTS播放期间忽略语音识别
- [x] 对话历史管理
- [x] 语音识别缓冲区管理
- [x] 动态调整语音识别轮询间隔
- [x] 实现无唤醒词模式，直接处理完整句子
- [x] 添加处理中反馈机制（"我想想"提示）
- [x] 实现完整句子判断逻辑
- [x] 实现处理中锁定机制，避免重复触发
- [x] 优化DeepSeek API调用日志，方便排查问题
- [x] 创建测试工具，验证DeepSeek API正常工作
- [x] 编写TTS专项测试程序，辅助TTS问题排查
- [x] 实现语音识别文本自动解码，转换Unicode编码
- [x] 修复TTS测试工具，使用正确的机器人初始化方法
- [x] 实现打断功能
- [x] 实现部分唤醒功能
- [x] 实现自声消除（在TTS播报期间不响应语音命令）
- [x] 优化语音缓冲区管理，添加超时机制
- [x] 优化语音片段合并功能
- [x] 重构语音识别架构，从轮询到事件驱动
- [x] 实现基于语音停顿的句子完成判断
- [x] 开发简单语音识别测试工具，纯事件驱动无唤醒词模式
- [x] 优化TTS播放控制，主动停止TTS播放避免重叠
- [x] TTS播放相关时间参数配置化，支持通过环境变量调整
- [x] 改进语音识别暂停和恢复机制，独立函数实现
- [x] 优化TTS播放完成后等待时间，减少不必要的延迟
- [x] 修复无唤醒词模式下语音输入被错误忽略的问题
- [x] 优化TTS播放控制逻辑，使用标志位控制而非估算时间
- [x] 完全移除唤醒词逻辑，使系统直接响应语音输入
- [x] 添加定期提醒功能的配置选项，可通过环境变量开关和调整间隔

## 待办任务

- [ ] 修复TTS播放问题
- [ ] 获取有效的DeepSeek API密钥
- [ ] 增加更多常见问题响应
- [ ] 添加情绪识别功能
- [ ] 实现更复杂的对话管理
- [ ] 支持多轮对话上下文保持

## 遇到的问题及解决方案

1. **TTS功能无法正常工作**
   - 问题：机器人TTS功能无声音输出
   - 解决方案：
     - 开发`test_tts.py`专项测试工具，详细分析TTS响应和状态码
     - 增强异常处理并添加重试机制
     - 添加响应类型判断，支持多种返回格式
     - 检查机器人音量设置和固件版本是否支持TTS

2. **环境变量读取问题**
   - 问题：.env文件中的变量读取错误，出现Unicode BOM问题
   - 解决：增强环境变量读取逻辑，添加BOM检测和处理

3. **WebSockets库冲突**
   - 问题：机器人SDK使用的websockets库版本冲突
   - 解决：锁定websockets库到兼容版本

4. **DeepSeek API调用失败**
   - 问题：API端点格式错误，请求参数传递问题，API验证失败
   - 解决方案：
     - 开发`test_deepseek_api.py`专用测试工具，全面验证API功能
     - 确保API密钥正确且包含"sk-"前缀，符合DeepSeek API要求
     - 确保API基础URL不以斜杠结尾，防止URL拼接错误
     - 完善错误处理逻辑，区分不同类型的API错误
     - 添加详细请求和响应日志，便于排查问题
     - 验证API可以正常处理单次请求、维持对话上下文和流式响应

5. **语音识别延迟问题**
   - 问题：语音识别轮询间隔太短，导致CPU占用高
   - 解决：实现动态调整轮询间隔，根据用户活动调整

6. **机器人自我识别问题**
   - 问题：机器人播放TTS时会识别自己的声音
   - 解决：TTS播放期间缓存语音识别结果，结束后再处理

7. **语音识别不完整问题**
   - 问题：系统处理碎片化语音输入，导致不必要的API调用
   - 解决方案：添加完整句子判断逻辑，只处理有意义的句子

8. **语音识别文本为Unicode编码**
   - 问题：日志中的语音识别文本显示为Unicode编码，难以阅读
   - 解决方案：
     - 开发`test_decode.py`测试工具，验证Unicode解码方法
     - 在`on_asr_result`函数中添加自动解码逻辑
     - 转换后记录可读的中文文本，方便检查语音识别结果

9. **处理过程中重复触发问题**
   - 问题：处理一个问题时，新的语音输入导致多次触发
   - 解决方案：添加处理锁定机制，在处理过程中忽略新的语音输入

10. **无唤醒词模式无法工作**
    - 问题：即使在.env中设置WAKE_WORD为空，系统仍要求使用唤醒词
    - 解决方案：
      - 修正`require_wake_word`的判断逻辑，使用`WAKE_WORD.strip() != ""`代替`bool(WAKE_WORD)`
      - 优化`is_complete_sentence`函数，为无唤醒词模式放宽判断标准
      - 增强语音识别结果解析，更好地处理不同格式的输入
      - 添加手动解析和Unicode解码逻辑，提高文本提取成功率
      - 重构语音处理流程，确保无唤醒词模式下能正确处理完整句子

11. **语音识别任务积累导致系统卡壳**
    - 问题：TTS播放期间积累的语音识别任务过多，导致处理队列越来越长，系统最终无响应
    - 解决方案：
      - 实现语音缓冲区超时机制，只处理最近N秒内的语音识别结果
      - 添加语音缓冲区大小限制，防止缓冲区无限增长
      - 为每条语音识别结果添加时间戳，方便过滤过期消息
      - 提供可配置参数调整缓冲区超时时间和最大大小
      - 优化缓冲区结构，使用字典存储消息内容和时间戳

12. **语音识别分段导致无法识别完整句子**
    - 问题：语音识别系统将一个完整句子拆分成多个小片段返回，系统对每个片段单独处理导致无法获取完整语义
    - 解决方案：
      - 实现语音片段合并功能，收集连续的语音片段后作为一个整体处理
      - 设置语音片段合并超时机制，在用户停止说话一段时间后处理积累的片段
      - 添加最大等待片段数限制，防止长时间不处理
      - 实现片段处理锁机制，避免并发处理造成混乱
      - 优化合并逻辑，去除重复内容和多余空格
      - 特殊处理唤醒词情况，检测到新唤醒词时先处理之前的片段

13. **无唤醒词模式问题**
    - 问题：设置了WAKE_WORD为空，但无唤醒词模式下语音输入仍被错误忽略
    - 解决方案：
      - 修复on_asr_result函数中的日志输出和处理逻辑
      - 确保无唤醒词模式下所有语音输入都会进入句子累积过程
      - 修复日志输出中的错误提示，避免混淆

14. **TTS播放控制逻辑问题**
    - 问题：使用估算时间来控制TTS播放过程，可能导致播放未完成时就恢复语音识别
    - 解决方案：
      - 使用标志位（tts_in_progress）控制语音识别的暂停和恢复
      - 主动调用StopPlayTTS确认TTS播放完成，而不依赖估算时间
      - 保留TTS_WAIT_TIME_AFTER_PLAY作为额外缓冲时间，确保平滑过渡
      - 优化暂停和恢复语音识别的函数，确保状态正确

## 测试工具

### speech_test_simple.py

专门设计的纯事件驱动式语音识别测试工具，主要特点：

- 无需唤醒词，直接进行语音交互
- 基于语音停顿自动判断句子完成（默认停顿1秒视为句子结束）
- 使用事件驱动架构，避免轮询带来的高CPU占用
- 支持简单的关键词识别和响应（包括时间、天气、笑话等）
- 语音片段自动合并，形成完整句子
- TTS播放期间自动暂停语音识别，避免机器人识别自己的声音
- 主动控制TTS播放过程，精确停止播放后立即恢复语音识别
- 通过StopPlayTTS实现精确控制，减少不必要的等待时间
- 详细的日志记录，便于排查问题
- 能够持续处理所有语音输入，不会忽略任何语音命令

使用方法：
```
python speech_test_simple.py
```

注意事项：
- 确保.env文件中配置了正确的机器人连接信息
- 可以通过修改代码中的`sentence_pause_timeout`参数调整句子停顿判断时间
- 说"退出"或"结束"可以结束程序

## DeepSeek API集成说明

DeepSeek API使用与OpenAI兼容的接口格式，关键配置如下：

```
# API基础URL
DEEPSEEK_API_BASE=https://api.deepseek.com

# API密钥（必须包含sk-前缀）
DEEPSEEK_API_KEY=sk-yourapikeyhere

# 模型名称
DEEPSEEK_MODEL=deepseek-chat
```

API调用流程：
1. 构建请求消息，包含system和user角色
2. 发送POST请求到`{DEEPSEEK_API_BASE}/v1/chat/completions`
3. 请求头包含`Authorization: Bearer {DEEPSEEK_API_KEY}`
4. 请求体包含model、messages、temperature等参数
5. 从响应中提取`choices[0].message.content`作为回复内容

## 配置说明

在`.env`文件中设置以下环境变量：

```
# DeepSeek API配置
DEEPSEEK_API_KEY=sk-yourapikeyhere
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 机器人配置
ROBOT_ID=00258
ROBOT_TYPE=mini
ROBOT_IP=192.168.50.3

# 功能开关
ENABLE_INTERRUPTION=true
ENABLE_THINKING_FEEDBACK=true
IGNORE_WAKE_DURING_TTS=true
# 是否启用定期提醒
ENABLE_PERIODIC_REMINDER=false
# 定期提醒间隔(分钟)
REMINDER_INTERVAL_MINUTES=10

# 语音缓冲区设置
SPEECH_BUFFER_TIMEOUT=5
MAX_SPEECH_BUFFER_SIZE=10

# 语音片段合并设置
ENABLE_FRAGMENT_MERGE=true
FRAGMENT_MERGE_TIMEOUT=1.5
MAX_WAIT_FRAGMENTS=5

# 句子判断和处理配置
MIN_SENTENCE_LENGTH=5
PROCESSING_LOCK_TIME=3
SENTENCE_PAUSE_TIMEOUT=1.0
SENTENCE_MAX_WAIT_TIME=10.0

# TTS播放配置
TTS_WAIT_TIME_AFTER_PLAY=0.5
TTS_CHAR_TIME=0.25
TTS_BASE_TIME=1.0
```

## 使用方法

1. 安装依赖：`pip install -r requirements.txt`
2. 配置`.env`文件：
   - 设置`DEEPSEEK_API_KEY`为有效的API密钥（必须包含sk-前缀）
   - 根据需要调整`ENABLE_PERIODIC_REMINDER`和`REMINDER_INTERVAL_MINUTES`
   - 设置`IGNORE_WAKE_DURING_TTS=true`以确保机器人不会对自己的语音作出反应
3. 运行主程序：`python main.py`
4. 直接对机器人说话，无需使用唤醒词
5. 当系统显示"我想想"时，表示正在处理请求，请等待回答