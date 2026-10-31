from rest_framework.test import APITestCase
from pages.models import AboutItem, FAQItem


class PagesTests(APITestCase):
    def test_home_is_public(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_about_empty(self):
        res = self.client.get('/about/')
        self.assertEqual(res.data, {'description': ''})

    def test_about_ignores_deleted(self):
        AboutItem.objects.create(description='old', deleted=True)
        AboutItem.objects.create(description='current')
        res = self.client.get('/about/')
        self.assertEqual(res.data['description'], 'current')

    def test_faq_excludes_deleted(self):
        FAQItem.objects.create(question='q1', answer='a1')
        FAQItem.objects.create(question='q2', answer='a2', deleted=True)
        res = self.client.get('/faq/')
        self.assertEqual(res.data['items'], [{'question': 'q1', 'answer': 'a1'}])