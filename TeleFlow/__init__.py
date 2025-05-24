import asyncio
import json
from typing import Dict, Optional, Callable, Any, Awaitable, List, Union
from types import SimpleNamespace
import aiohttp

class TelegramAPIError(Exception):
    pass

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.handlers: Dict[str, Callable[[Any, str], Awaitable[None]]] = {}
        self.offset = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False

    async def validate_url(self, url: str) -> bool:
        """Validate if the URL is accessible and returns a valid content type."""
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                if response.status != 200:
                    return False
                content_type = response.headers.get('Content-Type', '').lower()
                return content_type.startswith(('audio/', 'application/pdf', 'image/', 'video/', 'application/octet-stream'))
        except Exception as e:
            print(f"URL validation failed for {url}: {e}")
            return False

    async def __call__(self, method: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Any:
        if self.session is None:
            self.session = aiohttp.ClientSession()

        url = f"{self.api_url}/{method}"

        # Validate URLs in data
        if data:
            for key, value in data.items():
                if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                    if not await self.validate_url(value):
                        raise TelegramAPIError(f"Invalid or inaccessible URL: {value}")

        # Handle file uploads
        if files:
            form_data = aiohttp.FormData()
            if data:
                for key, value in data.items():
                    if value is not None:
                        if isinstance(value, (dict, list)):
                            form_data.add_field(key, json.dumps(value))
                        else:
                            form_data.add_field(key, str(value))

            open_files = []
            for key, file_info in files.items():
                if isinstance(file_info, tuple):
                    form_data.add_field(key, file_info[0], filename=file_info[1])
                elif isinstance(file_info, str):
                    if file_info.startswith('http://') or file_info.startswith('https://'):
                        if await self.validate_url(file_info):
                            form_data.add_field(key, file_info)
                        else:
                            raise TelegramAPIError(f"Invalid file URL: {file_info}")
                    else:
                        try:
                            f = open(file_info, 'rb')
                            open_files.append(f)
                            form_data.add_field(key, f, filename=file_info.split('/')[-1].split('\\')[-1])
                        except FileNotFoundError:
                            raise TelegramAPIError(f"File not found: {file_info}")
                else:
                    form_data.add_field(key, file_info)

            async with self.session.post(url, data=form_data) as response:
                result = await response.json()

            for f in open_files:
                f.close()
        else:
            headers = {'Content-Type': 'application/json'} if data else None
            async with self.session.post(url, json=data, headers=headers) as response:
                result = await response.json()

        if not result.get('ok'):
            error_desc = result.get('description', 'Unknown error')
            raise TelegramAPIError(f"Telegram API Error: {error_desc}")

        return json.loads(json.dumps(result['result']), object_hook=lambda d: SimpleNamespace(**d))

    def handler(self, update_type: str = None):
        def decorator(func: Callable[[Any, str], Awaitable[None]]):
            self.handlers[update_type or '*'] = func
            return func
        return decorator

    async def get_updates(self, timeout: int = 30) -> list:
        params = {
            "offset": self.offset,
            "timeout": timeout,
            "allowed_updates": list(self.handlers.keys()) if '*' not in self.handlers else None
        }
        result = await self("getUpdates", data=params)
        return result

    async def process_updates(self, updates: list):
        for update in updates:
            update_id = getattr(update, 'update_id', None)
            if update_id:
                self.offset = max(self.offset, update_id + 1)

            update_type = None
            for key in update.__dict__:
                if key != "update_id":
                    update_type = key
                    break

            handler = self.handlers.get(update_type, self.handlers.get('*'))
            if handler:
                update_part = getattr(update, update_type)
                try:
                    await handler(update_part, update_type)
                except Exception as e:
                    print(f"Error handling update {update_type}: {e}")

    async def start_polling(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        self.running = True
        try:
            while self.running:
                try:
                    updates = await self.get_updates()
                    if updates:
                        await self.process_updates(updates)
                except asyncio.CancelledError:
                    break
                except TelegramAPIError as e:
                    print(f"Telegram API Error: {e}")
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    await asyncio.sleep(5)
        finally:
            if self.session:
                await self.session.close()
                self.session = None

    def stop_polling(self):
        self.running = False

    def run(self):
        try:
            asyncio.run(self.start_polling())
        except KeyboardInterrupt:
            self.stop_polling()
            print("Bot stopped")
            
