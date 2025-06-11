from pydantic import BaseModel

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    refresh_token_expires_in: int
    role: str

