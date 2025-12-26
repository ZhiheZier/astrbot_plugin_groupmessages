# 群聊消息管理插件 💬

一个功能丰富、模块化设计的群聊消息管理插件，提供签到、积分系统、涩图等功能。

## 🏗️ 架构设计

### 模块化结构
```
astrbot_plugin_groupmessages/
├── main.py                 # 插件入口，负责模块加载和协调
├── metadata.yaml          # 插件元数据
├── README.md              # 文档
├── _conf_schema.json      # 配置文件定义
├── modules/               # 功能模块目录
│   ├── __init__.py
│   ├── base.py           # 基础模块类
│   ├── checkin.py        # 签到模块 ✅
│   └── setu.py           # 涩图模块 ✅
└── utils/                 # 工具类
    ├── __init__.py
    └── data_manager.py   # 数据管理工具
```

### 设计特点
- ✅ **模块化设计**：每个功能独立为一个模块，互不干扰
- ✅ **易于扩展**：添加新功能只需创建新模块并注册
- ✅ **统一管理**：数据管理、日志记录等统一处理
- ✅ **可配置**：通过配置文件控制功能开关和参数
- ✅ **跨群通用**：同一用户在所有群聊和私聊中积分通用

## ✨ 已实现功能

### 📅 签到系统
每日签到获取随机积分，支持积分系统和历史记录。

#### 功能特性
- **随机奖励系统**
  - 普通签到：随机获得 10-49 积分
  - 特殊奖励：
    - 50 积分（20% 概率）：星期四额外提示"今天是疯狂星期四，v你50"
    - 213 积分（2% 概率）："才不是2B呢"
    - 648 积分（1% 概率）："拿去充二游吧"
    - 51-200 积分（10% 概率）："运气不错哦"
- **积分系统**：自动累计签到积分，记录历史
- **跨群通用**：同一用户在所有群聊和私聊中积分通用

#### 使用命令
```
签到                # 每日签到
积分 / 我的积分     # 查询我的积分
积分记录            # 查看积分变动历史（最近10条）
```

#### 使用示例
```
用户: 签到
Bot: @用户 
     签到成功，获得 35 积分
     
     当前积分: 235 积分
     累计签到: 20 次

用户: 积分
Bot: @用户 
     当前积分：235分
     累计签到次数：20次
     上次签到：2025-11-26

用户: 积分记录
Bot: @用户 的积分记录
     2025-11-26 11:30:15 签到 +35
     2025-11-25 19:25:30 签到 +42
     2025-11-25 18:20:10 涩图 -10
```

