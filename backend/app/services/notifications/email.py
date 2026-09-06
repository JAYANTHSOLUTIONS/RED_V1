"""Email notification channel provider.

Provides decoupled SMTP email dispatch with bounded timeouts, async thread isolation,
graceful handling of unconfigured environments, and non-crashing failure modes.
"""
import asyncio
from email.message import EmailMessage
import logging
import smtplib
from typing import Any, Dict, Optional
import uuid

from app.core.config import get_settings
from app.schemas.notification import DeliveryResult, DeliveryStatus
from app.services.notifications.base import BaseNotificationChannel

logger = logging.getLogger("red.notifications.email")


def _send_smtp_sync(
    host: str,
    port: int,
    username: Optional[str],
    password: Optional[str],
    from_addr: str,
    to_addr: str,
    subject: str,
    body: str,
    use_tls: bool,
    timeout: int,
) -> None:
    """Synchronous SMTP email delivery run in a separate worker thread."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    with smtplib.SMTP(host=host, port=port, timeout=timeout) as server:
        if use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(msg)


class EmailNotificationChannel(BaseNotificationChannel):
    """Channel provider for sending emails via SMTP."""

    @property
    def channel_name(self) -> str:
        return "EMAIL"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: Optional[str] = None,
        use_tls: Optional[bool] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.from_addr = from_addr if from_addr is not None else settings.SMTP_FROM
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.timeout = timeout if timeout is not None else settings.SMTP_TIMEOUT_SECONDS

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        notification_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        """Send email to recipient asynchronously."""
        # 1. Validate recipient email
        if not recipient or "@" not in recipient or "." not in recipient:
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                channel="EMAIL",
                message="Invalid or missing recipient email address.",
            )

        # 2. Check if SMTP is configured
        if not self.host:
            logger.info("SMTP host not configured; email dispatch skipped.")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.NOT_CONFIGURED,
                channel="EMAIL",
                message="SMTP host is not configured.",
            )

        # 3. Deliver via thread-isolated SMTP call
        try:
            await asyncio.to_thread(
                _send_smtp_sync,
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                from_addr=self.from_addr,
                to_addr=recipient.strip(),
                subject=title.strip(),
                body=message.strip(),
                use_tls=self.use_tls,
                timeout=self.timeout,
            )
            logger.info(f"Email delivered successfully to recipient {recipient} (type: {notification_type})")
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.SENT,
                channel="EMAIL",
                message="Email dispatched successfully.",
            )
        except Exception as exc:
            # External delivery failures must never crash the caller
            logger.error(f"SMTP delivery failed for recipient {recipient}: {exc}", exc_info=False)
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                channel="EMAIL",
                message=f"SMTP dispatch error: {str(exc)}",
            )
