
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
    
    
class UserNotFoundException(AuthServiceException):
    detail = "Пользователь не найден"


class VerifyPasswordException(AuthServiceException):
    detail = "Неверный пароль"
    
    
class PasswordNotSetException(AuthServiceException):
    detail = "Пароль не установлен"
    
    
class DecodeTokenException(AuthServiceException):
    detail = "Ошибка декодирования токена"


class TokenKeysException(AuthServiceException):
    detail = "Несоответствие данных токена"
    
    
class TokenTypeExeption(AuthServiceException):
    detail = "Несоответствие типа токена"
    
    
class TokenExeption(AuthServiceException):
    detail = "Невалидный токен"
    
    
class TokenNotFoundExeption(AuthServiceException):
    detail = "Токен не обнаружен"
    
    
class ProviderException(AuthServiceException):
    detail = "Ошибка авторизации с помощью провайдера"
    
    
class OAuthStateException(AuthServiceException):
    detail = "Ошибка проверки state переданного провайдером"
    
    
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
    
    
class PasswordNotSetHTTPException(AuthServiceHTTPException):
    status_code = 401
    
    
class DecodeTokenHTTPException(AuthServiceHTTPException):
    status_code = 403


class TokenKeysHTTPException(AuthServiceHTTPException):
    status_code = 403


class InvalidTokenHTTPException(AuthServiceHTTPException):
    status_code = 401


class TokenExpiredError(AuthServiceHTTPException):
    status_code = 401
    
    
class ProviderHTTPException(AuthServiceHTTPException):
    status_code = 502
    
    
class OAuthStateHTTPException(AuthServiceHTTPException):
    status_code = 400


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
    
    
class PasswordAlreadySetException(AuthServiceException):
    detail = "Пароль уже установлен. Используйте смену пароля."


class PasswordAlreadySetHTTPException(AuthServiceHTTPException):
    status_code = 409


class OAuthAccountNotLinkedException(AuthServiceException):
    detail = "Указанный аккаунт не привязан к профилю"


class LastAuthMethodRestrictionException(AuthServiceException):
    detail = "Нельзя отвязать единственный способ входа. " \
             "Установите пароль или привяжите другой сервис."


class OAuthAccountNotLinkedHTTPException(AuthServiceHTTPException):
    status_code = 400


class LastAuthMethodRestrictionHTTPException(AuthServiceHTTPException):
    status_code = 400


class InvalidProviderException(AuthServiceException):
    detail = "Некорректный провайдер"


class InvalidProviderHTTPException(AuthServiceHTTPException):
    status_code = 400


class SubscriptionNotFoundException(AuthServiceException):
    detail = "Подписка не найдена"


class SubscriptionAlreadyExistsException(AuthServiceException):
    detail = "Подписка с таким кодом уже существует"


class SubscriptionInactiveException(AuthServiceException):
    detail = "Подписка неактивна"


class UserSubscriptionNotFoundException(AuthServiceException):
    detail = "Активная подписка пользователя не найдена"


class SubscriptionNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404


class SubscriptionAlreadyExistsHTTPException(AuthServiceHTTPException):
    status_code = 400


class SubscriptionInactiveHTTPException(AuthServiceHTTPException):
    status_code = 400


class UserSubscriptionNotFoundHTTPException(AuthServiceHTTPException):
    status_code = 404
