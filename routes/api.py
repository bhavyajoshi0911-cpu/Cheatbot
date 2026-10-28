import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request

from flask import Blueprint, jsonify, request, session

from config import Config

api_bp = Blueprint('api', __name__)


def normalize_search_value(value):
    if value is None:
        return ''
    return ''.join(ch.lower() for ch in value if ch.isalnum())


def matches_search(row, query):
    if not query:
        return True

    normalized_query = normalize_search_value(query)
    if not normalized_query:
        return False

    haystacks = [
        normalize_search_value(row['name']),
        normalize_search_value(row['description'] or ''),
        normalize_search_value(row['category_name'] or ''),
        normalize_search_value(row['url'] or '')
    ]

    query_tokens = [normalize_search_value(part) for part in re.split(r'\s+', query.strip()) if normalize_search_value(part)]
    if not query_tokens:
        return False

    for haystack in haystacks:
        if normalized_query in haystack:
            return True

        if all(token in haystack for token in query_tokens):
            return True

        if any(token in haystack for token in query_tokens):
            return True

    # Helpful fuzzy corrections for common short names and typos.
    alias_map = {
        'cheatgpt': 'chatgpt',
        'chatgpt': 'chatgpt',
        'chatgptai': 'chatgpt',
        'chagpt': 'chatgpt',
        'openai': 'chatgpt',
        'javahelp': 'java',
        'javacode': 'java',
        'javatutorial': 'java',
        'javasheet': 'java',
        'gogle': 'google',
        'googl': 'google',
        'googlesearch': 'google',
        'vscode': 'vscode',
        'vscodeeditor': 'vscode',
        'canvaa': 'canva',
        'canvadesign': 'canva',
        'designstudio': 'canva',
        'youtube': 'youtube',
        'yt': 'youtube',
        'videotutorial': 'youtube',
        'colab': 'jupyter',
        'notionapp': 'notion',
        'githubrepo': 'github',
        'gitlabrepo': 'gitlab',
        'courseraonline': 'coursera',
        'udemycourse': 'udemy',
    }

    for key, value in alias_map.items():
        if normalized_query == key or key in normalized_query:
            for haystack in haystacks:
                if value in haystack:
                    return True

    for token in query_tokens:
        alias = alias_map.get(token)
        if alias:
            for haystack in haystacks:
                if alias in haystack:
                    return True

    return False


def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_intent_message(message):
    return re.sub(r'\s+', ' ', (message or '').strip())


def get_resource_aliases():
    conn = get_db_connection()
    rows = conn.execute('SELECT name, url, open_type FROM resources ORDER BY name').fetchall()
    conn.close()
    aliases = []
    for row in rows:
        aliases.append((row['name'].lower(), row['name']))
        aliases.append((row['name'].lower().replace(' ', ''), row['name']))
    return aliases


def detect_intent(message):
    text = normalize_intent_message(message).lower()
    resource_names = [name.lower() for name, _ in get_resource_aliases()]
    known_sites = ['google', 'youtube', 'github', 'gitlab', 'canva', 'notion', 'gmail', 'slack', 'teams', 'stackoverflow', 'w3schools', 'coursera', 'udemy', 'chatgpt', 'openai', 'vscode', 'vs code', 'java', 'javascript']

    if re.search(r'\b(open|launch|start|run)\b', text):
        for resource_name in resource_names:
            if resource_name in text or resource_name.replace(' ', '') in text:
                return 'OPEN_APPLICATION'
        return 'OPEN_APPLICATION'

    if re.search(r'\b(visit|open|go to|goto)\b', text) and re.search(r'(\.com|\.io|\.dev|\.org|\.net|youtube|google|github|gitlab|canva|notion)', text):
        return 'OPEN_WEBSITE'

    if any(site in text for site in known_sites):
        if re.search(r"\b(what|who|why|how|when|where|which|explain|tell me|define|compare|show me|can you|please|what's|who's)\b", text):
            return 'AI_QUESTION'
        if re.search(r'\b(search|find|lookup|look up)\b', text):
            return 'WEB_SEARCH'
        return 'OPEN_WEBSITE'

    if re.search(r'^(what is|who is|how does|how do|why is|why does|when is|where is|which|explain|tell me about|define|can you explain|can you|please explain|show me|compare)\b', text):
        return 'AI_QUESTION'

    if re.search(r'\b(search|find|lookup|look up)\b', text):
        if 'youtube' in text or 'video' in text or 'tutorial' in text:
            return 'YOUTUBE_SEARCH'
        return 'WEB_SEARCH'

    if 'youtube' in text or 'video' in text:
        return 'YOUTUBE_SEARCH'

    if 'canva' in text or 'design' in text:
        return 'OPEN_WEBSITE'

    if re.search(r"\b(what|who|why|how|when|where|which|explain|tell me|define|compare|show me|can you|please|what's|who's|python|javascript|java|html|css|git|api|docker|sql|ai|ml|react|flask|django|node|sqlalchemy)\b", text):
        return 'AI_QUESTION'

    return 'AI_QUESTION'


