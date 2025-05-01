# 悟空机器人 + DeepSeek R1 部署说明

## 环境要求
- Python 3.8或更高版本
- Windows 10/11系统（推荐）或MacOS
- 稳定的网络连接（用于连接DeepSeek API）
- 悟空机器人（支持"悟空mini"或"悟空得度"型号）

## 安装步骤

### 1. 克隆或下载项目
将项目代码下载到本地计算机。

### 2. 创建虚拟环境
为避免依赖冲突，建议使用Python虚拟环境：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows PowerShell）
.\venv\Scripts\Activate.ps1

# 激活虚拟环境（Windows CMD）
.\venv\Scripts\activate.bat

# 激活虚拟环境（MacOS/Linux）
source venv/bin/activate
```

### 3. 安装依赖
使用国内镜像源安装依赖：

```bash
# 安装基本依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装特定版本的protobuf（适配悟空SDK）
pip install protobuf==3.20.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 配置环境变量
1. 在项目根目录创建`.env`文件
2. 参考`.env.example`文件，填写必要的环境变量：

```
# DeepSeek API配置
DEEPSEEK_API_KEY=您的DeepSeek API密钥
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 机器人配置
ROBOT_ID=您机器人的ID（在机器人底部或设置中查看）
ROBOT_TYPE=mini或dedu（根据您的机器人型号）
ROBOT_IP=192.168.xx.xx（机器人的IP地址，通常可以在悟空App中查看）

# 模拟模式设置
SIMULATION_MODE=false或true（是否使用模拟模式）
```

## 使用方式

### 正常模式（使用实际机器人）
1. 确保机器人已开机并连接到与电脑相同的WiFi网络
2. 在`.env`文件中设置`SIMULATION_MODE=false`
3. 运行主程序：

```bash
python main.py
```

4. 程序会尝试连接到指定IP的机器人
5. 连接成功后，机器人将进入编程模式，并开始监听语音输入
6. 对着机器人说话，等待DeepSeek处理并通过机器人回答

### 模拟模式（无需实际机器人）
1. 在`.env`文件中设置`SIMULATION_MODE=true`
2. 运行主程序：

```bash
python main.py
```

3. 程序会模拟机器人的行为，并打印出调试信息
4. 在控制台中可以看到模拟的语音输入和DeepSeek的回复

## 故障排除

### 连接问题
- 确保机器人和电脑在同一个WiFi网络
- 验证`.env`文件中的机器人IP地址是否正确
- 尝试在机器人上重启WiFi连接

### API问题
- 确认DeepSeek API密钥是否正确
- 检查网络连接是否稳定
- 查看API调用限制是否已达到

### SDK版本问题
如果遇到SDK相关错误，可能是由于版本不兼容：
```bash
# 卸载当前版本
pip uninstall alphamini

# 安装特定版本
pip install alphamini==1.2.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 高级配置

### 修改模拟输入
可以编辑`main.py`中的`simulate_speech_input`函数，自定义模拟的语音输入内容：

```python
def simulate_speech_input(deepseek_client):
    # 在这里修改模拟的语音输入内容
    test_inputs = [
        "你好，你能做什么？",
        "今天天气怎么样？",
        "讲个笑话"
    ]
    
    for input_text in test_inputs:
        print(f"模拟语音输入: {input_text}")
        # 处理模拟输入...
```

### 调整DeepSeek参数
可以修改`deepseek_client.py`中的DeepSeek API调用参数，如温度、最大响应长度等。

## 注意事项
- 机器人连接成功后会自动进入编程模式，此时机器人的原有功能会被暂停
- 退出程序时，机器人会自动退出编程模式，恢复正常功能
- 模拟模式下不会实际控制机器人，仅用于测试程序逻辑 