import os
import aiohttp
import json
import logging
from dotenv import load_dotenv

logger = logging.getLogger("DeepSeekClient")

class DeepSeekClient:
    """DeepSeek API客户端，用于连接DeepSeek V3大模型"""
    
    def __init__(self):
        """初始化DeepSeek客户端"""
        load_dotenv()
        
        # 打印环境变量用于调试
        logger.debug(f"所有环境变量键: {list(os.environ.keys())}")
        
        # 处理可能带有BOM的环境变量
        api_key = None
        for key in os.environ.keys():
            # 尝试匹配任何包含DEEPSEEK_API_KEY的键（可能带有BOM）
            if "DEEPSEEK_API_KEY" in key:
                logger.info(f"找到包含DEEPSEEK_API_KEY的键: {key}")
                api_key = os.environ[key]
                break
                
        if not api_key:
            # 尝试标准方式获取
            api_key = os.getenv("DEEPSEEK_API_KEY")
        
        # 检查环境变量是否存在
        if not api_key:
            raise ValueError("未设置DEEPSEEK_API_KEY环境变量")
        
        # 存储API密钥和基础URL
        self.api_key = api_key
        self.base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        logger.info(f"DeepSeek客户端已初始化，使用模型: {self.model}")
        logger.info(f"API基础URL: {self.base_url}")
        
        # 对话历史
        self.conversation_history = []
        
        # 系统提示词
        self.system_prompt = """你是悟空机器人的AI助手，由DeepSeek团队训练的大型语言模型提供支持。
用自然、友好的语气回答用户问题，不要太啰嗦，除非用户要求详细解释。
如果不确定或不知道某个问题的答案，要诚实地承认，不要编造信息。
请记住你是一个真实机器人的声音，你可以看、可以听、可以说话，但不能直接移动或操作物体。
用户是通过语音与你交流的，所以保持回答简洁明了。"""
        
    async def get_response(self, user_input):
        """
        获取DeepSeek大模型的回复
        
        Args:
            user_input (str): 用户输入的文本
            
        Returns:
            str: DeepSeek大模型的回复文本
        """
        # 添加用户输入到对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 如果对话历史太长，进行裁剪
        if len(self.conversation_history) > 10:
            # 保留系统消息和最近的9条对话
            self.conversation_history = self.conversation_history[-9:]
        
        try:
            # 构建完整消息历史，包括系统提示
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history)
            
            # 构建请求数据
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.95,
                "max_tokens": 1000
            }
            
            logger.debug(f"发送请求到DeepSeek API: {json.dumps(data, ensure_ascii=False)}")
            
            # 发送API请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/chat/completions", 
                                        headers=headers, 
                                        json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API请求失败，状态码: {response.status}, 错误: {error_text}")
                        return f"抱歉，我暂时无法回答你的问题，请稍后再试。(错误码: {response.status})"
                    
                    result = await response.json()
                    logger.debug(f"API响应: {json.dumps(result, ensure_ascii=False)}")
                    
                    # 解析响应
                    if "choices" in result and len(result["choices"]) > 0:
                        reply = result["choices"][0]["message"]["content"]
                        # 添加AI回复到对话历史
                        self.conversation_history.append({"role": "assistant", "content": reply})
                        return reply
                    else:
                        logger.error(f"API响应格式不正确: {result}")
                        return "抱歉，我遇到了一些问题，无法理解你的问题。请稍后再试。"
                        
        except Exception as e:
            logger.error(f"调用DeepSeek API时出错: {str(e)}")
            return f"抱歉，发生了一个错误: {str(e)}"
            
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []
        logger.info("对话历史已重置") 