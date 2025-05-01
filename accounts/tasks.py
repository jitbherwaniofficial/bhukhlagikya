# accounts/tasks.py
from celery import shared_task
import requests
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

@shared_task
def send_otp_task(phone, otp):
    cache.set(f'otp_{phone}', otp, timeout=300)
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "sender_id": "FSTSMS",
        "message": f"Your OTP is {otp}",
        "language": "english",
        "route": "p",
        "numbers": phone,
    }
    headers = {
        "authorization": settings.FAST2SMS_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code == 200

@shared_task
def send_email_otp_task(email, otp):
    cache.set(f'otp_{email}', otp, timeout=300)
    subject = 'Your OTP for KFC Clone'
    message = f'Your OTP is {otp}. It is valid for 5 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, [email])
    return True