import sys
import os

sys.path.insert(0, 'services')

from shared.email import (
    send_welcome_email,
    send_password_reset_email,
    send_assignment_invite,
    send_result_notification,
    EMAIL_ENABLED,
    SMTP_HOST,
    SMTP_USER,
    SMTP_FROM,
)

RECIPIENT = "vijaybaskaran.vlr@gmail.com"

print("=" * 50)
print("  Zetheta Email Test")
print("=" * 50)
print(f"SMTP Enabled: {EMAIL_ENABLED}")
print(f"SMTP Host:    {SMTP_HOST}")
print(f"SMTP User:    {SMTP_USER}")
print(f"From:         {SMTP_FROM}")
print(f"To:           {RECIPIENT}")
print("=" * 50)
print()

# Test 1: Welcome email
print("[1/4] Sending welcome email...")
ok = send_welcome_email(RECIPIENT, "Test User", "testpassword123")
print(f"      Result: {'SENT' if ok else 'FAILED'}")
print()

# Test 2: Password reset email
print("[2/4] Sending password reset email...")
ok = send_password_reset_email(RECIPIENT, "demo_reset_token_12345")
print(f"      Result: {'SENT' if ok else 'FAILED'}")
print()

# Test 3: Assignment invite email
print("[3/4] Sending assignment invite email...")
ok = send_assignment_invite(RECIPIENT, "Test User", "Full Stack Engineering Assessment")
print(f"      Result: {'SENT' if ok else 'FAILED'}")
print()

# Test 4: Result notification email
print("[4/4] Sending result notification email...")
ok = send_result_notification(RECIPIENT, "Test User", "Full Stack Engineering Assessment", 85.5)
print(f"      Result: {'SENT' if ok else 'FAILED'}")
print()

print("=" * 50)
print("  All 4 test emails dispatched!")
print(f"  Check your inbox: {RECIPIENT}")
print("=" * 50)
