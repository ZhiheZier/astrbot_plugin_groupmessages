"""
基础模块类 - 所有功能模块的父类
"""

from abc import ABC, abstractmethod
from astrbot.api.star import Context
from astrbot.api import logger
from pathlib import Path
from typing import Dict, Any


class BaseModule(ABC):
    """
    功能模块基类
    所有功能模块应继承此类
    """
    
    def __init__(self, context: Context, data_dir: Path):
        """
        初始化模块
        
        Args:
            context: AstrBot 上下文
            data_dir: 插件数据目录
        """
        self.context = context
        self.data_dir = data_dir
        self.module_name = self.__class__.__name__
        
    @abstractmethod
    async def initialize(self):
        """
        模块初始化方法
        子类必须实现
        """
        pass
    
    @abstractmethod
    async def terminate(self):
        """
        模块终止方法
        子类必须实现
        """
        pass
    
    def log_info(self, message: str):
        """记录信息日志"""
        logger.info(f"[{self.module_name}] {message}")
    
    def log_error(self, message: str):
        """记录错误日志"""
        logger.error(f"[{self.module_name}] {message}")
    
    def log_warning(self, message: str):
        """记录警告日志"""
        logger.warning(f"[{self.module_name}] {message}")

