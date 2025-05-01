#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
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
        
        # 构建API请求
        endpoint = f"{self.api_base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 基本系统提示词
        system_prompt = "你是DeepSeek语音助手，一个友好、专业的人工智能助手。请提供简洁、准确、有用的回答。"
        
        # 构建消息数组
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # 构建请求体
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.95,
            "stream": False
        }
        
        # 记录请求详情
        logger.info(f"API端点: {endpoint}")
        logger.debug(f"请求头: Authorization: Bearer {self.api_key[:3]}...{self.api_key[-3:]}, Content-Type: {headers['Content-Type']}")
        logger.debug(f"请求体: {json.dumps(payload, ensure_ascii=False)}")
        
        # 发送请求
        try:
            start_time = time.time()
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            end_time = time.time()
            
            logger.info(f"API响应状态码: {response.status_code}, 响应时间: {int((end_time-start_time)*1000)}ms")
            
            # 记录原始响应
            logger.debug(f"原始响应: {response.text[:1000]}...")
            
            # 检查响应状态
            if response.status_code == 200:
                # 解析响应JSON
                result = response.json()
                
                # 提取回复内容
                reply = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                logger.info(f"测试成功！API回复: {reply[:100]}..." if len(reply) > 100 else f"测试成功！API回复: {reply}")
                return True, reply
            else:
                # 处理错误响应
                logger.error(f"API请求失败: {response.status_code}, {response.text}")
                
                # 尝试解析错误信息
                try:
                    error_json = response.json()
                    error_message = error_json.get('error', {}).get('message', '未知错误')
                    error_type = error_json.get('error', {}).get('type', '未知类型')
                    logger.error(f"错误类型: {error_type}, 错误消息: {error_message}")
                except:
                    logger.error(f"无法解析错误响应: {response.text}")
                
                return False, f"API请求失败: {response.status_code}"
                
        except Exception as e:
            logger.error(f"请求过程中出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False, f"请求出错: {str(e)}"
            
    async def test_conversation(self):
        """测试对话上下文"""
        logger.info("测试对话上下文功能")
        
        # 构建API请求基本信息
        endpoint = f"{self.api_base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 基本系统提示词
        system_prompt = "你是DeepSeek语音助手，一个友好、专业的人工智能助手。请提供简洁、准确、有用的回答。"
        
        # 第一轮对话
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "我叫小明，请记住我的名字"}
        ]
        
        # 构建请求体
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.95,
            "stream": False
        }
        
        try:
            # 第一轮请求
            logger.info("发送第一轮对话请求...")
            response1 = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            
            if response1.status_code != 200:
                logger.error(f"第一轮对话请求失败: {response1.status_code}, {response1.text}")
                return False, "第一轮对话请求失败"
                
            result1 = response1.json()
            reply1 = result1.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"第一轮回复: {reply1}")
            
            # 添加助手回复到消息历史
            messages.append({"role": "assistant", "content": reply1})
            
            # 第二轮对话，测试上下文记忆
            messages.append({"role": "user", "content": "我叫什么名字？"})
            
            # 更新请求体
            payload["messages"] = messages
            
            # 第二轮请求
            logger.info("发送第二轮对话请求...")
            response2 = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            
            if response2.status_code != 200:
                logger.error(f"第二轮对话请求失败: {response2.status_code}, {response2.text}")
                return False, "第二轮对话请求失败"
                
            result2 = response2.json()
            reply2 = result2.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"第二轮回复: {reply2}")
            
            # 检查是否记住了名字
            if "小明" in reply2:
                logger.info("测试成功！DeepSeek API能够维持对话上下文")
                return True, "对话上下文测试成功"
            else:
                logger.warning("DeepSeek API可能未能正确维持对话上下文")
                return False, "对话上下文测试不完全成功"
                
        except Exception as e:
            logger.error(f"对话测试过程中出错: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False, f"对话测试出错: {str(e)}"
    
    async def test_streaming(self):
        """测试流式响应"""
        logger.info("测试流式响应功能")
        
        # 构建API请求基本信息
        endpoint = f"{self.api_base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 基本系统提示词
        system_prompt = "你是DeepSeek语音助手，一个友好、专业的人工智能助手。请提供简洁、准确、有用的回答。"
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请列举三种常见的水果及其特点"}
        ]
        
        # 构建请求体
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.95,
            "stream": True  # 启用流式响应
        }
        
        try:
            logger.info("发送流式响应请求...")
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30, stream=True)
            
            if response.status_code != 200:
                logger.error(f"流式响应请求失败: {response.status_code}, {response.text}")
                return False, "流式响应请求失败"
                
            full_response = ""
            chunk_count = 0
            
            # 处理流式响应
            logger.info("接收流式响应:")
            for line in response.iter_lines():
                if line:
                    chunk_count += 1
                    line_text = line.decode('utf-8')
                    
                    # 跳过保持连接的空行
                    if line_text.strip() == "":
                        continue
                        
                    # 跳过data: [DONE]
                    if line_text == "data: [DONE]":
                        logger.info("流式响应完成")
                        continue
                        
                    # 解析JSON数据
                    if line_text.startswith("data: "):
                        json_str = line_text[6:]  # 去掉"data: "前缀
                        try:
                            data = json.loads(json_str)
                            content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                full_response += content
                                # 打印进度
                                if chunk_count % 5 == 0:
                                    logger.info(f"已接收 {chunk_count} 个数据块, 当前累积内容长度: {len(full_response)}")
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析JSON: {json_str}")
            
            logger.info(f"流式响应测试完成，共收到 {chunk_count} 个数据块")
            logger.info(f"完整回复: {full_response[:100]}..." if len(full_response) > 100 else f"完整回复: {full_response}")
            
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
        context_success, context_result = await self.test_conversation()
        
        # 测试流式响应
        stream_success, stream_result = await self.test_streaming()
        
        # 汇总测试结果
        logger.info("====== 测试结果汇总 ======")
        logger.info(f"1. 单个提示词测试: {'成功' if single_success else '失败'}")
        logger.info(f"2. 对话上下文测试: {'成功' if context_success else '失败'}")
        logger.info(f"3. 流式响应测试: {'成功' if stream_success else '失败'}")
        
        # 总体结果
        overall_success = single_success and context_success and stream_success
        logger.info(f"总体测试结果: {'全部成功' if overall_success else '部分失败'}")
        
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