"""Реестр отправителей. Пока зарегистрирован только email. Можно в дальнейшем добавить sms/push."""

from senders.base import Sender
from senders.email import EmailSender

SENDERS: dict[str, Sender] = {
    "email": EmailSender(),
}
