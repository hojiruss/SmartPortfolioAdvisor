import re
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase
from accounts.models import UserInformation

User = get_user_model()
EMAIL = 'user@example.com'
LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
REQUEST_URL = '/api/accounts/request-otp/'
VERIFY_URL = '/api/accounts/verify-otp/'


@override_settings(CACHES=LOCMEM)
class OTPFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def request_code(self, email=EMAIL):
        res = self.client.post(REQUEST_URL, {'email': email}, format='json')
        self.assertEqual(res.status_code, 200)
        return re.search(r'\d{6}', mail.outbox[-1].body).group()

    def verify(self, code, email=EMAIL):
        return self.client.post(VERIFY_URL, {'email': email, 'code': code}, format='json')

    @staticmethod
    def wrong_of(code):
        return '000000' if code != '000000' else '111111'

    def test_request_sends_six_digit_code(self):
        code = self.request_code()
        self.assertEqual(len(code), 6)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [EMAIL])

    def test_invalid_email_rejected(self):
        res = self.client.post(REQUEST_URL, {'email': 'nope'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_resend_cooldown(self):
        self.request_code()
        res = self.client.post(REQUEST_URL, {'email': EMAIL}, format='json')
        self.assertEqual(res.status_code, 429)

    @override_settings(OTP_MAX_RESEND_PER_HOUR=1, OTP_RESEND_COOLDOWN_SECONDS=0)
    def test_hourly_resend_limit(self):
        self.request_code()
        res = self.client.post(REQUEST_URL, {'email': EMAIL}, format='json')
        self.assertEqual(res.status_code, 429)

    def test_verify_creates_user_and_tokens(self):
        code = self.request_code()
        res = self.verify(code)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['is_new_user'])
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        user = User.objects.get(email=EMAIL)
        self.assertTrue(UserInformation.objects.filter(user=user).exists())

    def test_second_login_is_not_new_user(self):
        self.verify(self.request_code())
        cache.clear()
        res = self.verify(self.request_code())
        self.assertFalse(res.data['is_new_user'])
        self.assertEqual(User.objects.filter(email=EMAIL).count(), 1)

    def test_code_cannot_be_reused(self):
        code = self.request_code()
        self.assertEqual(self.verify(code).status_code, 200)
        res = self.verify(code)
        self.assertEqual(res.data['state'], 'expired')

    def test_verify_without_request_is_expired(self):
        res = self.verify('123456')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['state'], 'expired')

    def test_wrong_code_three_times_locks_code(self):
        code = self.request_code()
        bad = self.wrong_of(code)
        self.assertEqual(self.verify(bad).data['state'], 'wrong')
        self.assertEqual(self.verify(bad).data['state'], 'wrong')
        self.assertEqual(self.verify(bad).data['state'], 'max_attempts')
        self.assertEqual(self.verify(code).data['state'], 'expired')

    def test_email_is_normalized(self):
        code = self.request_code('  User@Example.COM ')
        res = self.verify(code, EMAIL)
        self.assertEqual(res.status_code, 200)

    def test_logout_blacklists_refresh_token(self):
        tokens = self.verify(self.request_code()).data
        res = self.client.post('/api/accounts/logout/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(res.status_code, 200)
        res = self.client.post('/api/accounts/token-refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_logout_with_garbage_token(self):
        res = self.client.post('/api/accounts/logout/', {'refresh': 'garbage'}, format='json')
        self.assertEqual(res.status_code, 400)