"""
群聊消息管理插件 - 主入口文件

已实现功能：
- 签到系统：每日签到获取随机积分
- 涩图系统：消耗积分获取随机涩图
- 抢劫系统：抢劫其他用户积分，动态成功率
"""

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
from astrbot.api.message_components import At, Plain
from astrbot.core.star.star_tools import StarTools
from pathlib import Path
from typing import List, Dict, Any, Set
import json
import re

# 导入功能模块
from .modules import CheckInModule, SetuModule, RobberyModule
from .modules.base import BaseModule


@register("astrbot_plugin_groupmessages", "ZhiheZier", "群聊消息管理插件 - 提供签到、涩图、互动等多种功能", "1.0.0")
class GroupMessagesPlugin(Star):
    """
    群聊消息管理插件主类
    采用模块化设计，便于扩展新功能
    """
    
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.data_dir: Path | None = None
        self.config = config if config is not None else {}
        self.checkin_module: CheckInModule | None = None
        self.setu_module: SetuModule | None = None
        self.robbery_module: RobberyModule | None = None
        
        # 群组启用状态（存储禁用的群组ID）
        self.disabled_groups: Set[str] = set()
        self.data_file: Path | None = None
        
        # 群组涩图设置（存储每个群的涩图权限）
        # 格式: {"群号": {"normal_setu": bool, "r18_setu": bool}}
        self.group_setu_settings: Dict[str, Dict[str, bool]] = {}
        self.setu_settings_file: Path | None = None
        
        # 获取超级管理员列表
        bot_config = context.get_config()
        admins = bot_config.get("admins_id", [])
        self.superusers = [str(admin) for admin in admins] if admins else []
        
        if self.superusers:
            logger.info(f'获取到超级管理员列表: {self.superusers}')
        else:
            logger.warning('未找到超级管理员ID')
        
    def _load_disabled_groups(self):
        """加载禁用群组列表"""
        if not self.data_file:
            return
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.disabled_groups = set(data.get('disabled_groups', []))
                logger.info(f'已加载禁用群组列表，共 {len(self.disabled_groups)} 个群组')
            else:
                logger.info('禁用群组列表文件不存在，创建新文件')
                self._save_disabled_groups()
        except Exception as e:
            logger.error(f'加载禁用群组列表失败: {e}')
            self.disabled_groups = set()
    
    def _save_disabled_groups(self):
        """保存禁用群组列表"""
        if not self.data_file:
            return
        try:
            data = {'disabled_groups': list(self.disabled_groups)}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info('禁用群组列表已保存')
        except Exception as e:
            logger.error(f'保存禁用群组列表失败: {e}')
    
    def _is_group_enabled(self, group_id: str) -> bool:
        """检查群组是否启用插件"""
        return group_id not in self.disabled_groups
    
    def _load_group_setu_settings(self):
        """加载群组涩图设置"""
        if not self.setu_settings_file:
            return
        try:
            if self.setu_settings_file.exists():
                with open(self.setu_settings_file, 'r', encoding='utf-8') as f:
                    self.group_setu_settings = json.load(f)
                logger.info(f'已加载群组涩图设置，共 {len(self.group_setu_settings)} 个群组')
            else:
                logger.info('群组涩图设置文件不存在，创建新文件')
                self._save_group_setu_settings()
        except Exception as e:
            logger.error(f'加载群组涩图设置失败: {e}')
            self.group_setu_settings = {}
    
    def _save_group_setu_settings(self):
        """保存群组涩图设置"""
        if not self.setu_settings_file:
            return
        try:
            with open(self.setu_settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.group_setu_settings, f, ensure_ascii=False, indent=2)
            logger.info('群组涩图设置已保存')
        except Exception as e:
            logger.error(f'保存群组涩图设置失败: {e}')
    
    def _get_group_setu_permission(self, group_id: str, setu_type: str) -> bool:
        """
        获取群组的涩图权限
        
        Args:
            group_id: 群号
            setu_type: 涩图类型 ("normal_setu" 或 "r18_setu")
        
        Returns:
            是否允许
        """
        # 如果群组没有设置，使用全局配置
        if group_id not in self.group_setu_settings:
            if setu_type == "normal_setu":
                return self.config.get("normal_setu_enabled", True)
            elif setu_type == "r18_setu":
                return self.config.get("r18_setu_enabled", False)
        
        # 使用群组设置
        return self.group_setu_settings[group_id].get(setu_type, True)
    
    def _register_modules(self):
        """
        注册功能模块
        在这里添加新的功能模块
        """
        logger.info("正在注册功能模块...")
        
        # 签到模块
        checkin_enabled = self.config.get("checkin_enabled", True)
        if checkin_enabled:
            self.checkin_module = CheckInModule(self.context, self.data_dir)
            logger.info("✓ 签到模块已加载")
        else:
            logger.info("✗ 签到模块已禁用")
        
        # 涩图模块（依赖签到模块）
        normal_setu_enabled = self.config.get("normal_setu_enabled", True)
        r18_setu_enabled = self.config.get("r18_setu_enabled", False)
        setu_any_enabled = normal_setu_enabled or r18_setu_enabled
        
        if setu_any_enabled and self.checkin_module:
            self.setu_module = SetuModule(self.context, self.data_dir, self.checkin_module, self.config)
            if normal_setu_enabled and r18_setu_enabled:
                logger.info("✓ 涩图模块已加载（普通涩图 + R18涩图）")
            elif normal_setu_enabled:
                logger.info("✓ 涩图模块已加载（仅普通涩图）")
            elif r18_setu_enabled:
                logger.info("✓ 涩图模块已加载（仅R18涩图）")
        elif setu_any_enabled and not self.checkin_module:
            logger.warning("✗ 涩图模块需要签到模块支持，但签到模块未启用")
        else:
            logger.info("✗ 涩图模块已禁用")
        
        # 抢劫模块（依赖签到模块）
        robbery_enabled = self.config.get("robbery_enabled", True)
        if robbery_enabled and self.checkin_module:
            self.robbery_module = RobberyModule(self.context, self.data_dir, self.checkin_module, self.config)
            logger.info("✓ 抢劫模块已加载")
        elif robbery_enabled and not self.checkin_module:
            logger.warning("✗ 抢劫模块需要签到模块支持，但签到模块未启用")
        else:
            logger.info("✗ 抢劫模块已禁用")
        
        logger.info(f"功能模块注册完成")

    async def initialize(self):
        """插件初始化"""
        logger.info(f"群聊消息插件初始化中...")
        
        # 获取数据目录
        self.data_dir = StarTools.get_data_dir()
        logger.info(f"数据目录: {self.data_dir}")
        
        # 设置数据文件路径
        self.data_file = self.data_dir / "disabled_groups.json"
        self.setu_settings_file = self.data_dir / "group_setu_settings.json"
        
        # 加载禁用群组列表
        self._load_disabled_groups()
        
        # 加载群组涩图设置
        self._load_group_setu_settings()
        
        # 注册功能模块
        self._register_modules()
        
        # 初始化签到模块
        if self.checkin_module:
            try:
                await self.checkin_module.initialize()
                logger.info(f"✓ CheckInModule 初始化成功")
            except Exception as e:
                logger.error(f"✗ CheckInModule 初始化失败: {e}")
        
        # 初始化涩图模块
        if self.setu_module:
            try:
                await self.setu_module.initialize()
                logger.info(f"✓ SetuModule 初始化成功")
            except Exception as e:
                logger.error(f"✗ SetuModule 初始化失败: {e}")
        
        # 初始化抢劫模块
        if self.robbery_module:
            try:
                await self.robbery_module.initialize()
                logger.info(f"✓ RobberyModule 初始化成功")
            except Exception as e:
                logger.error(f"✗ RobberyModule 初始化失败: {e}")
        
        logger.info("群聊消息插件初始化完成")

    async def terminate(self):
        """插件终止"""
        logger.info("群聊消息插件正在终止...")
        
        # 保存禁用群组列表
        self._save_disabled_groups()
        
        # 保存群组涩图设置
        self._save_group_setu_settings()
        
        # 终止签到模块
        if self.checkin_module:
            try:
                await self.checkin_module.terminate()
                logger.info(f"✓ CheckInModule 已终止")
            except Exception as e:
                logger.error(f"✗ CheckInModule 终止失败: {e}")
        
        # 终止涩图模块
        if self.setu_module:
            try:
                await self.setu_module.terminate()
                logger.info(f"✓ SetuModule 已终止")
            except Exception as e:
                logger.error(f"✗ SetuModule 终止失败: {e}")
        
        # 终止抢劫模块
        if self.robbery_module:
            try:
                await self.robbery_module.terminate()
                logger.info(f"✓ RobberyModule 已终止")
            except Exception as e:
                logger.error(f"✗ RobberyModule 终止失败: {e}")
        
        logger.info("群聊消息插件已终止")
    
    # ==================== 群组管理命令 ====================
    
    @filter.regex(r'^(开启|关闭)(普通涩图|R18涩图)$')
    async def toggle_group_setu(self, event: AstrMessageEvent):
        """开启/关闭群涩图功能（超级管理员专用）"""
        # 检查是否为超级管理员
        sender_id = str(event.get_sender_id())
        if sender_id not in self.superusers:
            yield event.plain_result('仅允许超级管理员执行此操作')
            return
        
        # 检查是否在群聊中
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result('此命令仅在群聊中可用')
            return
        
        gid = str(group_id)
        message_str = event.message_str.strip()
        
        # 解析命令
        if message_str.startswith('开启'):
            action = '开启'
            setu_type_name = message_str[2:]
        else:
            action = '关闭'
            setu_type_name = message_str[2:]
        
        # 确定涩图类型
        if setu_type_name == '普通涩图':
            setu_type = 'normal_setu'
        elif setu_type_name == 'R18涩图':
            setu_type = 'r18_setu'
        else:
            yield event.plain_result('无效的涩图类型')
            return
        
        # 初始化群组设置（如果不存在）
        if gid not in self.group_setu_settings:
            self.group_setu_settings[gid] = {
                'normal_setu': self.config.get("normal_setu_enabled", True),
                'r18_setu': self.config.get("r18_setu_enabled", False)
            }
        
        # 更新设置
        if action == '开启':
            self.group_setu_settings[gid][setu_type] = True
            self._save_group_setu_settings()
            yield event.plain_result(f'已开启本群的{setu_type_name}功能')
        else:
            self.group_setu_settings[gid][setu_type] = False
            self._save_group_setu_settings()
            yield event.plain_result(f'已关闭本群的{setu_type_name}功能')
    
    @filter.regex(r'^(开启|关闭)群聊消息插件$')
    async def toggle_plugin(self, event: AstrMessageEvent):
        """开启/关闭群聊消息插件（超级管理员专用）"""
        # 检查是否为超级管理员
        sender_id = str(event.get_sender_id())
        if sender_id not in self.superusers:
            yield event.plain_result('仅允许超级管理员执行此操作')
            return
        
        # 检查是否在群聊中
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result('此命令仅在群聊中可用')
            return
        
        gid = str(group_id)
        message_str = event.message_str.strip()
        
        if message_str == '开启群聊消息插件':
            if gid in self.disabled_groups:
                self.disabled_groups.remove(gid)
                self._save_disabled_groups()
                yield event.plain_result(f'已开启本群的群聊消息插件')
            else:
                yield event.plain_result('本群群聊消息插件已经是开启状态')
        elif message_str == '关闭群聊消息插件':
            if gid not in self.disabled_groups:
                self.disabled_groups.add(gid)
                self._save_disabled_groups()
                yield event.plain_result(f'已关闭本群的群聊消息插件')
            else:
                yield event.plain_result('本群群聊消息插件已经是关闭状态')
    
    # ==================== 签到命令 ====================
    
    @filter.regex(r'^签到$')
    async def checkin_command(self, event: AstrMessageEvent):
        """签到命令"""
        # 检查群组是否启用
        group_id = event.message_obj.group_id
        if group_id and not self._is_group_enabled(str(group_id)):
            return
        
        if not self.checkin_module:
            return
        async for result in self.checkin_module.process_checkin(event):
            yield result
    
    @filter.regex(r'^(积分|我的积分)$')
    async def points_query_command(self, event: AstrMessageEvent):
        """查询积分"""
        # 检查群组是否启用
        group_id = event.message_obj.group_id
        if group_id and not self._is_group_enabled(str(group_id)):
            return
        
        if not self.checkin_module:
            return
        async for result in self.checkin_module.show_points_info(event):
            yield result
    
    @filter.regex(r'^积分记录$')
    async def points_history_command(self, event: AstrMessageEvent):
        """查询积分记录"""
        # 检查群组是否启用
        group_id = event.message_obj.group_id
        if group_id and not self._is_group_enabled(str(group_id)):
            return
        
        if not self.checkin_module:
            return
        async for result in self.checkin_module.points_history(event):
            yield result
    
    # ==================== 抢劫和奖励命令 ====================
    
    @filter.regex(r'^抢劫')
    async def robbery_command(self, event: AstrMessageEvent):
        """抢劫其他用户积分"""
        # 检查群组是否启用
        group_id = event.message_obj.group_id
        if group_id and not self._is_group_enabled(str(group_id)):
            return
        
        if not self.robbery_module:
            return
        async for result in self.robbery_module.process_robbery(event):
            yield result
    
    @filter.regex(r'^奖励')
    async def reward_points_command(self, event: AstrMessageEvent):
        """奖励积分（超级管理员专用）"""
        if not self.robbery_module:
            return
        async for result in self.robbery_module.reward_points(event, self.superusers):
            yield result
    
    # ==================== 涩图命令 ====================
    
    @filter.regex(r'^来张涩图$')
    async def normal_setu_command(self, event: AstrMessageEvent):
        """来张涩图（消耗10积分）"""
        # 检查群组是否启用
        group_id = event.message_obj.group_id
        if group_id and not self._is_group_enabled(str(group_id)):
            return
        
        if not self.setu_module:
            return
        
        # 检查全局配置
        if not self.config.get("normal_setu_enabled", True):
            yield event.plain_result("涩图功能已被管理员禁用")
            return
        
        # 检查群组权限（仅在群聊中）
        if group_id and not self._get_group_setu_permission(str(group_id), "normal_setu"):
            yield event.plain_result("本群已禁用涩图功能")
            return
        
        async for result in self.setu_module.get_normal_setu(event):
            yield result
    
    @filter.regex(r'^来张更涩的$')
    async def r18_setu_command(self, event: AstrMessageEvent):
        """来张更涩的（消耗30积分）"""
        # 检查群组是否启用
        group_id = event.message_obj.group_id
        if group_id and not self._is_group_enabled(str(group_id)):
            return
        
        if not self.setu_module:
            return
        
        # 检查全局配置
        if not self.config.get("r18_setu_enabled", False):
            yield event.plain_result("R18涩图功能已被管理员禁用")
            return
        
        # 检查群组权限（仅在群聊中）
        if group_id and not self._get_group_setu_permission(str(group_id), "r18_setu"):
            yield event.plain_result("本群已禁用R18涩图功能")
            return
        
        async for result in self.setu_module.get_r18_setu(event):
            yield result
