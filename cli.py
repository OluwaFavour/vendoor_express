from rich import print
from typing import Annotated

from sqlalchemy.orm import Session
import typer

from app.db.session import SessionLocal
from app.crud.user import create_user, get_user_by_email
from app.db.enums import UserRoleType
from app.schemas.user import UserCreate


cli = typer.Typer()


@cli.command()
def create_admin(
    full_name: Annotated[
        str, typer.Option(prompt=True, help="Full name of the admin user")
    ],
    email: Annotated[str, typer.Option(prompt=True, help="Email of the admin user")],
    password: Annotated[
        str,
        typer.Option(
            prompt=True,
            hide_input=True,
            confirmation_prompt=True,
            help="Password of the admin user, must be at least 8 characters long, contain at least one digit, one uppercase letter, one lowercase letter, one special character and must not contain spaces",
        ),
    ],
):
    """
    Create an admin user
    """
    db: Session = SessionLocal()
    if get_user_by_email(db, email):
        print(f"[bold red]Alert:[/bold red] [bold]{email}[/bold] already exists")
        return
    user = UserCreate(
        full_name=full_name, email=email, password=password, role=UserRoleType.ADMIN
    )
    create_user(db, user)
    print(f"Admin user {email} created successfully")


if __name__ == "__main__":
    cli()
