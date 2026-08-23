"""Реестр отправителей: email, push (Redis Pub/Sub → WebSocket)."""

from senders.base import Sender
from senders.email import EmailSender
from senders.push import PushSender

SENDERS: dict[str, Sender] = {
    "email": EmailSender(),
    "push": PushSender(),
}
