import os
import shutil
import sqlite3
import subprocess

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from config import Config


dashboard_bp = Blueprint('dashboard', __name__)


def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_id():
    return session.get('user_id')


@dashboard_bp.route('/dashboard')
def dashboard_home():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    resources = conn.execute('SELECT r.*, c.name AS category_name FROM resources r LEFT JOIN categories c ON c.id = r.category_id ORDER BY r.name').fetchall()
    recent = conn.execute('''
        SELECT r.name, r.icon, MAX(lh.launched_at) AS last_used
        FROM launch_history lh
        JOIN resources r ON r.id = lh.resource_id
        WHERE lh.user_id = ?
        GROUP BY r.id
        ORDER BY last_used DESC
        LIMIT 5
    ''', (get_user_id(),)).fetchall() if get_user_id() else []
    favorites = conn.execute('''
        SELECT r.*
        FROM favorites f
        JOIN resources r ON r.id = f.resource_id
        WHERE f.user_id = ?
        ORDER BY r.name
    ''', (get_user_id(),)).fetchall() if get_user_id() else []
    conn.close()
    return render_template(
        'dashboard.html',
        categories=categories,
        resources=resources,
        recent=recent,
        favorites=favorites,
        username=session.get('username', 'Developer')
    )


@dashboard_bp.route('/favorites')
def favorites_page():
    if not get_user_id():
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    favorites = conn.execute('''
        SELECT r.*, c.name AS category_name
        FROM favorites f
        JOIN resources r ON r.id = f.resource_id
        LEFT JOIN categories c ON c.id = r.category_id
        WHERE f.user_id = ?
        ORDER BY r.name
    ''', (get_user_id(),)).fetchall()
    conn.close()
    return render_template('favorites.html', favorites=favorites)


@dashboard_bp.route('/recent')
def recent_page():
    if not get_user_id():
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    recent = conn.execute('''
        SELECT r.*, MAX(lh.launched_at) AS last_used
        FROM launch_history lh
        JOIN resources r ON r.id = lh.resource_id
        WHERE lh.user_id = ?
        GROUP BY r.id
        ORDER BY last_used DESC
    ''', (get_user_id(),)).fetchall()
    conn.close()
    return render_template('recent.html', recent=recent)


@dashboard_bp.route('/categories')
def categories_page():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    category_map = {}
    for category in categories:
        category_map[category['id']] = category
    resources = conn.execute('SELECT * FROM resources ORDER BY category_id, name').fetchall()
    conn.close()
    return render_template('categories.html', categories=categories, resources=resources, category_map=category_map)


@dashboard_bp.route('/analytics')
def analytics_page():
    conn = get_db_connection()
    resource_usage = conn.execute('''
        SELECT r.name, COUNT(lh.id) AS count
        FROM launch_history lh
        JOIN resources r ON r.id = lh.resource_id
        WHERE lh.user_id = ?
        GROUP BY r.id
        ORDER BY count DESC
        LIMIT 10
    ''', (get_user_id(),)).fetchall() if get_user_id() else []
    category_usage = conn.execute('''
        SELECT c.name, COUNT(lh.id) AS count
        FROM launch_history lh
        JOIN resources r ON r.id = lh.resource_id
        JOIN categories c ON c.id = r.category_id
        WHERE lh.user_id = ?
        GROUP BY c.id
        ORDER BY count DESC
    ''', (get_user_id(),)).fetchall() if get_user_id() else []
    conn.close()
    return render_template('analytics.html', resource_usage=resource_usage, category_usage=category_usage)


@dashboard_bp.route('/settings')
def settings_page():
    return render_template('settings.html')


