import email
import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings


def normalize_email(email):
    return email.strip().lower()

def _code_key(email):
    return f'otp:code:{email}'

def _attempts_key(email):
    return f'otp:attempts:{email}'

def _cooldown_key(email):
    return f'otp:cooldown:{email}'

def _resend_count_key(email):
    return f'otp:resend_count:{email}'

def can_resend(email):
    return cache.get(_cooldown_key(email) is None)

def resend_limit_reached(email):
    count = cache.get(_resend_count_key(email),0)
    return count >= settings.OTP_MAX_RESEND_LIMIT

def generate_and_send_otp(email):
    code = str(random.randint(10**(settings.OTP_LENGTH-1),10**(settings.OTP_LENGTH-1)))

    cache.set(_code_key(email), code, timeout=settings.OTP_EXPIRY_SECONDS)
    cache.delete(_attempts_key(email))
    cache.set(_code_key(email), True, timeout=settings.OTP_RESEND_COOLDOWN_SECONDS)

    resend_count = cache.get(_resend_count_key(email),0)
    cache.set(_resend_count_key(email),resend_count+1, timeout=3600)

    send_mail(
        subject='کد ورود Smart Portfolio Advisor',
        message= f'کد ورود :{code}\n این کد فقط به مدت 3 دقیقه معتبر است.',
        from_email = None,
        recipient_list = [email]
    )

def verify_otp(email, submitted_code):
    stored_code = cache.get(_code_key(email))

    if stored_code is None:
        return 'expired'

    attempts = cache.get(_attempts_key(email),0)

    if attempts >= settings.OTP_MAX_WRONG_ATTEMPTS:
        cache.delete(_code_key(email))
        return 'max wrong attempts hit'

    if stored_code != submitted_code:
        cache.set(_attempts_key(email), attempts + 1, timeout=settings.OTP_EXPIRY_SECONDS)
        remaining = settings.OTP_MAX_WRONG_ATTEMPS - (attempts + 1)
        if remaining<=0:
            cache.delete(_code_key(email))
            return 'max wrong attempts hit'
        return 'wrong'
    cache.delete(_code_key(email))
    cache.delete(_attempts_key(email))
    return 'valid'


