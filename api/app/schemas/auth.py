from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def _bcrypt_limit(value: str) -> str:
    # bcrypt uzima najvise 72 bajta; sve preko toga tiho ne bi ulazilo u hash
    if len(value.encode()) > 72:
        raise ValueError("Lozinka smije imati najvise 72 bajta")
    return value


Password = Annotated[str, Field(min_length=1), AfterValidator(_bcrypt_limit)]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: Password


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
