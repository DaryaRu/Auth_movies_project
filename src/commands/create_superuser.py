import asyncio
import logging
import pathlib
import sys

import rich

if __name__ == "__main__":
    sys.path.append(str(pathlib.Path(__file__).parent.parent.parent))

    from src.databases.pg import async_session_maker
    from src.services.auth import AuthService
    from src.utils.db_manager import DBManager
    from src.utils.hashes import HashBcryptService
    from src.utils.tokens import JWTTokenService
    from src.schemas.users import UserRequestScheme


async def create_admin():
    """Асинхронная функция для интерактивного создания администратора.

    1. Запрашивает у пользователя email и пароль.
    2. Проверяет совпадение пароля и подтверждения.
    3. Добавляет администратора в базу данных через `AuthService.add_admin`.
    4. Логирует ошибки и выводит сообщения о статусе выполнения.

    Uses:
        - `DBManager` для асинхронной работы с базой данных.
        - `AuthService` для управления пользователями и добавления администратора.

    Side Effects:
        - Создаёт запись администратора в базе данных.
        - Печатает сообщения в консоль с помощью `rich`.
        - В случае ошибок логирует их через `logging`.

    Raises:
        SystemExit: если пароли не совпадают.
    """
    email = input("Введите адрес электронной почты: ")
    password = input("Введите пароль: ")
    confirm_password = input("Повтороите пароль: ")
    if password != confirm_password:
        rich.print("[red]Пароли не совпадают")
        sys.exit(1)
    try:
        admin = UserRequestScheme(email=email, password=password)
        async with DBManager(session_factory=async_session_maker) as db:
            await AuthService(HashBcryptService(), JWTTokenService(), db).create_admin(admin)
        rich.print(f"[green]Администратор {email} успешно создан")
    except Exception as e:
        logging.error(e)
        rich.print("[red]Введите корректные данные")


if __name__ == "__main__":
    asyncio.run(create_admin())
