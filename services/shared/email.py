import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@zetheta.com")

EMAIL_ENABLED = all([SMTP_HOST, SMTP_USER, SMTP_PASS])


def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email via SMTP if configured; otherwise log to console."""
    if EMAIL_ENABLED:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = to
            msg.attach(MIMEText(text_body or html_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, [to], msg.as_string())
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email to {to}: {e}")
            return False
    else:
        print(f"[EMAIL] To: {to}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body: {html_body[:200]}...")
        print("-" * 40)
        return True


def send_welcome_email(to: str, name: str) -> bool:
    subject = "Welcome to Zetheta"
    html = f"""
    <h2>Welcome, {name}!</h2>
    <p>Your Zetheta account has been created successfully.</p>
    <p>You can now log in and access your assessment dashboard.</p>
    <p>— The Zetheta Team</p>
    """
    return send_email(to, subject, html)


def send_password_reset_email(to: str, reset_token: str) -> bool:
    subject = "Reset your Zetheta password"
    reset_url = f"http://localhost:4000/reset-password?token={reset_token}"
    html = f"""
    <h2>Password Reset Request</h2>
    <p>You requested a password reset for your Zetheta account.</p>
    <p><a href="{reset_url}" style="padding:10px 20px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px;">Reset Password</a></p>
    <p>Or copy this link: {reset_url}</p>
    <p>This link expires in 1 hour.</p>
    <p>— The Zetheta Team</p>
    """
    return send_email(to, subject, html)


def send_assignment_invite(to: str, name: str, assessment_title: str) -> bool:
    subject = f"New Assessment: {assessment_title}"
    html = f"""
    <h2>Hi {name},</h2>
    <p>You have been assigned a new assessment: <strong>{assessment_title}</strong>.</p>
    <p>Please log in to your candidate portal to start the assessment.</p>
    <p><a href="http://localhost:4000" style="padding:10px 20px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px;">Go to Portal</a></p>
    <p>— The Zetheta Team</p>
    """
    return send_email(to, subject, html)


def send_result_notification(to: str, name: str, assessment_title: str, percentage: float) -> bool:
    subject = f"Assessment Results: {assessment_title}"
    html = f"""
    <h2>Hi {name},</h2>
    <p>Your assessment <strong>{assessment_title}</strong> has been evaluated.</p>
    <p>Your score: <strong>{percentage:.1f}%</strong></p>
    <p>Log in to view detailed results.</p>
    <p>— The Zetheta Team</p>
    """
    return send_email(to, subject, html)
