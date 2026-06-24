try:
    from flask import Flask, render_template, request, redirect, url_for, session
except ImportError as e:
    raise ImportError("Flask is not installed. Run: pip install flask") from e

try:
    import git
except ImportError as e:
    raise ImportError("GitPython is not installed. Run: pip install gitpython") from e

import os
import random
import time
import platform
import threading
import subprocess

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = 'change_this_to_a_secure_key'

# Register code management blueprint if available
try:
    import code_manager
    app.register_blueprint(code_manager.bp, url_prefix='/code_manager')
except Exception as e:
    print('Code manager blueprint not loaded:', e)

users = {
    'Linda': '7271',
    'Casimiro': '9552',
}

user_info = {
    'Linda': 'Linda López',
    'Casimiro': 'Raspberry Pi',
}

runtime_state = {
    'simulation_running': False,
    'last_started_by': None,
    'github_updates': 0,
    'last_update_by': None,
}

DEVICE_INFO = {
    'SWITCH': {'label': 'Network Switch', 'ip': 'N/A'},
    'PC_USER2': {'label': 'PC User 2', 'ip': '192.168.0.55'},
    'RASPBERRY_PI': {'label': 'Raspberry Pi', 'ip': '192.168.0.3'},
    'PLC_S7': {'label': 'PLC S7', 'ip': '192.168.0.1'},
    'BANNER': {'label': 'Banner', 'ip': '192.168.0.2'},
    'PC_USER1': {'label': 'PC User 1', 'ip': '192.168.0.10'},
}

runtime_state['connections'] = { key: 'disconnected' for key in DEVICE_INFO }
runtime_state['positions'] = {
    'PC_USER1': {'left': '12%', 'top': '22%'},
    'PC_USER2': {'left': '12%', 'top': '72%'},
    'RASPBERRY_PI': {'left': '38%', 'top': '52%'},
    'PLC_S7': {'left': '78%', 'top': '26%'},
    'BANNER': {'left': '78%', 'top': '72%'},
    'SWITCH': {'left': '50%', 'top': '45%'},
}


def ping_host(address, timeout=1.0):
    system = platform.system().lower()
    if system == 'windows':
        args = ['ping', '-n', '1', '-w', str(int(timeout * 1000)), address]
    else:
        args = ['ping', '-c', '1', '-W', str(int(timeout)), address]

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout + 1)
        return result.returncode == 0
    except Exception:
        return False


def refresh_network_status():
    while True:
        runtime_state['connections']['SWITCH'] = 'loading'
        updated = {}
        for key, info in DEVICE_INFO.items():
            if key == 'SWITCH':
                continue
            ip = info.get('ip')
            if not ip or ip == 'N/A':
                updated[key] = 'disconnected'
                continue
            alive = ping_host(ip, timeout=0.8)
            updated[key] = 'connected' if alive else 'disconnected'

        if any(status == 'connected' for status in updated.values()):
            switch_status = 'connected'
        elif any(status == 'disconnected' for status in updated.values()):
            switch_status = 'disconnected'
        else:
            switch_status = 'loading'

        runtime_state['connections'].update(updated)
        runtime_state['connections']['SWITCH'] = switch_status
        runtime_state['last_check'] = time.strftime('%Y-%m-%d %H:%M:%S')
        time.sleep(1)


def start_network_monitor():
    monitor_thread = threading.Thread(target=refresh_network_status, daemon=True)
    monitor_thread.start()


# Start the network status monitor as soon as the app module is imported.
# Flask 3 removed before_first_request, so we use module startup instead.
start_network_monitor()

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username in users and users[username] == password:
            session['username'] = username
            return render_template(
                'management.html',
                username=username,
                user_description=user_info.get(username, username),
                runtime_state=runtime_state,
                action_message=None,
            )

        error = 'Incorrect username or password.'

    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    return render_template(
        'management.html',
        username=username,
        user_description=user_info.get(username, username),
        runtime_state=runtime_state,
        action_message=None,
    )

