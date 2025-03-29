import aiohttp
import asyncio
import json
from typing import Dict, Optional, Callable, Any, Union, Awaitable

class TelegramBot:
    """A simple and efficient asynchronous Telegram Bot API client."""
    
    def __init__(self, token: str):
        """
        Initialize the Telegram bot with the given token.
        
        Args:
            token: Your Telegram bot token from @BotFather
        """
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.handlers: Dict[str, Callable[[Dict, str], Awaitable[None]]] = {}
        self.offset = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self._running = False
        
    async def __call__(self, method: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Dict:
        """
        Make an API call to Telegram Bot API.
        
        Args:
            method: API method name (e.g., 'getMe', 'sendMessage')
            data: Dictionary of parameters
            files: Dictionary of files to upload
            
        Returns:
            Dictionary with API response
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
        url = f"{self.api_url}/{method}"
        form_data = aiohttp.FormData()
        
        if data:
            for key, value in data.items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        form_data.add_field(key, json.dumps(value))
                    else:
                        form_data.add_field(key, str(value))
        
        if files:
            for key, file_info in files.items():
                if isinstance(file_info, tuple):
                    form_data.add_field(key, file_info[0], filename=file_info[1])
                elif isinstance(file_info, str):
                    filename = file_info.split('/')[-1]
                    with open(file_info, 'rb') as f:
                        form_data.add_field(key, f, filename=filename)
                else:
                    form_data.add_field(key, file_info)
        
        async with self.session.post(url, data=form_data) as response:
            result = await response.json()
            if not result.get('ok'):
                raise TelegramAPIError(result.get('description', 'Unknown error'))
            return result
    
    def handler(self, update_type: str = None):
        """
        Decorator to register a handler for specific update types or all updates.
        
        Args:
            update_type: The type of update to handle (e.g., 'message', 'callback_query')
                        If None, handles all updates.
        """
        def decorator(func: Callable[[Dict, str], Awaitable[None]]):
            self.handlers[update_type or '*'] = func
            return func
        return decorator
    
    async def get_updates(self, timeout: int = 30) -> list:
        """
        Get new updates from Telegram using long polling.
        
        Args:
            timeout: Timeout in seconds for long polling
            
        Returns:
            List of updates
        """
        params = {
            "offset": self.offset,
            "timeout": timeout,
            "allowed_updates": list(self.handlers.keys()) if '*' not in self.handlers else None
        }
        
        result = await self("getUpdates", data=params)
        return result.get("result", [])
    
    async def process_updates(self, updates: list):
        """
        Process a list of updates by calling the appropriate handlers.
        """
        for update in updates:
            update_id = update.get("update_id")
            if update_id:
                self.offset = max(self.offset, update_id + 1)
            
            update_type = None
            for key in update:
                if key != "update_id":
                    update_type = key
                    break
            
            # Call specific handler if exists, otherwise call generic handler
            handler = self.handlers.get(update_type, self.handlers.get('*'))
            if handler:
                await handler(update[update_type], update_type)
    
    async def start_polling(self):
        """
        Start polling for updates from Telegram.
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
        self._running = True
        try:
            while self._running:
                try:
                    updates = await self.get_updates()
                    if updates:
                        await self.process_updates(updates)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error processing updates: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
        finally:
            if self.session:
                await self.session.close()
                self.session = None
    
    def stop_polling(self):
        """Stop the polling loop."""
        self._running = False
    
    def run(self):
        """
        Run the bot with polling (blocking call).
        """
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.start_polling())
        except KeyboardInterrupt:
            self.stop_polling()
            print("Bot stopped")

class TelegramAPIError(Exception):
    """Exception raised for Telegram API errors."""
    pass