from django.test import TestCase


class CorsTests(TestCase):
    def preflight(self, origin):
        return self.client.options('/api/workspaces/', headers={
            'Origin': origin,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'authorization',
        })

    def test_react_dev_server_is_allowed(self):
        r = self.preflight('http://localhost:5173')
        self.assertEqual(r['Access-Control-Allow-Origin'], 'http://localhost:5173')
        self.assertIn('authorization', r['Access-Control-Allow-Headers'])

    def test_other_origins_are_not(self):
        self.assertNotIn('Access-Control-Allow-Origin', self.preflight('https://evil.example'))