@dashboard_bp.route('/resource/add', methods=['POST'])
def add_resource():
    if not get_user_id():
        return redirect(url_for('auth.login'))

    name = request.form.get('name', '').strip()
    url = request.form.get('url', '').strip()
    description = request.form.get('description', '').strip()
    category_name = request.form.get('category', '').strip()
    icon = request.form.get('icon', '🔗').strip() or '🔗'
    open_type = request.form.get('open_type', 'website')
    executable_path = request.form.get('executable_path', '').strip()

    if not name or not url:
        flash('Resource name and URL are required.', 'error')
        return redirect(url_for('dashboard.dashboard_home'))

    conn = get_db_connection()
    category = conn.execute('SELECT * FROM categories WHERE name = ?', (category_name,)).fetchone()
    if not category:
        category_id = conn.execute('INSERT INTO categories (name, icon) VALUES (?, ?)', (category_name or 'General', '📁')).lastrowid
    else:
        category_id = category['id']

    conn.execute(
        '''
        INSERT INTO resources (name, url, description, category_id, icon, open_type, executable_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (name, url, description, category_id, icon, open_type, executable_path or None)
    )
    conn.commit()
    conn.close()
    flash('Resource added successfully.', 'success')
    return redirect(url_for('dashboard.dashboard_home'))


@dashboard_bp.route('/resource/<int:resource_id>/favorite', methods=['POST'])
def toggle_favorite(resource_id):
    user_id = get_user_id()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    if not user_id:
        if is_ajax:
            return jsonify({'success': False, 'favorited': False, 'message': 'Login required.'}), 401
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    current = conn.execute('SELECT * FROM favorites WHERE user_id = ? AND resource_id = ?', (user_id, resource_id)).fetchone()
    if current:
        conn.execute('DELETE FROM favorites WHERE id = ?', (current['id'],))
        favorited = False
        message = 'Resource removed from favorites.'
    else:
        conn.execute('INSERT INTO favorites (user_id, resource_id) VALUES (?, ?)', (user_id, resource_id))
        favorited = True
        message = 'Added to favorites.'
    conn.commit()
    conn.close()

    if is_ajax:
        return jsonify({'success': True, 'favorited': favorited, 'message': message})

    flash(message, 'success')
    return redirect(url_for('dashboard.dashboard_home'))


@dashboard_bp.route('/resource/<int:resource_id>/launch', methods=['POST'])
@dashboard_bp.route('/resource/<int:resource_id>/open', methods=['POST'])
def launch_resource(resource_id):
    conn = get_db_connection()
    resource = conn.execute('SELECT * FROM resources WHERE id = ?', (resource_id,)).fetchone()
    if not resource:
        conn.close()
        flash('Resource not found.', 'error')
        return redirect(url_for('dashboard.dashboard_home'))

    user_id = get_user_id()
    if user_id:
        conn.execute('INSERT INTO launch_history (user_id, resource_id) VALUES (?, ?)', (user_id, resource_id))
        conn.commit()
    conn.close()

    if resource['open_type'] == 'local':
        launch_result = launch_local_application(resource)
        if not launch_result['success']:
            flash(launch_result['message'], 'error')
            return redirect(url_for('dashboard.dashboard_home'))
        flash('Application opened successfully.', 'success')
    else:
        flash(f'{resource["name"]} opened successfully.', 'success')

    return redirect(url_for('dashboard.dashboard_home'))


def launch_local_application(resource):
    exec_path = (resource['executable_path'] or '').strip()
    resource_name = (resource['name'] or '').strip().lower()
    app_key = resource_name.replace(' ', '')
    allowed = Config.ALLOWED_APPLICATIONS.get(app_key) or Config.ALLOWED_APPLICATIONS.get(resource_name)

    if not allowed:
        return {'success': False, 'message': 'This application is not allowed for local launch.'}

    target_path = exec_path if exec_path else allowed
    if exec_path and exec_path.lower() != allowed.lower():
        return {'success': False, 'message': 'Executable path is not allowed.'}

    if not os.path.exists(target_path):
        return {'success': False, 'message': 'Executable path is missing or unavailable.'}

    try:
        if os.name == 'nt':
            if hasattr(os, 'startfile'):
                os.startfile(target_path)
            else:
                subprocess.Popen(['cmd', '/c', 'start', '', target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which('xdg-open'):
            subprocess.Popen(['xdg-open', target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which('open'):
            subprocess.Popen(['open', target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return {'success': False, 'message': 'No desktop launcher is available on this system.'}
        return {'success': True, 'message': 'Application opened successfully.'}
    except (OSError, ValueError):
        try:
            if os.name == 'nt':
                subprocess.Popen(['cmd', '/c', 'start', '', target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif shutil.which('xdg-open'):
                subprocess.Popen(['xdg-open', target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif shutil.which('open'):
                subprocess.Popen(['open', target_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                raise
            return {'success': True, 'message': 'Application opened successfully.'}
        except (OSError, ValueError):
            return {'success': False, 'message': 'Unable to launch application. Please check the executable path.'}
