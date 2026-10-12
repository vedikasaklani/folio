from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()
NEW = {'username': 'ada', 'email': 'ada@example.com', 'password': 'correct-horse-9'}


class AccountsTests(APITestCase):
    def test_register_returns_token_that_works(self):
        r = self.client.post('/api/auth/register/', NEW)
        self.assertEqual(r.status_code, 201)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        self.assertEqual(self.client.get('/api/workspaces/').status_code, 200)

    def test_password_is_hashed(self):
        self.client.post('/api/auth/register/', NEW)
        self.assertNotEqual(User.objects.get(username='ada').password, NEW['password'])

    def test_weak_password_is_400(self):
        r = self.client.post('/api/auth/register/', {**NEW, 'password': '123'})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_login(self):
        self.client.post('/api/auth/register/', NEW)
        ok = self.client.post('/api/auth/login/', {'username': 'ada', 'password': NEW['password']})
        self.assertEqual(ok.status_code, 200)
        self.assertIn('token', ok.data)
        bad = self.client.post('/api/auth/login/', {'username': 'ada', 'password': 'nope'})
        self.assertEqual(bad.status_code, 400)

    def test_no_token_is_401(self):
        self.assertEqual(self.client.get('/api/workspaces/').status_code, 401)
        self.assertEqual(self.client.get('/api/pages/').status_code, 401)