@app.route('/start', methods=['POST'])
def start_simulation():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    if username == 'Casimiro':
        runtime_state['simulation_running'] = True
        runtime_state['last_started_by'] = username
        message = 'Simulation started by Raspberry user.'
    else:
        message = 'Only the Raspberry user can start the simulation.'

    return render_template(
        'management.html',
        username=username,
        user_description=user_info.get(username, username),
        runtime_state=runtime_state,
        action_message=message,
    )

@app.route('/update', methods=['POST'])
def update_github():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    runtime_state['github_updates'] += 1
    runtime_state['last_update_by'] = username
    message = 'Code update request sent to GitHub.'

    return render_template(
        'management.html',
        username=username,
        user_description=user_info.get(username, username),
        runtime_state=runtime_state,
        action_message=message,
    )

@app.route('/exit', methods=['POST'])
def exit_app():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    shutdown = request.environ.get('werkzeug.server.shutdown')
    if shutdown:
        shutdown()
        return 'Server is shutting down...'

    return render_template(
        'management.html',
        username=username,
        user_description=user_info.get(username, username),
        runtime_state=runtime_state,
        action_message='Exit requested. Server shutdown not available in this environment.',
    )

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    support_email = 'support@martinrea.com'
    actual_support_email = 'linda.lopez@martinrea.com'

    full_name = ''
    email = ''
    username = ''
    support_message = 'Please validate my username request.'

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        support_message = request.form.get('support_message', '').strip()
        captcha_answer = request.form.get('captcha_answer', '').strip()

        if not full_name or not email or not username or not support_message or not captcha_answer:
            error = 'Please complete all fields, including the captcha.'
        elif '@martinrea.com' not in email.lower():
            error = 'Please use a valid @martinrea.com email address.'
        else:
            correct_answer = session.get('captcha_answer')
            if not correct_answer or str(correct_answer) != captcha_answer:
                error = 'Captcha answer is incorrect. Please try again.'
            else:
                success = (
                    f'Your registration request has been sent to {support_email}. '
                    f'It will be handled by {actual_support_email}.'
                )

    # Generate a simple numeric captcha for display
    left = random.randint(1, 9)
    right = random.randint(1, 9)
    session['captcha_answer'] = left + right
    captcha_question = f'{left} + {right} = ?'

    return render_template(
        'register.html',
        error=error,
        success=success,
        support_email=support_email,
        actual_support_email=actual_support_email,
        captcha_question=captcha_question,
        full_name=full_name,
        email=email,
        username=username,
        support_message=support_message,
    )


@app.route('/architecture')
def architecture():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    connections = runtime_state.get('connections', {})
    positions = runtime_state.get('positions', {})
    return render_template(
        'architecture.html',
        username=username,
        user_description=user_info.get(username, username),
        connections=connections,
        positions=positions,
        device_info=DEVICE_INFO,
        runtime_state=runtime_state,
    )


@app.route('/code_management')
def code_management():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    return render_template(
        'code_management.html',
        username=username,
        user_description=user_info.get(username, username),
        runtime_state=runtime_state,
    )


@app.route('/api/connection', methods=['GET', 'POST'])
def api_connection():
    # GET: return current connection statuses
    if request.method == 'GET':
        return {
            'connections': runtime_state.get('connections', {}),
            'positions': runtime_state.get('positions', {}),
            'device_info': DEVICE_INFO,
            'last_check': runtime_state.get('last_check'),
        }

    # POST: update a connection status
    data = None
    try:
        data = request.get_json(force=True)
    except Exception:
        data = request.form.to_dict()

    device = data.get('device')
    status = data.get('status')
    if not device or not status:
        return { 'ok': False, 'error': 'device and status required' }, 400

    status = status.lower()
    if status not in ('connected', 'disconnected', 'loading'):
        return { 'ok': False, 'error': 'invalid status' }, 400

    runtime_state.setdefault('connections', {})[device] = status
    return { 'ok': True, 'connections': runtime_state['connections'] }


import json
import shlex


def push_to_github(commit_message="Automatic update from PLC interface"):
    """
    GitHub integration to push changes automatically.
    This can be modified later depending on the interface design.
    """
    try:
        repo_path = BASE_DIR
        repo = git.Repo(repo_path)
        repo.git.add(A=True)
        repo.index.commit(commit_message)
        origin = repo.remote(name='origin')
        origin.push()
        return True, "Changes pushed successfully to GitHub"
    except Exception as e:
        return False, str(e)