def build_search_url(query, kind='web'):
    if kind == 'youtube':
        return 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
    if kind == 'web':
        return 'https://www.google.com/search?q=' + urllib.parse.quote(query)
    return None


def find_best_resource_match(query):
    query_norm = normalize_search_value(query)
    if not query_norm:
        return None
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM resources ORDER BY name').fetchall()
    conn.close()
    for row in rows:
        name = normalize_search_value(row['name'])
        if query_norm in name or name in query_norm:
            return row
    return None


def build_gemini_prompt(question):
    clean_question = (question or '').strip()
    return f"""
You are the AI assistant inside my Cheatbot application.

Answer the user's question directly and accurately.

User question:
{clean_question}

Rules:
- Understand the exact meaning of the user's question.
- Do not generate generic filler text.
- Do not repeat phrases like "this topic becomes clearer..."
- Give a direct answer first.
- Keep simple questions concise.
- Give detailed explanations when needed.
- For coding questions, provide working code.
- If the user's grammar is incorrect, understand the intended meaning and answer it.
- Do not say that every question is a "topic".
- Do not invent information.
""".strip()


def generate_local_fallback_answer(question):
    text = (question or '').strip()
    lowered = text.lower()

    if 'python' in lowered:
        return 'Python is a high-level programming language known for its clean syntax, readability, and flexibility. It is widely used for web development, automation, data analysis, AI, scripting, and backend services.'
    if 'java' in lowered:
        return 'Java is an object-oriented programming language used for backend systems, Android apps, enterprise software, and large-scale applications. It runs on the JVM and is known for portability, strong typing, and a large ecosystem.'
    if 'javascript' in lowered or 'js' in lowered:
        return 'JavaScript is a scripting language used mainly for interactive web pages and modern front-end frameworks. It can also run on the server with Node.js.'
    if 'html' in lowered:
        return 'HTML is the standard markup language for creating the structure of web pages and web applications.'
    if 'css' in lowered:
        return 'CSS is used to style and layout HTML elements, controlling colors, spacing, fonts, responsiveness, and design.'
    if 'git' in lowered:
        return 'Git is a distributed version control system used to track changes in code and collaborate with other developers.'
    if 'api' in lowered:
        return 'An API is a way for software systems to communicate with each other, usually through structured requests and responses.'
    if 'sql' in lowered:
        return 'SQL is a language used to query and manage data in relational databases such as SQLite, MySQL, and PostgreSQL.'

    return 'I could not reach the Gemini service right now, but the app is still running. Please try again in a moment or rephrase your question.'


