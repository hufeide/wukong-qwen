#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from http import HTTPStatus
import os
import aiohttp
import json
import logging
from dotenv import load_dotenv
import time
import dashscope  # 在文件开头导入 dashscope 库

# 获取logger
logger = logging.getLogger("deepseek语音助手")

class DeepSeekClient:
    """使用DeepSeek V3 API的客户端封装"""
    
    def __init__(self):
        """初始化DeepSeek V3客户端"""
        load_dotenv()
        
        # 获取API密钥
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key:
            # 尝试处理可能的Unicode BOM问题
            for key in os.environ.keys():
                if "QWEN_API_KEY" in key:
                    api_key = os.environ[key]
                    logger.info(f"找到API密钥: {key[:5]}...")
                    break
        
        if not api_key:
            logger.error("DEEPSEEK_API_KEY环境变量未设置")
            raise ValueError("DEEPSEEK_API_KEY环境变量未设置")
            
        self.api_key = api_key
        
        # 获取API基础URL，默认使用官方文档中的URL
        self.api_base = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        # 确保api_base不以/结尾
        if self.api_base.endswith("/"):
            self.api_base = self.api_base[:-1]
        
        # 模型名称，默认为deepseek (DeepSeek)
        self.model = os.getenv("QWEN_MODEL", "qwen-plus")
        
        logger.info(f"DeepSeek配置: API Base: {self.api_base}, 模型: {self.model}")
        logger.info("DeepSeek客户端初始化成功")
        
        # 系统提示词 - 用于引导模型以适当的方式回答
        self.system_prompt = (
            "你是deepseek语音助手，一个友好、专业的人工智能助手。"
            "请提供简洁、准确、有用的回答。"
            "回答应该是自然的口语化表达，适合语音播报。"
            "避免使用长句和复杂术语，尽量使用简单词汇。"
            "不要列出项目符号或格式化文本，所有回答应该是连贯的语音流。"
            "你的回答应该简明扼要，避免冗长的开场白或结束语。"
            "如果无法回答某个问题，请直接说明无法提供该信息，不要提供不准确的答案。"
        )
    
    async def get_response(self, query):
        """获取单次查询的回复"""
        return await self._call_api([
             {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
            # {"role": "system", "content": self.system_prompt},
            # {"role": "user", "content": query}
        ])
    
    async def get_response_with_history(self, conversation_history):
        """使用对话历史获取回复"""
        # 创建完整的对话历史，包括系统提示
        messages = [{"role": "system", "content": self.system_prompt}]
        # 如果已提供了system角色，则不再添加
        if len(conversation_history) > 0 and conversation_history[0].get("role") == "system":
            messages = conversation_history
        else:
            messages.extend(conversation_history)
        
        return await self._call_api(messages)
    
    async def _call_api(self, messages):
        """Call the DeepSeek V3 API and return the generated response text"""
        dashscope.api_key = self.api_key  # Set the API key
        try:
            start_time = time.time()
            # Use the dashscope client to call the API
            response = dashscope.Generation.call(
                model=self.model,  # Use the configured model name
                messages=messages,
                temperature=0.7,  # Control creativity, 0.7 is a balanced value
                max_tokens=1000,  # Maximum number of generated tokens
                top_p=0.95,  # Control diversity
                stream=False  # Do not use streaming response
            )
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000)
            logger.info(f"API response status code: {response.status_code}, response time: {response_time}ms")
            # logger.debug(f"Raw response: {response.to_dict()[:500]}...")
        
            if HTTPStatus.OK.value!=200:
                logger.error(f"DeepSeek API returned an error: {response.status_code}, {response.to_dict()[:500]}")
                # Try to parse error details
                try:
                    print("error")
                    # error_data = response.to_dict()
                    # if 'error' in error_data:
                    #     error_detail = error_data['error']
                    #     logger.error(f"Error details: {error_detail}")
                except:
                    pass
                return "Sorry, I encountered a technical issue and cannot answer your question. Please try again later."
        
            try:
                result = response.output.get("text","")
            except Exception as e:
                logger.error(f"Failed to parse API response: {str(e)}")
                return "Sorry, I received an invalid response format. Please try again later."
        
            # if not result.get("output") or not result["output"].get("text"):
            #     logger.error(f"DeepSeek API returned an invalid result: {result}")
            #     return "Sorry, I cannot generate a valid response."
        
            # Extract the generated response text
            content = result
        
            # Record token usage information
            # if "usage" in result:
            #     usage = result["usage"]
            #     logger.info(f"Token usage: input={usage.get('input_tokens', 'unknown')}, "
            #                 f"output={usage.get('output_tokens', 'unknown')}, "
            #                 f"total={usage.get('total_tokens', 'unknown')}")
        
            # Simple cleaning to ensure it's suitable for voice output
            content = content.replace("\n", " ").strip()
        
            logger.info(f"Received DeepSeek response: {content[:100]}...")
            return content
        
        except Exception as e:
            logger.error(f"An error occurred while calling the DeepSeek API: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Detailed error: {traceback.format_exc()}")
            return "Sorry, I'm temporarily unable to connect to the server. Please try again later."

# 简单测试函数
async def test_deepseek_client():
    """测试DeepSeek客户端功能"""
    try:
        client = DeepSeekClient()
        logger.info("测试单轮对话...")
        response = await client.get_response("今天天气怎么样？")
        logger.info(f"单轮对话回复: {response}")
        
        logger.info("测试多轮对话...")
        conversation = [
            {"role": "user", "content": "你好，请介绍一下自己"},
            {"role": "assistant", "content": "你好！我是DeepSeek语音助手，一个基于DeepSeek V3模型的AI助手。有什么我可以帮助你的吗？"},
            {"role": "user", "content": "今天是几号？"}
        ]
        response2 = await client.get_response_with_history(conversation)
        logger.info(f"多轮对话回复: {response2}")
        
        return response
    except Exception as e:
        logger.error(f"测试DeepSeek客户端时出错: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,  # 测试时使用DEBUG级别
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import asyncio
    
    # 测试
    asyncio.run(test_deepseek_client()) 