def is_safe_path(rel_path):
    # Only allow editing files inside the project BASE_DIR
    if not rel_path:
        return False
    abs_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    return abs_path.startswith(BASE_DIR)


def run_model(prompt: str, timeout: int = 30) -> str:
    """Try to invoke a local 'continue' CLI if available, otherwise return a helpful stub suggestion.
    The real CLI can be provided via environment variable `CONTINUE_CMD` (full command as string).
    """
    cmd_env = os.environ.get('CONTINUE_CMD')
    # Try env-specified command first
    if cmd_env:
        try:
            cmd_list = shlex.split(cmd_env)
            proc = subprocess.run(cmd_list, input=prompt, text=True, capture_output=True, timeout=timeout)
            if proc.returncode == 0:
                return proc.stdout.strip() or proc.stderr.strip()
            else:
                return proc.stdout.strip() or proc.stderr.strip() or f"(continue exited {proc.returncode})"
        except Exception as e:
            return f"(failed to run continue command: {e})"

    # Attempt to call 'continue' via cmd (may fail if not installed or blocked by PowerShell keyword)
    try:
        proc = subprocess.run(['cmd', '/c', 'continue', 'chat', '--model', 'gemini-1.5-flash'], input=prompt, text=True, capture_output=True, timeout=timeout)
        if proc.returncode == 0:
            return proc.stdout.strip() or proc.stderr.strip()
    except Exception:
        pass

    # Fallback stub for HTML suggestions
    suggestions = [
        "Add <meta charset=\"utf-8\"> inside <head> if missing.",
        "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> for responsive layout.",
        "Ensure <title> is present and descriptive.",
        "Add lang=\"es\" to <html> if content is Spanish.",
        "Close any unclosed tags and validate nesting (use an HTML validator).",
    ]
    stub = "STUB SUGGESTIONS:\n" + "\n".join([f"- {s}" for s in suggestions]) + "\n\nProposed edit: add meta tags in head and a descriptive title."
    return stub


@app.route('/agent/suggest', methods=['POST'])
def agent_suggest():
    data = None
    try:
        data = request.get_json(force=True)
    except Exception:
        return { 'ok': False, 'error': 'invalid json' }, 400

    path = data.get('path')
    if not path:
        return { 'ok': False, 'error': 'path required' }, 400
    if not is_safe_path(path):
        return { 'ok': False, 'error': 'path not allowed' }, 403

    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not os.path.exists(abs_path):
        return { 'ok': False, 'error': 'file not found' }, 404

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return { 'ok': False, 'error': str(e) }, 500

    prompt = (
        "Eres un asistente de edición de código. Revisa el siguiente archivo HTML y proporciona: 1) una lista breve de problemas y 2) una versión propuesta completa del archivo con las correcciones aplicadas.\n\n"
        + content
    )

    result = run_model(prompt)
    return { 'ok': True, 'suggestions': result }


@app.route('/agent/apply', methods=['POST'])
def agent_apply():
    try:
        data = request.get_json(force=True)
    except Exception:
        return { 'ok': False, 'error': 'invalid json' }, 400

    path = data.get('path')
    new_content = data.get('content')
    if not path or new_content is None:
        return { 'ok': False, 'error': 'path and content required' }, 400
    if not is_safe_path(path):
        return { 'ok': False, 'error': 'path not allowed' }, 403

    abs_path = os.path.abspath(os.path.join(BASE_DIR, path))
    if not os.path.exists(abs_path):
        return { 'ok': False, 'error': 'file not found' }, 404

    # Backup original
    try:
        bak_path = abs_path + '.bak'
        with open(abs_path, 'r', encoding='utf-8') as f:
            orig = f.read()
        with open(bak_path, 'w', encoding='utf-8') as bf:
            bf.write(orig)
        # Write new content
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        return { 'ok': False, 'error': str(e) }, 500

    return { 'ok': True, 'backup': os.path.basename(bak_path) }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    