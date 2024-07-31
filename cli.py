from rich import print
from typing import Annotated, Optional

from sqlalchemy.orm import Session
import typer

from app.db.session import SessionLocal
from app.crud.user import create_user, get_user_by_email
from app.db.enums import UserRoleType
from app.schemas.user import UserCreate
from app.core.config import settings


cli = typer.Typer()


@cli.command()
def create_admin(
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
):
    """
    Create an admin user
    """
    if not full_name:
        full_name = settings.admin_name
    if not email:
        email = settings.admin_email
    if not password:
        password = settings.admin_password
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
