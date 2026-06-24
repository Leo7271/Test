from flask import Blueprint, request, jsonify
import os
import json
import shutil

bp = Blueprint('code_manager', __name__)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CODES_DIR = os.path.join(WORKSPACE_ROOT, 'Test_2_Codes', 'code_management')
METADATA_FILE = os.path.join(CODES_DIR, 'codes.json')

def safe_path(path):
    full = os.path.realpath(path)
    return full.startswith(os.path.realpath(CODES_DIR) + os.sep)

def load_meta():
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'files': {}}

def save_meta(meta):
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

@bp.route('/list', methods=['GET'])
def list_codes():
    # Return a simple structure: masters and slaves
    result = {'masters': [], 'slaves': []}
    for kind in ('masters', 'slaves'):
        folder = os.path.join(CODES_DIR, kind)
        if not os.path.exists(folder):
            continue
        for name in sorted(os.listdir(folder)):
            p = os.path.join(folder, name)
            if os.path.isfile(p):
                result[kind].append({
                    'name': name,
                    'path': os.path.relpath(p, CODES_DIR).replace('\\', '/'),
                })
    return jsonify(result)

@bp.route('/content', methods=['GET'])
def get_content():
    rel = request.args.get('path')
    if not rel:
        return jsonify({'ok': False, 'error': 'path required'}), 400
    target = os.path.join(CODES_DIR, rel)
    if not safe_path(target) or not os.path.exists(target):
        return jsonify({'ok': False, 'error': 'not found or invalid path'}), 404
    try:
        with open(target, 'r', encoding='utf-8') as f:
            return jsonify({'ok': True, 'content': f.read()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/create', methods=['POST'])
def create_file():
    data = request.get_json(force=True)
    kind = data.get('kind')  # 'masters' or 'slaves'
    name = data.get('name')
    content = data.get('content', '')
    meta = data.get('meta', {})
    if kind not in ('masters', 'slaves') or not name:
        return jsonify({'ok': False, 'error': 'invalid parameters'}), 400
    folder = os.path.join(CODES_DIR, kind)
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, name)
    if os.path.exists(target):
        return jsonify({'ok': False, 'error': 'file exists'}), 409
    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    # update metadata
    metadata = load_meta()
    metadata['files'][os.path.relpath(target, CODES_DIR).replace('\\', '/')] = meta
    save_meta(metadata)
    return jsonify({'ok': True})

@bp.route('/edit', methods=['POST'])
def edit_file():
    data = request.get_json(force=True)
    rel = data.get('path')
    content = data.get('content', '')
    if not rel:
        return jsonify({'ok': False, 'error': 'path required'}), 400
    target = os.path.join(CODES_DIR, rel)
    if not safe_path(target) or not os.path.exists(target):
        return jsonify({'ok': False, 'error': 'not found'}), 404
    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'ok': True})

@bp.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json(force=True)
    rel = data.get('path')
    if not rel:
        return jsonify({'ok': False, 'error': 'path required'}), 400
    target = os.path.join(CODES_DIR, rel)
    if not safe_path(target) or not os.path.exists(target):
        return jsonify({'ok': False, 'error': 'not found'}), 404
    try:
        os.remove(target)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    metadata = load_meta()
    metadata['files'].pop(rel.replace('\\', '/'), None)
    save_meta(metadata)
    return jsonify({'ok': True})

@bp.route('/copy', methods=['POST'])
def copy_file():
    data = request.get_json(force=True)
    src = data.get('src')
    dst = data.get('dst')
    if not src or not dst:
        return jsonify({'ok': False, 'error': 'src and dst required'}), 400
    s = os.path.join(CODES_DIR, src)
    d = os.path.join(CODES_DIR, dst)
    if not safe_path(s) or not safe_path(d):
        return jsonify({'ok': False, 'error': 'invalid path'}), 400
    try:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        # copy metadata if exists
        metadata = load_meta()
        files = metadata.get('files', {})
        key_src = src.replace('\\', '/')
        key_dst = dst.replace('\\', '/')
        if key_src in files:
            files[key_dst] = files[key_src].copy()
            save_meta(metadata)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/move', methods=['POST'])
def move_file():
    data = request.get_json(force=True)
    src = data.get('src')
    dst = data.get('dst')
    if not src or not dst:
        return jsonify({'ok': False, 'error': 'src and dst required'}), 400
    s = os.path.join(CODES_DIR, src)
    d = os.path.join(CODES_DIR, dst)
    if not safe_path(s) or not safe_path(d):
        return jsonify({'ok': False, 'error': 'invalid path'}), 400
    try:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.move(s, d)
        metadata = load_meta()
        files = metadata.get('files', {})
        ksrc = src.replace('\\', '/')
        kdst = dst.replace('\\', '/')
        if ksrc in files:
            files[kdst] = files.pop(ksrc)
            save_meta(metadata)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/update_meta', methods=['POST'])
def update_meta():
    data = request.get_json(force=True)
    rel = data.get('path')
    meta = data.get('meta', {})
    if not rel:
        return jsonify({'ok': False, 'error': 'path required'}), 400
    metadata = load_meta()
    metadata['files'][rel.replace('\\', '/')] = meta
    save_meta(metadata)
    return jsonify({'ok': True})


@bp.route('/meta', methods=['GET'])
def get_meta():
    """Return the full metadata store."""
    metadata = load_meta()
    return jsonify(metadata)
