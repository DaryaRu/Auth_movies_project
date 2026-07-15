from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.utils.jwt import decode_token

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> UUID:
    exception_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = await decode_token(credentials.credentials)
    if payload is None:
        raise exception_401
    user_id = payload.get("sub")
    if not user_id:
        raise exception_401
    return UUID(user_id)


CurrentUserDep = Annotated[UUID, Depends(get_current_user)]
