#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from openai import OpenAI
import os
import sys
import json
import logging
import asyncio
import requests
import time
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DeepSeek API测试")

class DeepSeekAPITester:
    """DeepSeek API测试类"""
    
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        # 获取API配置
        self.api_key = os.getenv("QWEN_API_KEY")
        self.api_base = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = os.getenv("QWEN_MODEL", "qwen-plus")
        
        # 确保API基础URL不以斜杠结尾
        if self.api_base.endswith('/'):
            self.api_base = self.api_base[:-1]
            
        logger.info(f"DeepSeek配置: API Base: {self.api_base}, 模型: {self.model}")
        
        # 验证API密钥
        if not self.api_key:
            logger.error("缺少DeepSeek API密钥，请在.env文件中设置DEEPSEEK_API_KEY")
            sys.exit(1)
            
        # 显示带掩码的API密钥前缀
        masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "****"
        logger.info(f"API密钥前缀: {masked_key}")
        
    async def test_single_prompt(self):
        """测试单个提示词"""
        prompt = "你好，请自我介绍一下"
        logger.info(f"测试单个提示词: '{prompt}'")
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=self.api_key, 
            base_url=self.api_base,
        )
        
        
        # 基本系统提示词
        system_prompt = "You are a helpful assistant."
        
        # 构建消息数组
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        
        # 发送请求
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                    model=self.model, # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                    messages=messages,
                    )
            end_time = time.time()
            
            # logger.info(f"API响应状态码: {response.status_code}, 响应时间: {int((end_time-start_time)*1000)}ms")
            
            # # 记录原始响应
            # logger.debug(f"原始响应: {response.text[:1000]}...")
            
            # 检查响应状态
            if 1==1:
                
                # 提取回复内容
                reply = response.choices[0].message.content
                
                logger.info(f"测试成功！API回复: {reply[:100]}..." if len(reply) > 100 else f"测试成功！API回复: {reply}")
                return True, reply
            else:
            
                
                return False, f"API请求失败: {response}"
                
        except Exception as e:
            logger.error(f"请求过程中出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False, f"请求出错: {str(e)}"
            
   
    
    async def test_streaming(self):
        """测试流式响应"""
        logger.info("测试流式响应功能")
        
        prompt = "你好，请自我介绍一下"
        logger.info(f"测试单个提示词: '{prompt}'")
        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
            api_key=self.api_key, 
            base_url=self.api_base,
        )
        
        
        # 基本系统提示词
        system_prompt = "You are a helpful assistant."
        
        # 构建消息数组
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        
        try:
            completion = client.chat.completions.create(
                    model=self.model, # 此处以qwen-plus为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
                    messages=messages,
                    stream=True,
                    )
                
            full_content = ""
            print("流式输出内容为：")
            for chunk in completion:
                # 如果stream_options.include_usage为True，则最后一个chunk的choices字段为空列表，需要跳过（可以通过chunk.usage获取 Token 使用量）
                if chunk.choices:
                    full_content += chunk.choices[0].delta.content
                    print(chunk.choices[0].delta.content)
            print(f"完整内容为：{full_content}")
                        
            
            return True, "流式响应测试成功"
            
        except Exception as e:
            logger.error(f"流式响应测试过程中出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False, f"流式响应测试出错: {str(e)}"
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("====== 开始DeepSeek API测试 ======")
        
        # 测试单个提示词
        single_success, single_result = await self.test_single_prompt()
        
        # 测试对话上下文
        # context_success, context_result = await self.test_conversation()
        
        # 测试流式响应
        stream_success, stream_result = await self.test_streaming()
        
        # 汇总测试结果
        logger.info("====== 测试结果汇总 ======")
        logger.info(f"1. 单个提示词测试: {'成功' if single_success else '失败'}")
        # logger.info(f"2. 对话上下文测试: {'成功' if context_success else '失败'}")
        logger.info(f"3. 流式响应测试: {'成功' if stream_success else '失败'}")
        
        # 总体结果
        overall_success = single_success  and stream_success
        # logger.info(f"总体测试结果: {'全部成功' if overall_success else '部分失败'}")
        
        return overall_success

async def main():
    """主函数"""
    try:
        tester = DeepSeekAPITester()
        success = await tester.run_all_tests()
        
        if success:
            logger.info("DeepSeek API测试完全成功！API可用且工作正常。")
        else:
            logger.warning("DeepSeek API测试部分失败，请检查上面的错误信息。")
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

if __name__ == "__main__":
    """程序入口"""
    asyncio.run(main()) 