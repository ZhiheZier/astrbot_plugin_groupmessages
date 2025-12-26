"""
签到模块 - 每日签到获取随机积分

规则：
- 每次签到随机 1-49，获得对应积分
- 如果随机到特殊数字，触发特殊奖励
- 保留上次签到时间和最近10条积分变动记录
"""

import random
from datetime import date, timedelta
from typing import Dict, Tuple
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain, At
from .base import BaseModule
from ..utils import DataManager


class CheckInModule(BaseModule):
    """
    签到功能模块
    
    每次签到随机 10-49，获得对应积分
    随机到特殊数字时触发特殊奖励
    
    数据结构：
    - total_points: 总积分
    - last_checkin_date: 上次签到日期
    - total_checkin_count: 累计签到次数
    - points_history: 积分变动记录（最近10条）
    """
    
    def __init__(self, context, data_dir, config: dict | None = None):
        super().__init__(context, data_dir)
        self.data_manager = DataManager(data_dir)
        self.data_file = "checkin_data.json"
        self.user_data: Dict[str, dict] = {}
        
        # ============ 签到配置区域（可自定义） ============
        
        # 普通签到点数范围：10-49（包括10和49）
        self.min_points = 10
        self.max_points = 49
        
        # 特殊签到配置
        # 格式: 积分值: {"probability": 概率(0-1), "description": "特殊描述"}
        self.special_rewards = {
            50: {
                "probability": 0.2, 
                "description": ""     # 描述为空，在get_reward_message中根据星期四动态判断
            },
            213: {
                "probability": 0.02, 
                "description": "才不是2B呢"    
            },
            648: {
                "probability": 0.01, 
                "description": "拿去充二游吧"
            }
        }
        
        # 范围型特殊签到配置（积分在范围内随机）
        # 格式: (最小值, 最大值): {"probability": 概率(0-1), "description": "特殊描述"}
        self.range_rewards = {
            (51, 200): {
                "probability": 0.1,
                "description": "运气不错哦"
            }
        }
        
        # ================================================
    
    async def initialize(self):
        """初始化签到模块"""
        self.user_data = self.data_manager.load_json(self.data_file, default={})
        self.log_info(f"已加载 {len(self.user_data)} 个用户的签到数据")
        self.log_info("签到模块初始化完成")
    
    async def terminate(self):
        """终止签到模块，保存数据"""
        self.save_data()
        self.log_info("签到模块已终止，数据已保存")
    
    def save_data(self):
        """保存签到数据"""
        self.data_manager.save_json(self.data_file, self.user_data)
    
    def get_user_info(self, user_id: str) -> dict:
        """获取用户信息，不存在则创建"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "total_points": 0,          # 总积分
                "last_checkin_date": None,  # 上次签到日期
                "total_checkin_count": 0,   # 总签到次数
                "points_history": []        # 积分变动记录（最近10条）
            }
        return self.user_data[user_id]
    
    def add_points_record(self, user_info: dict, points: int, action_type: str, 
                         description: str, source_user_id: str | None = None):
        """
        添加积分变动记录
        
        Args:
            user_info: 用户信息字典
            points: 变动的积分（正数为增加，负数为减少）
            action_type: 动作类型，如 "checkin", "rob", "被抢劫" 等
            description: 描述信息
            source_user_id: 来源用户ID（如果有）
        """
        from datetime import datetime
        
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 保存完整时间
            "action": action_type,
            "points": points,
            "description": description,
            "source": source_user_id,  # 来源用户ID
            "balance": user_info["total_points"]  # 变动后的余额
        }
        
        user_info["points_history"].append(record)
        
        # 只保留最近10条记录
        if len(user_info["points_history"]) > 10:
            user_info["points_history"] = user_info["points_history"][-10:]
    
    def calculate_points(self) -> Tuple[int, str]:
        """
        计算签到点数
        返回: (积分, 特殊描述)
        
        逻辑：
        1. 优先判断范围型奖励，根据概率触发
        2. 再判断固定积分奖励，根据概率触发
        3. 如果都未触发，返回普通签到积分（10-49）
        """
        # 1. 优先判断范围型奖励（按范围最大值从高到低排序）
        sorted_range_rewards = sorted(self.range_rewards.items(), 
                                     key=lambda x: x[0][1], reverse=True)
        
        for (min_val, max_val), config in sorted_range_rewards:
            probability = config.get("probability", 0)
            if random.random() < probability:
                # 触发范围奖励，从范围内随机
                points = random.randint(min_val, max_val)
                description = config.get("description", "")
                return points, description
        
        # 2. 判断固定积分奖励（按积分从高到低排序）
        sorted_rewards = sorted(self.special_rewards.items(), 
                               key=lambda x: x[0], reverse=True)
        
        for points, config in sorted_rewards:
            probability = config.get("probability", 0)
            if random.random() < probability:
                # 触发特殊奖励
                description = config.get("description", "")
                return points, description
        
        # 3. 未触发任何特殊奖励，返回普通签到积分
        normal_points = random.randint(self.min_points, self.max_points)
        return normal_points, ""
    
    def get_reward_message(self, points: int, special_desc: str) -> str:
        """
        生成签到消息
        
        格式：
        - 普通签到: "签到成功，获得 XX 积分"
        - 特殊签到: "签到成功，获得 XX 积分\n[特殊描述]"
        
        特殊逻辑：
        - 50积分且星期四: 显示"今天是疯狂星期四，v你50"
        - 50积分但不是星期四: 不显示特殊描述
        """
        from datetime import datetime
        
        base_msg = f"签到成功，获得 {points} 积分"
        
        # 特殊处理：50积分根据星期四判断
        if points == 50:
            # 判断今天是否是星期四（weekday(): 0=星期一, 3=星期四）
            if datetime.now().weekday() == 3:
                return f"{base_msg}\n今天是疯狂星期四，v你50"
            else:
                # 不是星期四，不显示特殊描述
                return base_msg
        
        # 其他特殊奖励
        if special_desc:
            # 特殊奖励：第一行 + 特殊描述
            return f"{base_msg}\n{special_desc}"
        else:
            # 普通签到：只有第一行
            return base_msg
    
    async def process_checkin(self, event: AstrMessageEvent):
        """处理签到逻辑"""
        user_id = str(event.get_sender_id())  # 用于数据存储（跨群聊通用）
        user_name = event.get_sender_name()
        today = date.today().isoformat()
        
        # 获取用户信息
        user_info = self.get_user_info(user_id)
        
        # 检查今天是否已签到
        if user_info["last_checkin_date"] == today:
            message_parts = [
                At(qq=user_id),
                Plain(text=f" \n你今天已经签到过了\n\n当前积分: {user_info['total_points']} 积分")
            ]
            yield event.chain_result(message_parts)
            return
        
        # 计算点数
        points, special_desc = self.calculate_points()
        
        # 更新用户数据
        user_info["total_points"] += points
        user_info["last_checkin_date"] = today
        user_info["total_checkin_count"] += 1
        
        # 记录积分变动
        desc = special_desc if special_desc else f"签到获得 {points} 积分"
        self.add_points_record(user_info, points, "签到", desc)
        
        # 保存数据
        self.save_data()
        
        # 生成签到消息
        reward_msg = self.get_reward_message(points, special_desc)
        
        # 构建消息：第一行@，第二行描述，空一行，然后积分信息
        message_text = f" \n{reward_msg}\n\n当前积分: {user_info['total_points']} 积分\n累计签到: {user_info['total_checkin_count']} 次"
        message_parts = [
            At(qq=user_id),
            Plain(text=message_text)
        ]
        
        yield event.chain_result(message_parts)
    
    async def show_points_info(self, event: AstrMessageEvent):
        """显示积分信息"""
        user_id = str(event.get_sender_id())  # 用于数据存储（跨群聊通用）
        user_info = self.get_user_info(user_id)
        today = date.today().isoformat()
        
        # 构建消息文本
        message_text = f" \n当前积分：{user_info['total_points']}分\n累计签到次数：{user_info['total_checkin_count']}次\n"
        
        # 上次签到时间
        if user_info["last_checkin_date"]:
            message_text += f"上次签到：{user_info['last_checkin_date']}\n"
            
            # 检查今日是否已签到
            if user_info["last_checkin_date"] != today:
                message_text += "\n今日还未签到，快去签到吧"
        else:
            message_text += "上次签到：无\n\n今日还未签到，快去签到吧"
        
        message_parts = [
            At(qq=user_id),
            Plain(text=message_text)
        ]
        
        yield event.chain_result(message_parts)
    
    async def points_history(self, event: AstrMessageEvent):
        """查询积分变动记录"""
        user_id = str(event.get_sender_id())  # 用于数据存储（跨群聊通用）
        user_info = self.get_user_info(user_id)
        
        # 构建消息文本
        message_text = " 的积分记录\n"
        
        # 显示积分变动记录
        if user_info.get("points_history"):
            # 倒序显示，最新的在前
            for record in reversed(user_info["points_history"]):
                points_str = f"+{record['points']}" if record['points'] > 0 else str(record['points'])
                date_str = record['date']  # 完整时间 YYYY-MM-DD HH:MM:SS
                action = record['action']
                
                # 一行显示一条记录
                line = f"{date_str} {action} {points_str}"
                
                # 如果有来源用户ID，显示QQ号
                if record.get('source'):
                    line += f" 来自:{record['source']}"
                
                message_text += line + "\n"
        else:
            message_text += "暂无积分变动记录"
        
        message_parts = [
            At(qq=user_id),
            Plain(text=message_text)
        ]
        
        yield event.chain_result(message_parts)
    

