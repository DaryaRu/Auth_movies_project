import pathlib
import sys

import typer

sys.path.append(str(pathlib.Path(__file__).parent.parent))

from src.commands.create_superuser import app as superuser_app

app = typer.Typer()

app.add_typer(
    superuser_app,
    name="superuser",
)


if __name__ == "__main__":
    app()
