from telegram import Bot

class TelegramClient:
    def __init__(self, token: str):
        if len(token) > 0:
            self.bot = Bot(token=token)
            self.work = True
        else:
            self.work = False


    async def send_message(self, chat_id: str, text: str):
        if self.work:
            await self.bot.send_message(chat_id=chat_id, text=text)