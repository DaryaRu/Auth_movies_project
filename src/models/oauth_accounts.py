from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.databases.pg import Base, BaseORM


class OAuthAccountORM(Base, BaseORM):
    """
    OAuth-аккаунт пользователя, привязанный к внешнему провайдеру.

    Атрибуты:
        user_id: Идентификатор пользователя в системе.
        provider: Название провайдера (google, yandex, vk).
        provider_user_id: Идентификатор пользователя на стороне провайдера.
        user: Пользователь, которому принадлежит аккаунт.
    """

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        Index(
            "ix_oauth_accounts_provider_provider_user_id",
            "provider",
            "provider_user_id",
            unique=True,
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(String(50))
    provider_user_id: Mapped[str] = mapped_column(String(255))

    user: Mapped["UserORM"] = relationship(back_populates="oauth_accounts")
