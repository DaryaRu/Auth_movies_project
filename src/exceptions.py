
from fastapi import HTTPException


class AuthServiceException(Exception):
    detail = "Неожиданная ошибка"

    def __init__(self, *args, **kwargs):
        super().__init__(self.detail, *args, **kwargs)
        
class ObjectNotFoundException(AuthServiceException):
    detail = "Объект не найден"
    
    
class ObjectAlreadyexistsException(AuthServiceException):
    detail = "Объект уже существует"


class UserAlreadyexistsException(AuthServiceException):
    detail = "Пользователь уже зарегестрирован в системе"
    
    
class UserNotFoundError(AuthServiceException):
    detail = "Пользователь не найден"


class VerifyPasswordError(AuthServiceException):
    detail = "Неверный пароль"
    
    
class DecodeTokenException(AuthServiceException):
    detail = "Ошибка декодирования токена"


class TokenKeysException(AuthServiceException):
    detail = "Несоответствие данных токена"
    
    
class AuthServiceHTTPException(HTTPException):
    status_code = 500
    detail = None

    def __init__(self, detail: str | None = None):
        if detail is None:
            detail = getattr(self, "detail", None)
        super().__init__(status_code=self.status_code, detail={"error": detail})
    
    
class UserAlreadyexistsHTTPException(AuthServiceHTTPException):
    status_code = 400
    
    
class UserNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404
    
    
class VerifyPasswordHTTPException(AuthServiceHTTPException):
    status_code = 401
    
    
class DecodeTokenHTTPException(AuthServiceHTTPException):
    status_code = 403


class TokenKeysHTTPException(AuthServiceHTTPException):
    status_code = 403