def ask_llm(question):
    clean_question = (question or '').strip()
    if not clean_question:
        return {'success': False, 'answer': 'Please enter a question before asking the assistant.'}

    api_key = Config.LLM_API_KEY or Config.GEMINI_API_KEY or Config.OPENAI_API_KEY
    if not api_key:
        return {'success': False, 'answer': 'Gemini API key is missing. Please add GEMINI_API_KEY to your .env file and restart the app.'}

    provider = (Config.LLM_PROVIDER or 'gemini').lower()
    if provider != 'gemini':
        return {'success': False, 'answer': 'The configured AI provider is not available. Please set LLM_PROVIDER=gemini in your .env file.'}

    model_name = (Config.LLM_MODEL or 'gemini-2.5-flash').strip()
    if model_name.lower() in {'gemini-3.5-flash', 'gemini-3.5-flash-lite'}:
        model_name = 'gemini-2.5-flash'

    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
    prompt = build_gemini_prompt(clean_question)
    payload = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 512}
    }).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = json.loads(response.read().decode('utf-8'))
            candidates = body.get('candidates') or []
            for candidate in candidates:
                parts = candidate.get('content', {}).get('parts', [])
                texts = [part.get('text', '') for part in parts if isinstance(part, dict)]
                answer = ''.join(texts).strip()
                if answer:
                    return {'success': True, 'answer': answer}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', 'ignore')
        try:
            error_data = json.loads(body)
            error_message = error_data.get('error', {}).get('message', '').lower()
        except Exception:
            error_message = body.lower()

        if 'api key' in error_message or 'invalid' in error_message or 'permission' in error_message:
            return {'success': False, 'answer': 'The Gemini API key is invalid or expired. Please update GEMINI_API_KEY in your .env file.'}
        if 'model' in error_message or 'not found' in error_message or 'unavailable' in error_message or 'service unavailable' in error_message or '503' in error_message:
            fallback_answer = generate_local_fallback_answer(clean_question)
            return {'success': True, 'answer': fallback_answer}
        return {'success': False, 'answer': 'Gemini returned an error. Please try again in a moment.'}
    except urllib.error.URLError:
        return {'success': True, 'answer': generate_local_fallback_answer(clean_question)}
    except (json.JSONDecodeError, ValueError):
        return {'success': True, 'answer': generate_local_fallback_answer(clean_question)}

    return {'success': True, 'answer': generate_local_fallback_answer(clean_question)}


def save_conversation_turn(user_id, message, answer, intent):
    if not user_id:
        return None

    conn = get_db_connection()
    conversation = conn.execute(
        'SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1',
        (user_id,)
    ).fetchone()

    if conversation is None:
        title = (message[:40] + '...') if len(message) > 40 else message
        cursor = conn.execute(
            'INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
            (user_id, title or 'New chat',)
        )
        conversation_id = cursor.lastrowid
    else:
        conversation_id = conversation['id']
        conn.execute(
            'UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (conversation_id,)
        )

    conn.execute(
        'INSERT INTO chat_messages (conversation_id, sender, message, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
        (conversation_id, 'user', message)
    )
    conn.execute(
        'INSERT INTO chat_messages (conversation_id, sender, message, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
        (conversation_id, 'assistant', answer)
    )
    conn.commit()
    conn.close()
    return conversation_id


