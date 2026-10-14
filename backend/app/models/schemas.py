from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20000)


class ChatResponse(BaseModel):
    response: str


class LearnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


class LearnResponse(BaseModel):
    message: str