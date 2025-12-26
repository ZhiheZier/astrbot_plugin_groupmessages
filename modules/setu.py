"""
涩图模块 - 消耗积分获取随机涩图
"""

import asyncio
import time
from typing import List, Any
import httpx

from astrbot.api.message_components import At, Plain, Image
from astrbot.api.event import AstrMessageEvent

from ..modules.base import BaseModule


class SetuModule(BaseModule):
    """
    涩图功能模块
    
    涩图：消耗 10 积分
    R18涩图：消耗 30 积分
    
    使用 Lolicon API 获取图片
    """
    
    def __init__(self, context, data_dir, checkin_module, config: dict | None = None):
        super().__init__(context, data_dir)
        self.checkin_module = checkin_module  # 引用签到模块，用于操作积分
        self.semaphore = asyncio.Semaphore(10)  # 限制并发请求数量
        self.config = config if config is not None else {}
        
        # 积分消耗配置
        self.normal_setu_cost = 10   # 普通涩图消耗积分
        self.r18_setu_cost = 30      # R18涩图消耗积分
        
        # 冷却时间配置（秒）
        self.cooldown = self.config.get("setu_cooldown", 60)
        
        # 是否排除AI作品
        self.exclude_ai = self.config.get("exclude_ai", True)
        
        # 用户冷却时间记录 {user_id: last_use_timestamp}
        self.last_usage: dict = {}
    
    async def initialize(self):
        """初始化涩图模块"""
        self.log_info("涩图模块初始化完成")
    
    async def terminate(self):
        """终止涩图模块"""
        self.log_info("涩图模块已终止")
    
    async def fetch_setu(self, r18: int = 0) -> dict:
        """
        从 Lolicon API 获取涩图
        
        Args:
            r18: 0=普通, 1=R18
        
        Returns:
            API 响应数据
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 构建API URL，添加excludeAI参数
            exclude_ai_param = 1 if self.exclude_ai else 0
            url = f"https://api.lolicon.app/setu/v2?r18={r18}&excludeAI={exclude_ai_param}"
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    
    async def process_setu_request(self, event: AstrMessageEvent, is_r18: bool = False):
        """
        处理涩图请求
        
        Args:
            event: 消息事件
            is_r18: 是否为 R18 涩图
        """
        user_id = str(event.get_sender_id())
        user_info = self.checkin_module.get_user_info(user_id)
        
        # 判断需要消耗的积分
        cost = self.r18_setu_cost if is_r18 else self.normal_setu_cost
        setu_type = "R18涩图" if is_r18 else "涩图"
        
        # 检查冷却时间
        if self.cooldown > 0:
            current_time = time.time()
            if user_id in self.last_usage:
                time_passed = current_time - self.last_usage[user_id]
                if time_passed < self.cooldown:
                    remaining_time = self.cooldown - time_passed
                    message_parts = [
                        At(qq=user_id),
                        Plain(text=f" \n冷却中，请等待 {remaining_time:.1f} 秒后重试")
                    ]
                    yield event.chain_result(message_parts)
                    return
        
        # 检查积分是否足够
        if user_info["total_points"] < cost:
            message_parts = [
                At(qq=user_id),
                Plain(text=f" \n积分不足！\n{setu_type}需要 {cost} 积分，当前积分：{user_info['total_points']} 分")
            ]
            yield event.chain_result(message_parts)
            return
        
        # 获取涩图
        async with self.semaphore:
            try:
                # 发送提示消息
                yield event.plain_result(f"正在获取{setu_type}，请稍候...")
                
                # 调用 API
                data = await self.fetch_setu(r18=1 if is_r18 else 0)
                
                if data.get('data') and len(data['data']) > 0:
                    image_info = data['data'][0]
                    image_url = image_info['urls']['original']
                    title = image_info.get('title', '未知')
                    author = image_info.get('author', '未知')
                    
                    # 扣除积分
                    user_info["total_points"] -= cost
                    
                    # 记录积分变动
                    desc = f"获取{setu_type}"
                    self.checkin_module.add_points_record(
                        user_info, 
                        -cost, 
                        "涩图", 
                        desc
                    )
                    
                    # 保存数据
                    self.checkin_module.save_data()
                    
                    # 更新冷却时间
                    if self.cooldown > 0:
                        self.last_usage[user_id] = time.time()
                    
                    # 构建消息
                    message_text = f" \n{setu_type}来啦！\n标题：{title}\n作者：{author}\n消耗积分：{cost} 分\n剩余积分：{user_info['total_points']} 分"
                    chain = [
                        At(qq=user_id),
                        Plain(text=message_text),
                        Image.fromURL(image_url, size='original')
                    ]
                    yield event.chain_result(chain)
                else:
                    yield event.plain_result("没有找到涩图，积分未扣除。")
                    
            except httpx.HTTPStatusError as e:
                self.log_error(f"获取涩图时发生HTTP错误: {e.response.status_code}")
                yield event.plain_result(f"获取涩图失败（HTTP {e.response.status_code}），积分未扣除。")
            except httpx.TimeoutException:
                self.log_error("获取涩图超时")
                yield event.plain_result("获取涩图超时，请稍后重试，积分未扣除。")
            except httpx.HTTPError as e:
                self.log_error(f"获取涩图时发生网络错误: {e}")
                yield event.plain_result(f"网络错误，积分未扣除。")
            except Exception as e:
                self.log_error(f"获取涩图时发生未知错误: {e}")
                yield event.plain_result(f"发生错误，积分未扣除。")
    
    async def get_normal_setu(self, event: AstrMessageEvent):
        """获取普通涩图（消耗10积分）"""
        async for result in self.process_setu_request(event, is_r18=False):
            yield result
    
    async def get_r18_setu(self, event: AstrMessageEvent):
        """获取R18涩图（消耗30积分）"""
        async for result in self.process_setu_request(event, is_r18=True):
            yield result

