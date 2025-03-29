# Telegram Bot API

A simple and efficient asynchronous Telegram Bot API client.

## Installation

```bash
pip install -U TeleFlow
```

## Usage

```python
from TeleFlow import TelegramBot

bot = TelegramBot("YOUR_BOT_TOKEN")

@bot.handler('message')
async def handle_message(message, update_type):
    if message.text == '/start':
        await bot("sendMessage", {
            'chat_id': message.chat['id'],
            'text': 'Hello!'
        })

bot.run()
```
