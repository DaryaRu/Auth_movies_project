from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from src.utils.jwt import decode_token


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    exception_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization:
        raise exception_401
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise exception_401
    payload = await decode_token(token)
    if payload is None:
        raise exception_401
    user_id = payload.get("sub")
    if not user_id:
        raise exception_401
    return UUID(user_id)


CurrentUserDep = Annotated[UUID, Depends(get_current_user)]
