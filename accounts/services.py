import hmac
import secrets
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
    return cache.get(_cooldown_key(email)) is None

def resend_limit_reached(email):
    count = cache.get(_resend_count_key(email),0)
    return count >= settings.OTP_MAX_RESEND_PER_HOUR

def generate_and_send_otp(email):
    code = f'{secrets.randbelow(10 ** settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}'

    cache.set(_code_key(email), code, timeout=settings.OTP_EXPIRY_SECONDS)
    cache.delete(_attempts_key(email))
    cache.set(_cooldown_key(email), True, timeout=settings.OTP_RESEND_COOLDOWN_SECONDS)

    count_key =  _resend_count_key(email)
    if not cache.add(count_key, 1, timeout=3600):
        cache.incr(count_key)

    send_mail(
        subject='کد ورود Smart Portfolio Advisor',
        message=f'کد ورود: {code}\nاین کد فقط به مدت ۳ دقیقه معتبر است.',
        from_email=None,
        recipient_list=[email],
    )

def verify_otp(email, submitted_code):
    stored_code = cache.get(_code_key(email))
    if stored_code is None:
        return 'expired'

    attempts_key = _attempts_key(email)
    cache.add(attempts_key, 0, timeout=settings.OTP_EXPIRY_SECONDS)
    attempts = cache.incr(attempts_key)

    if attempts > settings.OTP_MAX_WRONG_ATTEMPTS:
        cache.delete(_code_key(email))
        return 'max_attempts'

    if not hmac.compare_digest(str(stored_code), str(submitted_code)):
        if attempts >= settings.OTP_MAX_WRONG_ATTEMPTS:
            cache.delete(_code_key(email))
            return 'max_attempts'
        return 'wrong'

    cache.delete(_code_key(email))
    cache.delete(attempts_key)
    return 'valid'