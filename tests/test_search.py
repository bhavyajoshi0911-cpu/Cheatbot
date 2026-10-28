import sqlite3
import unittest
from unittest.mock import patch

from app import app
from config import Config
from routes import api as api_routes


class SearchEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_single_word_query_matches_space_separated_resource_names(self):
        response = self.client.get('/api/search?q=vscode')
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        names = [item['name'] for item in data]
        self.assertIn('VS Code', names)

    def test_toggle_favorite_returns_json_and_persists_state_for_logged_in_user(self):
        with sqlite3.connect(Config.DATABASE) as conn:
            conn.execute('INSERT OR IGNORE INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)',
                         (999, 'favorite_test_user', 'favorite_test@example.com', 'unused'))
            resource_id = conn.execute('SELECT id FROM resources ORDER BY id LIMIT 1').fetchone()[0]
            conn.execute('DELETE FROM favorites WHERE user_id = ? AND resource_id = ?', (999, resource_id))
            conn.commit()

        with self.client.session_transaction() as session:
            session['user_id'] = 999
            session['username'] = 'favorite_test_user'

        response = self.client.post(
            f'/resource/{resource_id}/favorite',
            headers={'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
            json={}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        self.assertTrue(response.get_json()['success'])
        self.assertTrue(response.get_json()['favorited'])

        with sqlite3.connect(Config.DATABASE) as conn:
            row = conn.execute(
                'SELECT COUNT(*) FROM favorites WHERE user_id = ? AND resource_id = ?',
                (999, resource_id)
            ).fetchone()[0]
            self.assertEqual(row, 1)

    def test_launch_local_application_falls_back_when_startfile_is_unavailable(self):
        from routes.dashboard import launch_local_application

        resource = {
            'name': 'Calculator',
            'executable_path': r'C:\Windows\System32\calc.exe',
            'open_type': 'local'
        }

        with patch('os.startfile', side_effect=OSError('blocked'), create=True), \
             patch('subprocess.Popen') as popen_mock:
            result = launch_local_application(resource)

        self.assertTrue(result['success'])
        popen_mock.assert_called()

    def test_search_matches_typo_and_short_queries_for_common_tools(self):
        response = self.client.get('/api/search?q=cheat%20gpt')
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.get_json()]
        self.assertIn('ChatGPT', names)

        response = self.client.get('/api/search?q=gogle')
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.get_json()]
        self.assertIn('Google', names)

        response = self.client.get('/api/search?q=youtube%20videos')
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.get_json()]
        self.assertIn('YouTube', names)

        response = self.client.get('/api/search?q=canva%20design%20poster')
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.get_json()]
        self.assertIn('Canva', names)

    def test_ai_intent_and_ask_endpoint_handle_open_commands(self):
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['username'] = 'tester'

        response = self.client.post('/api/ask', json={'message': 'Open VS Code'})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['intent'], 'OPEN_APPLICATION')
        self.assertIn('VS Code', payload['answer'])

        response = self.client.post('/api/ask', json={'message': 'what is python'})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['intent'], 'AI_QUESTION')
        self.assertIn('Python', payload['answer'])

        response = self.client.post('/api/ask', json={'message': 'Search what is Python'})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn(payload['intent'], ('WEB_SEARCH', 'AI_QUESTION'))

    def test_java_cheatbot_search_and_fallback_answer_work(self):
        with patch.object(api_routes.Config, 'LLM_API_KEY', None), \
             patch.object(api_routes.Config, 'GEMINI_API_KEY', None), \
             patch.object(api_routes.Config, 'OPENAI_API_KEY', None):
            response = self.client.get('/api/search?q=java%20cheat')
            self.assertEqual(response.status_code, 200)
            names = [item['name'] for item in response.get_json()]
            self.assertTrue(any('Java' in name for name in names))

            response = self.client.post('/api/ask', json={'message': 'what is java'})
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload['success'])
            self.assertEqual(payload['intent'], 'AI_QUESTION')
            self.assertIn('Java', payload['answer'])

    def test_ask_route_uses_question_field_and_error_message_without_api_key(self):
        with patch.object(api_routes.Config, 'LLM_API_KEY', None), \
             patch.object(api_routes.Config, 'GEMINI_API_KEY', None), \
             patch.object(api_routes.Config, 'OPENAI_API_KEY', None):
            response = self.client.post('/ask', json={'question': 'is bikes have legs'})
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertFalse(payload['success'])
            self.assertIn('Gemini API key', payload['answer'])
            self.assertNotIn('topic that becomes clearer', payload['answer'].lower())


if __name__ == '__main__':
    unittest.main()
