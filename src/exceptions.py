
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


class InvalidTokenError(AuthServiceHTTPException):
    status_code = 401


class TokenExpiredError(AuthServiceHTTPException):
    status_code = 401


class RoleAlreadyExistsException(AuthServiceException):
    detail = "Роль уже существует"


class RoleNotFoundException(AuthServiceException):
    detail = "Роль не найдена"


class UserRoleAlreadyExistsException(AuthServiceException):
    detail = "Роль уже назначена пользователю"


class UserRoleNotFoundException(AuthServiceException):
    detail = "У пользователя нет такой роли"


class NotEnoughPermissionsException(AuthServiceException):
    detail = "Недостаточно прав"


class RoleAlreadyExistsHTTPException(AuthServiceHTTPException):
    status_code = 400


class RoleNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404


class UserRoleAlreadyExistsHTTPException(AuthServiceHTTPException):
    status_code = 400


class UserRoleNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404


class NotEnoughPermissionsHTTPException(AuthServiceHTTPException):
    status_code = 403


class PermissionAlreadyExistsException(AuthServiceException):
    detail = "Право уже существует"


class PermissionNotFoundException(AuthServiceException):
    detail = "Право не найдено"


class RolePermissionAlreadyExistsException(AuthServiceException):
    detail = "Право уже назначено роли"


class RolePermissionNotFoundException(AuthServiceException):
    detail = "У роли нет такого права"


class SystemRoleCannotBeDeletedException(AuthServiceException):
    detail = "Системную роль нельзя удалить"


class PermissionAlreadyExistsHTTPException(AuthServiceHTTPException):
    status_code = 400


class PermissionNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404


class RolePermissionAlreadyExistsHTTPException(AuthServiceHTTPException):
    status_code = 400


class RolePermissionNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404


class SystemRoleCannotBeDeletedHTTPException(AuthServiceHTTPException):
    status_code = 409
