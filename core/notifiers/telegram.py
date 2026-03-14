import asyncio
import aiohttp
import json
import os
from datetime import datetime
from core.config import settings
from core.logger import logger, LogCategory

class TelegramNotifier:
    """
    Telegram Notifier for Sentinel Governance Events.
    Sends instant alerts to the operator for high-stakes actions.
    """
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.debug(LogCategory.SYSTEM, "Telegram notifications disabled (missing token or chat_id)")

    async def send_message(self, text: str, priority: str = "LOW"):
        """Send a message via Telegram Bot API"""
        if not self.enabled:
            return

        # Format message
        icon = "🛡️" if priority == "HIGH" else "ℹ️"
        if "KILL SWITCH" in text.upper(): icon = "🚨"
        if "LOCK" in text.upper(): icon = "🔒"
        
        formatted_text = f"{icon} *SENTINEL ALERT*\n\n{text}\n\n_Time: {datetime.now().strftime('%H:%M:%S')}_"
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": formatted_text,
            "parse_mode": "Markdown"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as response:
                    if response.status != 200:
                        logger.debug(LogCategory.SYSTEM, f"Telegram API Error: {response.status}")
        except Exception as e:
            logger.debug(LogCategory.SYSTEM, f"Failed to send Telegram alert: {e}")

    def notify(self, text: str, priority: str = "LOW"):
        """Fire and forget notification"""
        if not self.enabled:
            return
            
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.send_message(text, priority))
        except RuntimeError:
            pass

# Global Singleton
notifier = TelegramNotifier()
