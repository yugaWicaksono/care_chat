from pydantic import BaseModel


class ChatIn(BaseModel):
    message: str