"""
抢劫模块 - 抢劫其他用户积分和管理员奖励功能
"""

import time
import random
from typing import Dict, List, Any

from astrbot.api.message_components import At, Plain
from astrbot.api.event import AstrMessageEvent

from ..modules.base import BaseModule


class RobberyModule(BaseModule):
    """
    抢劫功能模块
    
    规则：
    - 初始成功概率：50%
    - 成功后概率 -1%，失败后概率 +1%
    - 最多抢劫 50 积分，失败最多被抢劫 50 积分
    - 积分大于 100 才可以抢劫
    - 冷却时间：30 分钟
    """
    
    def __init__(self, context, data_dir, checkin_module, config: dict | None = None):
        super().__init__(context, data_dir)
        self.checkin_module = checkin_module  # 引用签到模块，用于操作积分
        self.config = config if config is not None else {}
        
        # 抢劫配置
        self.min_points_to_rob = 50  # 最低抢劫积分要求
        self.initial_success_rate = 0.5  # 初始成功概率 50%
        self.max_rob_amount = 50  # 最多抢劫积分
        self.max_lose_amount = 50  # 失败最多被抢劫积分
        self.cooldown = 30 * 60  # 冷却时间 30 分钟（秒）
        
        # 用户抢劫数据 {user_id: {"success_rate": float, "last_rob_time": float}}
        self.robbery_data: Dict[str, Dict[str, Any]] = {}
        
        # 用户冷却时间记录 {user_id: last_rob_timestamp}
        self.last_robbery: Dict[str, float] = {}
    
    async def initialize(self):
        """初始化抢劫模块"""
        self.log_info("抢劫模块初始化完成")
    
    async def terminate(self):
        """终止抢劫模块"""
        self.log_info("抢劫模块已终止")
    
    def get_user_robbery_data(self, user_id: str) -> Dict[str, Any]:
        """获取用户抢劫数据"""
        if user_id not in self.robbery_data:
            self.robbery_data[user_id] = {
                "success_rate": self.initial_success_rate,
                "total_rob_count": 0,
                "success_count": 0,
                "fail_count": 0
            }
        return self.robbery_data[user_id]
    
    async def process_robbery(self, event: AstrMessageEvent):
        """
        处理抢劫请求
        """
        robber_id = str(event.get_sender_id())
        robber_info = self.checkin_module.get_user_info(robber_id)
        
        # 检查冷却时间
        current_time = time.time()
        if robber_id in self.last_robbery:
            time_passed = current_time - self.last_robbery[robber_id]
            if time_passed < self.cooldown:
                remaining_time = self.cooldown - time_passed
                remaining_minutes = int(remaining_time // 60)
                remaining_seconds = int(remaining_time % 60)
                message_parts = [
                    At(qq=robber_id),
                    Plain(text=f" \n抢劫冷却中\n剩余时间：{remaining_minutes} 分 {remaining_seconds} 秒")
                ]
                yield event.chain_result(message_parts)
                return
        
        # 检查抢劫者积分是否足够
        if robber_info["total_points"] < self.min_points_to_rob:
            message_parts = [
                At(qq=robber_id),
                Plain(text=f" \n积分不足！\n抢劫需要至少 {self.min_points_to_rob} 积分，当前积分：{robber_info['total_points']} 分")
            ]
            yield event.chain_result(message_parts)
            return
        
        # 解析目标用户（从消息链中提取 At 组件）
        message_chain = event.message_obj.message
        target_user_id = None
        
        for item in message_chain:
            # 检查是否为 At 组件（兼容不同的类型表示）
            if hasattr(item, 'type'):
                item_type = str(item.type).lower()
                if 'at' in item_type and hasattr(item, 'qq'):
                    target_user_id = str(item.qq)
                    break
            elif hasattr(item, 'qq'):  # 直接检查是否有 qq 属性
                target_user_id = str(item.qq)
                break
        
        if not target_user_id:
            yield event.plain_result('请使用 @ 指定要抢劫的用户')
            return
        
        # 不能抢劫自己
        if target_user_id == robber_id:
            yield event.plain_result('不能抢劫自己！')
            return
        
        # 获取目标用户信息
        target_info = self.checkin_module.get_user_info(target_user_id)
        
        # 检查目标用户积分
        if target_info["total_points"] < self.min_points_to_rob:
            message_parts = [
                At(qq=robber_id),
                Plain(text=f" \n对方积分不足 {self.min_points_to_rob} 分，无法抢劫！")
            ]
            yield event.chain_result(message_parts)
            return
        
        # 获取抢劫者数据
        robbery_data = self.get_user_robbery_data(robber_id)
        success_rate = robbery_data["success_rate"]
        
        # 判断抢劫是否成功
        is_success = random.random() < success_rate
        
        if is_success:
            # 抢劫成功
            # 计算抢劫金额（随机 1-50）
            rob_amount = random.randint(1, self.max_rob_amount)
            rob_amount = min(rob_amount, target_info["total_points"])  # 不能超过对方积分
            
            # 转移积分
            robber_info["total_points"] += rob_amount
            target_info["total_points"] -= rob_amount
            
            # 记录积分变动
            self.checkin_module.add_points_record(
                robber_info,
                rob_amount,
                "抢劫成功",
                f"抢劫成功获得 {rob_amount} 积分",
                source_user_id=target_user_id
            )
            self.checkin_module.add_points_record(
                target_info,
                -rob_amount,
                "被抢劫",
                f"被抢劫损失 {rob_amount} 积分",
                source_user_id=robber_id
            )
            
            # 更新成功率（成功后 -1%）
            robbery_data["success_rate"] = max(0.01, success_rate - 0.01)
            robbery_data["total_rob_count"] += 1
            robbery_data["success_count"] += 1
            
            # 更新冷却时间
            self.last_robbery[robber_id] = current_time
            
            # 保存数据
            self.checkin_module.save_data()
            
            # 构建消息
            message_text = f" \n抢劫成功！\n获得积分：+{rob_amount} 分\n当前积分：{robber_info['total_points']} 分\n当前成功率：{int(robbery_data['success_rate']*100)}%"
            message_parts = [
                At(qq=robber_id),
                Plain(text=message_text)
            ]
            yield event.chain_result(message_parts)
            
        else:
            # 抢劫失败
            # 计算被抢金额（随机 1-50）
            lose_amount = random.randint(1, self.max_lose_amount)
            lose_amount = min(lose_amount, robber_info["total_points"])  # 不能超过自己积分
            
            # 转移积分
            robber_info["total_points"] -= lose_amount
            target_info["total_points"] += lose_amount
            
            # 记录积分变动
            self.checkin_module.add_points_record(
                robber_info,
                -lose_amount,
                "抢劫失败",
                f"抢劫失败损失 {lose_amount} 积分",
                source_user_id=target_user_id
            )
            self.checkin_module.add_points_record(
                target_info,
                lose_amount,
                "反抢",
                f"反抢获得 {lose_amount} 积分",
                source_user_id=robber_id
            )
            
            # 更新成功率（失败后 +1%）
            robbery_data["success_rate"] = min(0.99, success_rate + 0.01)
            robbery_data["total_rob_count"] += 1
            robbery_data["fail_count"] += 1
            
            # 更新冷却时间
            self.last_robbery[robber_id] = current_time
            
            # 保存数据
            self.checkin_module.save_data()
            
            # 构建消息
            message_text = f" \n抢劫失败！\n损失积分：-{lose_amount} 分\n当前积分：{robber_info['total_points']} 分\n当前成功率：{int(robbery_data['success_rate']*100)}%"
            message_parts = [
                At(qq=robber_id),
                Plain(text=message_text)
            ]
            yield event.chain_result(message_parts)
    
    async def reward_points(self, event: AstrMessageEvent, superusers: List[str]):
        """
        奖励积分（超级管理员专用）
        """
        sender_id = str(event.get_sender_id())
        
        # 检查是否为超级管理员
        if sender_id not in superusers:
            yield event.plain_result('仅允许超级管理员执行此操作')
            return
        
        # 解析消息内容
        message_chain = event.message_obj.message
        target_user_id = None
        points_amount = None
        
        # 遍历消息链查找 At 组件和数字
        import re
        message_text = event.message_str.strip()
        
        # 匹配格式：奖励 @用户 数字
        # 先从消息链中找 At 组件
        for item in message_chain:
            # 检查是否为 At 组件（兼容不同的类型表示）
            if hasattr(item, 'type'):
                item_type = str(item.type).lower()
                if 'at' in item_type and hasattr(item, 'qq'):
                    target_user_id = str(item.qq)
                    break
            elif hasattr(item, 'qq'):  # 直接检查是否有 qq 属性
                target_user_id = str(item.qq)
                break
        
        # 从文本中提取数字
        numbers = re.findall(r'\d+', message_text)
        if numbers:
            try:
                points_amount = int(numbers[-1])  # 取最后一个数字
            except ValueError:
                pass
        
        # 验证参数
        if not target_user_id:
            yield event.plain_result('请使用 @ 指定要奖励的用户')
            return
        
        if points_amount is None or points_amount <= 0:
            yield event.plain_result('请指定有效的积分数量（正整数）')
            return
        
        # 获取目标用户信息
        user_info = self.checkin_module.get_user_info(target_user_id)
        
        # 增加积分
        user_info["total_points"] += points_amount
        
        # 记录积分变动
        self.checkin_module.add_points_record(
            user_info,
            points_amount,
            "奖励",
            f"管理员奖励",
            source_user_id=sender_id
        )
        
        # 保存数据
        self.checkin_module.save_data()
        
        # 构建回复消息
        message_parts = [
            Plain(text="已成功奖励 "),
            At(qq=target_user_id),
            Plain(text=f" {points_amount} 积分\n当前积分：{user_info['total_points']} 分")
        ]
        yield event.chain_result(message_parts)

