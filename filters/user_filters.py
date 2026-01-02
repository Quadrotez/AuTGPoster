from aiogram.types import Message
from aiogram.filters import BaseFilter

from typing import Union

class CheckPayload(BaseFilter):
    async def __call__(self, message: Message) -> Union[bool, dict]:
        if not message.text:
            return False
        
        return len(message.text.split()) > 1
