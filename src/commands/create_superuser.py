import asyncio

import rich
import typer
from pydantic import ValidationError

from src.databases.pg import async_session_maker
from src.exceptions import UserAlreadyexistsException
from src.schemas.users import UserRequestScheme
from src.services.auth import AuthService
from src.utils.db_manager import DBManager
from src.utils.hashes import HashArgon2Service
from src.utils.tokens import JWTTokenService

app = typer.Typer()


async def _create_superuser(
    email: str,
    password: str,
) -> None:
    admin = UserRequestScheme(
        email=email,
        password=password,
    )
    async with DBManager(session_factory=async_session_maker) as db:
        await AuthService(
            HashArgon2Service(),
            JWTTokenService(),
            db,
        ).create_admin(admin)


@app.command()
def create(
    email: str = typer.Option(
        ...,
        prompt="Введите адрес электронной почты",
        help="Email администратора",
    ),
    password: str = typer.Option(
        ...,
        prompt="Введите пароль",
        hide_input=True,
        help="Пароль администратора",
    ),
):
    confirm_password = typer.prompt(
        "Повторите пароль",
        hide_input=True,
    )

    if password != confirm_password:
        rich.print("[red]Пароли не совпадают[/red]")
        raise typer.Exit(code=1)
    try:
        asyncio.run(_create_superuser(email, password))
        rich.print(
            f"[green]Администратор {email} успешно создан[/green]"
        )
    except ValidationError:
        rich.print(
            "[red]Невалидный адрес электронной почты[/red]"
        )
    except UserAlreadyexistsException as exc:
        rich.print(
            f"[red]{exc.detail}[/red]"
        )
    except Exception:
        rich.print(
            "[red]Не удалось создать администратора[/red]"
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
