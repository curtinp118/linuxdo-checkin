"""
通知模块 - 支持多种通知方式
"""

import os
import re
import random
import time
from datetime import datetime
from loguru import logger
from curl_cffi import requests


class NotificationManager:
    """统一通知管理器"""
    
    def __init__(self):
        # 获取环境变量
        self.gotify_url = os.environ.get("GOTIFY_URL")
        self.gotify_token = os.environ.get("GOTIFY_TOKEN")
        self.sc3_push_key = os.environ.get("SC3_PUSH_KEY")
        self.wxpush_url = os.environ.get("WXPUSH_URL")
        self.wxpush_token = os.environ.get("WXPUSH_TOKEN")
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    def send_all(self, title: str, message: str):
        """发送所有配置的通知"""
        self.send_gotify(title, message)
        self.send_server_chan(title, message)
        self.send_wxpush(title, message)
        self.send_telegram(title, message)
    
    def send_login_result(self, success: bool, method: str, username: str):
        """发送登录结果通知"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if success:
            title = "✅ LinuxDo 签到 - 登录成功"
            message = f"""🎯 **登录成功**

📅 时间：{now}
👤 账号：{username}
🔑 方式：{method}登录

🚀 开始执行浏览任务..."""
        else:
            title = "❌ LinuxDo 签到 - 登录失败"
            message = f"""🎯 **登录失败**

📅 时间：{now}
👤 账号：{username}
🔑 方式：{method}登录

⚠️ 请检查账号密码或Cookie是否正确"""
        
        self.send_all(title, message)
    
    def send_progress(self, current: int, total: int):
        """发送浏览进度通知"""
        now = datetime.now().strftime("%H:%M:%S")
        progress_bar = self._generate_progress_bar(current, total)
        
        title = f"📖 浏览进度 - {current}/{total}"
        message = f"""📊 **浏览进度更新**

⏰ 时间：{now}
📈 进度：{progress_bar}
📝 已浏览：{current} 篇
📋 总计：{total} 篇

💪 继续加油！"""
        
        self.send_all(title, message)
    
    def send_summary(self, username: str, login_method: str, browse_enabled: bool, 
                     browsed_count: int, connect_info: list, elapsed_seconds: float):
        """发送完成任务总体概览通知"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elapsed_min = elapsed_seconds / 60
        
        # 构建连接信息表格
        connect_text = ""
        if connect_info:
            connect_text = "\n📊 **连接信息统计**\n"
            for item in connect_info:
                project = item.get("project", "")
                current = item.get("current", "0")
                requirement = item.get("requirement", "0")
                status = "✅" if current >= requirement else "⚠️"
                connect_text += f"{status} {project}：{current}/{requirement}\n"
        
        # 浏览状态
        browse_status = "✅ 已完成" if browse_enabled and browsed_count > 0 else "⏭️ 已跳过"
        browse_detail = f"{browsed_count} 篇" if browse_enabled and browsed_count > 0 else ""
        
        title = "🎉 LinuxDo 签到 - 任务完成"
        message = f"""🎯 **每日签到任务完成**

📅 时间：{now}
👤 账号：{username}
🔑 登录方式：{login_method}登录
⏱️ 耗时：{elapsed_min:.1f} 分钟

📝 **任务执行情况**
• 登录状态：✅ 成功
• 浏览任务：{browse_status} {browse_detail}
{connect_text}
🎊 今日签到任务已全部完成！"""
        
        self.send_all(title, message)
    
    def _generate_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """生成进度条"""
        filled = int(length * current / total)
        bar = "█" * filled + "░" * (length - filled)
        percentage = int(100 * current / total)
        return f"[{bar}] {percentage}%"
    
    def send_gotify(self, title: str, message: str):
        """发送 Gotify 通知"""
        if not self.gotify_url or not self.gotify_token:
            logger.info("未配置Gotify环境变量，跳过通知发送")
            return False
        
        try:
            response = requests.post(
                f"{self.gotify_url}/message",
                params={"token": self.gotify_token},
                json={"title": title, "message": message, "priority": 1},
                timeout=10,
            )
            response.raise_for_status()
            logger.success("消息已推送至Gotify")
            return True
        except Exception as e:
            logger.error(f"Gotify推送失败: {str(e)}")
            return False
    
    def send_server_chan(self, title: str, message: str):
        """发送 Server酱³ 通知"""
        if not self.sc3_push_key:
            return False
        
        match = re.match(r"sct(\d+)t", self.sc3_push_key, re.I)
        if not match:
            logger.error("❌ SC3_PUSH_KEY格式错误，未获取到UID，无法使用Server酱³推送")
            return False
        
        uid = match.group(1)
        url = f"https://{uid}.push.ft07.com/send/{self.sc3_push_key}"
        params = {"title": title, "desp": message}
        
        attempts = 5
        for attempt in range(attempts):
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                logger.success(f"Server酱³推送成功: {response.text}")
                return True
            except Exception as e:
                logger.error(f"Server酱³推送失败: {str(e)}")
                if attempt < attempts - 1:
                    sleep_time = random.randint(180, 360)
                    logger.info(f"将在 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
        
        return False
    
    def send_wxpush(self, title: str, message: str):
        """发送 wxpush 通知"""
        if not self.wxpush_url or not self.wxpush_token:
            logger.info("未配置 WXPUSH_URL 或 WXPUSH_TOKEN，跳过通知发送")
            return False
        
        try:
            response = requests.post(
                f"{self.wxpush_url}/wxsend",
                headers={
                    "Authorization": self.wxpush_token,
                    "Content-Type": "application/json",
                },
                json={"title": title, "content": message},
                timeout=10,
            )
            response.raise_for_status()
            logger.success(f"wxpush 推送成功: {response.text}")
            return True
        except Exception as e:
            logger.error(f"wxpush 推送失败: {str(e)}")
            return False
    
    def send_telegram(self, title: str, message: str):
        """发送 Telegram 通知"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.info("未配置 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，跳过 Telegram 通知")
            return False
        
        try:
            telegram_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            text = f"🤖 {title}\n\n{message}"
            response = requests.post(
                telegram_url,
                json={
                    "chat_id": self.telegram_chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.success("Telegram 推送成功")
            return True
        except Exception as e:
            logger.error(f"Telegram 推送失败: {str(e)}")
            return False