### 🖼️ 涩图系统
消耗积分获取随机涩图，基于 [Lolicon API](https://api.lolicon.app)。

#### 功能特性
- **涩图**：消耗 10 积分
- **R18涩图**：消耗 30 积分
- **排除AI作品**：默认排除AI生成的作品
- **积分不足提示**：余额不足时会提示
- **自动记录**：每次获取都会记录在积分历史中
- **跨群通用**：积分在所有群聊和私聊中通用

#### 使用命令
```
来张涩图       # 获取涩图（消耗10积分）
来张更涩的     # 获取R18涩图（消耗30积分）
```

#### 使用示例
```
用户: 来张涩图
Bot: 正在获取涩图，请稍候...
Bot: @用户 
     涩图来啦！
     标题：夏日泳装
     作者：XX画师
     消耗积分：10 分
     剩余积分：225 分
     [图片]

用户: 来张更涩的
Bot: @用户 
     积分不足！
     R18涩图需要 30 积分，当前积分：5 分
```

### 🎲 抢劫系统
抢劫其他用户积分，动态成功率系统。

#### 功能特性
- **动态成功率**：初始成功率50%，成功后-1%，失败后+1%
- **积分门槛**：积分大于50才可以抢劫
- **随机金额**：成功最多抢50积分，失败最多被抢50积分
- **冷却时间**：30分钟冷却
- **管理员奖励**：超级管理员可以奖励积分

#### 使用命令
```
抢劫 @用户       # 抢劫指定用户（需要50积分）
奖励 @用户 数字  # 管理员奖励积分（超级管理员专用）
```

#### 使用示例
```
用户: 抢劫 @小明
Bot: @用户 
     抢劫成功！
     获得积分：+35 分
     当前积分：265 分
     当前成功率：49%

用户: 抢劫 @小红
Bot: @用户 
     抢劫失败！
     损失积分：-28 分
     当前积分：237 分
     当前成功率：50%

管理员: 奖励 @用户 100
Bot: 已成功奖励 @用户 100 积分
     当前积分：337 分
```

## ⚙️ 配置说明

插件支持通过 AstrBot 管理面板或配置文件进行配置。

### 配置项说明

- **checkin_enabled** (布尔值，默认: true)
  - 启用或禁用签到功能
  - 开启后用户可以使用签到功能获取随机积分

- **normal_setu_enabled** (布尔值，默认: true)
  - 启用或禁用涩图功能
  - 开启后用户可以消耗10积分获取涩图
  - 需要签到模块同时启用

- **r18_setu_enabled** (布尔值，默认: false)
  - 启用或禁用R18涩图功能
  - 开启后用户可以消耗30积分获取R18涩图
  - 需要签到模块同时启用
  - **默认关闭，需要手动开启**

- **setu_cooldown** (整数，默认: 60)
  - 涩图功能冷却时间（秒）
  - 用户使用涩图功能后需要等待的时间
  - 设置为 0 表示无冷却限制
  - 建议设置：30-120 秒

- **exclude_ai** (布尔值，默认: true)
  - 排除AI作品
  - 开启后获取的涩图将排除AI生成的作品
  - **默认开启，推荐保持开启**

- **robbery_enabled** (布尔值，默认: true)
  - 启用或禁用抢劫功能
  - 开启后用户可以抢劫其他用户的积分，管理员可以奖励积分
  - 需要签到模块同时启用

### 配置文件

配置文件自动生成在：`data/config/astrbot_plugin_groupmessages.json`

### 配置示例

通过 AstrBot 配置面板修改，或直接编辑配置文件：

```json
{
  "checkin_enabled": true,
  "normal_setu_enabled": true,
  "r18_setu_enabled": false,
  "setu_cooldown": 60,
  "exclude_ai": true,
  "robbery_enabled": true
}
```

### 群聊管理功能

#### 插件总开关

超级管理员可以在群聊中开启/关闭整个插件：

```
开启群聊消息插件    # 在本群启用所有功能
关闭群聊消息插件    # 在本群禁用所有功能
```

#### 涩图功能开关

超级管理员可以单独控制每个群的涩图功能：

```
开启普通涩图        # 在本群启用涩图功能
关闭普通涩图        # 在本群禁用涩图功能
开启R18涩图         # 在本群启用R18涩图
关闭R18涩图         # 在本群禁用R18涩图
```

**使用示例：**
```
管理员: 关闭R18涩图
Bot: 已关闭本群的R18涩图功能

用户: 来张更涩的
Bot: 本群已禁用R18涩图功能

管理员: 开启R18涩图
Bot: 已开启本群的R18涩图功能
```

**冷却时间示例：**
```
用户: 来张涩图
Bot: 正在获取涩图，请稍候...
Bot: @用户 
     涩图来啦！
     [图片]

用户: 来张涩图  # 立即再次请求
Bot: @用户 
     冷却中，请等待 58.5 秒后重试
```

**优先级说明：**
1. 群聊设置优先于全局配置
2. 如果群聊未设置，则使用全局配置
3. 插件总开关优先于功能开关

## 📦 数据存储

所有数据保存在 `data/plugin_data/astrbot_plugin_groupmessages/` 目录下：

```
plugin_data/astrbot_plugin_groupmessages/
└── checkin_data.json      # 签到数据
```

## 🔧 如何添加新功能

### 1. 创建新模块

在 `modules/` 目录下创建新文件，例如 `new_feature.py`：

```python
"""
新功能模块
"""

from astrbot.api.event import filter, AstrMessageEvent
from .base import BaseModule
from ..utils import DataManager


class NewFeatureModule(BaseModule):
    """新功能模块"""
    
    def __init__(self, context, data_dir, config: dict | None = None):
        super().__init__(context, data_dir)
        self.config = config if config is not None else {}
        self.data_manager = DataManager(data_dir)
    
    async def initialize(self):
        """初始化模块"""
        self.log_info("新功能模块已初始化")
    
    async def terminate(self):
        """终止模块"""
        self.log_info("新功能模块已终止")
    
    @filter.command("命令")
    async def command_handler(self, event: AstrMessageEvent):
        """命令处理"""
        return event.plain_result("功能响应...")
```

### 2. 注册模块

在 `modules/__init__.py` 中导出新模块：

```python
from .new_feature import NewFeatureModule

__all__ = ['BaseModule', 'CheckInModule', 'NewFeatureModule']
```

### 3. 加载模块

在 `main.py` 的 `_register_modules()` 方法中添加：

```python
# 导入模块
from .modules import NewFeatureModule

# 在 _register_modules 方法中注册
new_feature_enabled = self.config.get("new_feature_enabled", True)
if new_feature_enabled:
    new_config = self.config.get("new_feature_config", {})
    new_module = NewFeatureModule(self.context, self.data_dir, new_config)
    self.modules.append(new_module)
    self._register_module_handlers(new_module)
    logger.info("✓ 新功能模块已加载")
```

### 4. 添加配置（可选）

如果新功能需要开关，在 `_conf_schema.json` 中添加：

```json
{
  "new_feature_enabled": {
    "type": "boolean",
    "description": "启用新功能",
    "default": true
  }
}
```

## 📊 性能优化

- **懒加载**：模块按需加载，禁用的模块不会被实例化
- **数据缓存**：减少文件读写
- **异步处理**：所有 IO 操作异步化
- **内存控制**：历史记录限制数量

## 📝 版本历史

### v1.0.0
- ✅ 模块化架构设计
- ✅ 签到系统完整实现
- ✅ 可配置的功能开关和参数
- ✅ 数据持久化
- ✅ 积分排行榜
- ✅ 完善的日志系统

## 🤝 贡献

欢迎贡献新功能模块！只需：
1. Fork 本项目
2. 创建新的功能模块
3. 提交 Pull Request

## 📄 许可证

本插件遵循 AstrBot 插件开发规范，开源免费使用。

## 💡 支持

- 文档: [AstrBot 帮助文档](https://astrbot.app)
- 仓库: https://github.com/ZhiheZier/astrbot_plugin_groupmessages
- 问题反馈: 在仓库提交 Issue