@api_bp.route('/api/resources')
def api_resources():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT r.*, c.name AS category_name
        FROM resources r
        LEFT JOIN categories c ON c.id = r.category_id
        ORDER BY r.name
    ''').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@api_bp.route('/api/search')
def api_search():
    query = (request.args.get('q', '') or '').strip()
    conn = get_db_connection()

    if not query:
        rows = conn.execute('SELECT r.*, c.name AS category_name FROM resources r LEFT JOIN categories c ON c.id = r.category_id ORDER BY r.name LIMIT 10').fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])

    rows = conn.execute('''
        SELECT r.*, c.name AS category_name
        FROM resources r
        LEFT JOIN categories c ON c.id = r.category_id
        ORDER BY r.name
    ''').fetchall()
    filtered = [row for row in rows if matches_search(row, query)]
    conn.close()
    return jsonify([dict(row) for row in filtered[:12]])


@api_bp.route('/api/favorites')
def api_favorites():
    return jsonify([])


@api_bp.route('/api/recent')
def api_recent():
    return jsonify([])


@api_bp.route('/ask', methods=['POST'])
def ask_route():
    data = request.get_json(silent=True) or {}
    message = (data.get('question') or data.get('message') or '').strip()
    if not message:
        return jsonify({'success': False, 'answer': 'Please enter a question or command.'}), 400

    try:
        intent = detect_intent(message)
        resource_match = find_best_resource_match(message) if intent in {'OPEN_APPLICATION', 'OPEN_WEBSITE'} else None

        if intent == 'OPEN_APPLICATION':
            target = resource_match or {'name': 'Application', 'url': '#'}
            answer = f'Opening {target["name"]} for you.'
            response = {
                'success': True,
                'intent': intent,
                'answer': answer,
                'action': {'type': 'open_application', 'name': target['name']}
            }
            save_conversation_turn(session.get('user_id'), message, answer, intent)
            return jsonify(response)

        if intent == 'OPEN_WEBSITE':
            target = resource_match or {'name': 'Website', 'url': 'https://www.google.com'}
            answer = f'Opening {target["name"]} for you.'
            response = {
                'success': True,
                'intent': intent,
                'answer': answer,
                'action': {'type': 'open_website', 'url': target['url'] or 'https://www.google.com', 'name': target['name']}
            }
            save_conversation_turn(session.get('user_id'), message, answer, intent)
            return jsonify(response)

        if intent == 'WEB_SEARCH':
            query = message
            url = build_search_url(query, 'web')
            answer = f'I found the web result for: {query}. Open the search in your browser.'
            response = {
                'success': True,
                'intent': intent,
                'answer': answer,
                'action': {'type': 'web_search', 'url': url}
            }
            save_conversation_turn(session.get('user_id'), message, answer, intent)
            return jsonify(response)

        if intent == 'YOUTUBE_SEARCH':
            query = re.sub(r'\b(open|search|find|youtube|video|tutorial)\b', '', message, flags=re.IGNORECASE).strip() or message
            url = build_search_url(query, 'youtube')
            answer = f'Opening YouTube results for: {query}.'
            response = {
                'success': True,
                'intent': intent,
                'answer': answer,
                'action': {'type': 'youtube_search', 'url': url}
            }
            save_conversation_turn(session.get('user_id'), message, answer, intent)
            return jsonify(response)

        result = ask_llm(message)
        if not result.get('success'):
            if request.path == '/ask':
                return jsonify({
                    'success': False,
                    'intent': intent,
                    'answer': result.get('answer', 'Unable to get an AI response right now.')
                })

            if 'Gemini API key is missing' in (result.get('answer') or ''):
                answer = generate_local_fallback_answer(message)
                save_conversation_turn(session.get('user_id'), message, answer, intent)
                return jsonify({'success': True, 'intent': intent, 'answer': answer})

            return jsonify({
                'success': False,
                'intent': intent,
                'answer': result.get('answer', 'Unable to get an AI response right now.')
            })

        answer = result.get('answer')
        save_conversation_turn(session.get('user_id'), message, answer, intent)
        return jsonify({'success': True, 'intent': intent, 'answer': answer})
    except Exception:
        return jsonify({'success': False, 'answer': 'Unable to get an AI response right now.'})


@api_bp.route('/api/ask', methods=['POST'])
def api_ask():
    return ask_route()


@api_bp.route('/api/conversations')
def api_conversations():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    conn = get_db_connection()
    rows = conn.execute('''
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT 10
    ''', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@api_bp.route('/api/launch', methods=['POST'])
def api_launch():
    data = request.get_json(silent=True) or {}
    resource_id = data.get('resource_id')
    if not resource_id:
        return jsonify({'success': False, 'message': 'Resource ID is required.'}), 400

    conn = get_db_connection()
    resource = conn.execute('SELECT * FROM resources WHERE id = ?', (resource_id,)).fetchone()
    if not resource:
        conn.close()
        return jsonify({'success': False, 'message': 'Resource not found.'}), 404

    conn.execute('INSERT INTO launch_history (user_id, resource_id) VALUES (?, ?)', (1, resource_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'{resource["name"]} launched.', 'resource': dict(resource)})
