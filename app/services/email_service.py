
import smtplib
from email.message import EmailMessage
from html import escape

from app.core.config import get_settings


def send_password_reset_email(
    recipient_email: str,
    reset_url: str,
) -> None:
    """
    Send a password-reset email using the configured SMTP server.

    In local development, this sends the message to Mailpit.
    """
    settings = get_settings()

    message = EmailMessage()
    message["Subject"] = "Reset your Paw Pantry password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient_email

    message.set_content(
        f"""Hello,

We received a request to reset your Paw Pantry account password.

Use the following link to reset your password:

{reset_url}

This link expires in
{settings.password_reset_token_expire_minutes} minutes.

If you did not request a password reset, you can ignore this email.

Paw Pantry Team
"""
    )

    safe_url = escape(reset_url, quote=True)

    message.add_alternative(
        f"""\
<html>
  <body>
    <h2>Password Reset</h2>
    <p>Hello,</p>
    <p>We received a request to reset your Paw Pantry password.</p>
    <p>
      <a href="{safe_url}">Reset My Password</a>
    </p>
    <p>
      This link expires in
      {settings.password_reset_token_expire_minutes} minutes.
    </p>
    <p>
      If you did not request this, you can safely ignore this email.
    </p>
    <p>Paw Pantry Team</p>
  </body>
</html>
""",
        subtype="html",
    )

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=10,
        ) as smtp:
            smtp.ehlo()

            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()

            smtp.send_message(message)

    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError(
            "Unable to send password-reset email."
        ) from exc
