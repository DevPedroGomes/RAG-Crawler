from pydantic import BaseModel, EmailStr

class SignUpIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CrawlIn(BaseModel):
    url: str

class ChatIn(BaseModel):
    question: str
