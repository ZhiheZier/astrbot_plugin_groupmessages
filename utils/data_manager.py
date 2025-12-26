"""
数据管理工具类 - 负责数据的读写和持久化
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from astrbot.api import logger


class DataManager:
    """
    数据管理器
    提供统一的数据读写接口
    """
    
    def __init__(self, data_dir: Path):
        """
        初始化数据管理器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def load_json(self, filename: str, default: Any = None) -> Any:
        """
        从 JSON 文件加载数据
        
        Args:
            filename: 文件名
            default: 文件不存在时返回的默认值
            
        Returns:
            加载的数据或默认值
        """
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            return default if default is not None else {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"成功加载数据文件: {filename}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误 ({filename}): {e}")
            return default if default is not None else {}
        except Exception as e:
            logger.error(f"加载数据文件失败 ({filename}): {e}")
            return default if default is not None else {}
    
    def save_json(self, filename: str, data: Any) -> bool:
        """
        保存数据到 JSON 文件
        
        Args:
            filename: 文件名
            data: 要保存的数据
            
        Returns:
            是否保存成功
        """
        file_path = self.data_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"成功保存数据文件: {filename}")
            return True
        except Exception as e:
            logger.error(f"保存数据文件失败 ({filename}): {e}")
            return False
    
    def file_exists(self, filename: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            filename: 文件名
            
        Returns:
            文件是否存在
        """
        return (self.data_dir / filename).exists()
    
    def delete_file(self, filename: str) -> bool:
        """
        删除文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否删除成功
        """
        file_path = self.data_dir / filename
        
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"成功删除文件: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败 ({filename}): {e}")
            return False

