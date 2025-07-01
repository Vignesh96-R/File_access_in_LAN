import os
import re
import email
import socket
import time
import mimetypes
from email import policy
import os
import platform
from flask import Flask, render_template_string, request, abort, send_file, Response, url_for, redirect

app = Flask(__name__)

# File type categories with their extensions
FILE_TYPES = {
    'mhtml': ['.mhtml', '.mht'],
    'pdf': ['.pdf'],
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
    'video': ['.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv'],
    'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
    'text': ['.txt', '.log', '.csv', '.json', '.xml', '.yaml', '.yml'],
    'document': ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.rtf'],
    'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    'code': ['.py', '.js', '.html', '.css', '.php', '.java', '.c', '.cpp', '.h'],
    'other': []  # Catch-all for other file types
}

def get_local_ip():
    """Get the local IP address of the machine"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def extract_html_from_mhtml(mhtml_path):
    try:
        with open(mhtml_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                content = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                return content.decode(charset, errors='replace')
        
        for part in msg.walk():
            if part.get_content_maintype() == 'text':
                content = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                return f"<pre>{content.decode(charset, errors='replace')}</pre>"
        
        return "No HTML content found in MHTML file"
    
    except Exception as e:
        return f"<h2>Error loading file</h2><pre>{str(e)}</pre>"

def get_file_info(path, name):
    """Get file information for filtering"""
    full_path = os.path.join(path, name)
    # Compute relative path from base dir
    base_dir = get_base_dir()
    rel_path = os.path.relpath(full_path, base_dir)
    stat = os.stat(full_path)
    is_dir = os.path.isdir(full_path)
    return {
        'name': name,
        'path': path,
        'full_path': full_path,
        'rel_path': rel_path,
        'size': stat.st_size if not is_dir else 0,
        'created': time.ctime(stat.st_ctime),
        'modified': time.ctime(stat.st_mtime),
        'timestamp': stat.st_mtime,
        'type': 'directory' if is_dir else get_file_type(name)
    }


def get_base_dir():
    # Get the current file's absolute path
    current_path = os.path.abspath(__file__)
    
    # Normalize path for consistent splitting
    normalized_path = os.path.normpath(current_path)
    path_parts = normalized_path.split(os.sep)

    # Platform-specific desktop folder detection
    if platform.system() == 'Windows':
        if 'Desktop' in path_parts:
            desktop_index = path_parts.index('Desktop')
            base_path = os.sep.join(path_parts[:desktop_index + 1])
            return os.path.join(base_path, 'LAN Network file share', 'Project code')
    else:
        # macOS / Linux
        if 'Desktop' in path_parts:
            desktop_index = path_parts.index('Desktop')
            base_path = os.sep.join(path_parts[:desktop_index + 1])
            return os.path.join(base_path, 'LANDataCenter')

    # Fallback if Desktop is not found
    return os.path.expanduser('~/Desktop/LAN Network file share/Project code')



def get_file_type(filename):
    """Determine the file type category"""
    ext = os.path.splitext(filename)[1].lower()
    for file_type, extensions in FILE_TYPES.items():
        if ext in extensions:
            return file_type
    return 'other'

def get_file_icon(file_type):
    """Get icon for file type"""
    icons = {
        'directory': '📁',
        'mhtml': '📄',
        'pdf': '📕',
        'image': '🖼️',
        'video': '🎬',
        'audio': '🔊',
        'text': '📝',
        'document': '📄',
        'archive': '🗄️',
        'code': '💻',
        'other': '📁'
    }
    return icons.get(file_type, '📁')

def get_file_preview(full_path):
    """Generate appropriate preview for the file type"""
    if os.path.isdir(full_path):
        return None, None
    
    file_type = get_file_type(os.path.basename(full_path))
    # Compute rel_path for use in URLs
    base_dir = get_base_dir()
    rel_path = os.path.relpath(full_path, base_dir)
    try:
        if file_type == 'mhtml':
            content = extract_html_from_mhtml(full_path)
            content = re.sub(r'<meta[^>]+charset=[^>]+>', '', content, flags=re.IGNORECASE)
            return content, 'text/html'
        
        elif file_type == 'pdf':
            return f'''
                <embed src="/raw/{rel_path}" type="application/pdf" width="100%" height="100%">
            ''', 'text/html'
        
        elif file_type == 'image':
            return f'<img src="/raw/{rel_path}" style="max-width: 100%; max-height: 100%;">', 'text/html'
        
        elif file_type == 'video':
            return f'''
                <video controls style="max-width: 100%; max-height: 100%;">
                    <source src="/raw/{rel_path}" type="{mimetypes.guess_type(full_path)[0]}">
                    Your browser does not support the video tag.
                </video>
            ''', 'text/html'
        
        elif file_type == 'audio':
            return f'''
                <audio controls>
                    <source src="/raw/{rel_path}" type="{mimetypes.guess_type(full_path)[0]}">
                    Your browser does not support the audio element.
                </audio>
            ''', 'text/html'
        
        elif file_type in ['text', 'code']:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f'<pre style="white-space: pre-wrap; background: #fff; color: #111; padding: 16px; border-radius: 6px;">{content}</pre>', 'text/html'
        
        else:
            # For unsupported types, show file info and download option
            file_info = get_file_info(os.path.dirname(full_path), os.path.basename(full_path))
            return f'''
                <h2>File Preview Not Available</h2>
                <p>No preview available for this file type.</p>
                <ul>
                    <li>Name: {file_info['name']}</li>
                    <li>Type: {file_info['type']}</li>
                    <li>Size: {(file_info['size']/1024):.2f} KB</li>
                    <li>Modified: {file_info['modified']}</li>
                </ul>
                <p><a href="/download/{rel_path}">Download this file</a></p>
            ''', 'text/html'
    
    except Exception as e:
        return f"<h2>Error loading file</h2><pre>{str(e)}</pre>", 'text/html'

def get_sibling_images(current_path):
    """Get all image files in the same directory as the current file"""
    directory = os.path.dirname(current_path)
    images = []
    for filename in os.listdir(directory):
        if filename.startswith('.'):
            continue
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and get_file_type(filename) == 'image':
            images.append({
                'name': filename,
                'path': full_path
            })
    # Sort images alphabetically
    images.sort(key=lambda x: x['name'])
    return images

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Project code'))
print(f"[INFO] BASE_DIR is set to: {BASE_DIR}")
print(get_base_dir())

@app.route('/')
@app.route('/browse/')
@app.route('/browse/<path:subpath>')
def file_selector(subpath=''):
    # Get current directory path
    # current_path = os.path.join('.', subpath)
    current_path = os.path.join(get_base_dir(), subpath)
    if not os.path.exists(current_path):
        abort(404, "Directory not found")
    
    # Get filter parameters from request
    filter_by = request.args.get('filter_by', 'name')
    sort_order = request.args.get('sort', 'asc')
    search_term = request.args.get('search', '').lower()
    file_type_filter = request.args.get('file_type', 'all')
    
    # Get all files and directories with their metadata
    all_items = []
    for name in os.listdir(current_path):
        if name.startswith('.'):
            continue  # Skip hidden files/directories
        all_items.append(get_file_info(current_path, name))
    
    # Apply filters
    filtered_items = all_items
    
    # Apply file type filter
    if file_type_filter != 'all':
        if file_type_filter == 'directory':
            filtered_items = [f for f in filtered_items if f['type'] == 'directory']
        else:
            filtered_items = [f for f in filtered_items if f['type'] == file_type_filter]
    
    # Apply search filter if any
    if search_term:
        filtered_items = [f for f in filtered_items if search_term in f['name'].lower()]
    
    # Apply sorting
    if filter_by == 'name':
        filtered_items.sort(key=lambda x: x['name'], reverse=(sort_order == 'desc'))
    elif filter_by == 'size':
        filtered_items.sort(key=lambda x: x['size'], reverse=(sort_order == 'desc'))
    elif filter_by == 'modified':
        filtered_items.sort(key=lambda x: x['timestamp'], reverse=(sort_order == 'desc'))
    elif filter_by == 'type':
        filtered_items.sort(key=lambda x: x['type'], reverse=(sort_order == 'desc'))
    
    # Prepare breadcrumb navigation
    breadcrumbs = []
    path_parts = subpath.split('/')
    for i in range(len(path_parts)):
        if path_parts[i]:
            breadcrumbs.append({
                'name': path_parts[i],
                'path': '/'.join(path_parts[:i+1])
            })
    
    local_ip = get_local_ip()
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>File Browser - {{ subpath if subpath else 'Home' }}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css?family=Inter:400,600&display=swap" rel="stylesheet">
            <style>
                body {
                    font-family: 'Inter', Arial, sans-serif;
                    margin: 0;
                    background: #f7fafd;
                    color: #222;
                }
                a {
                    color: #2563eb;
                    text-decoration: none;
                    transition: color 0.2s;
                }
                a:hover {
                    color: #1e40af;
                }
                .container {
                    max-width: 1100px;
                    margin: 32px auto;
                    background: #fff;
                    border-radius: 16px;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
                    padding: 32px 24px 24px 24px;
                }
                .breadcrumb {
                    margin-bottom: 18px;
                    font-size: 1.05em;
                    background: #e0e7ef;
                    border-radius: 8px;
                    padding: 8px 16px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                }
                .breadcrumb a {
                    color: #2563eb;
                    font-weight: 600;
                    background: none;
                    padding: 0;
                }
                .breadcrumb span {
                    color: #94a3b8;
                }
                .upload-btn {
                    display: inline-block;
                    margin-bottom: 18px;
                    background: #2563eb;
                    color: #fff;
                    padding: 8px 18px;
                    border-radius: 8px;
                    font-weight: 600;
                    box-shadow: 0 2px 8px rgba(37,99,235,0.07);
                    transition: background 0.2s;
                    border: none;
                    cursor: pointer;
                    position: absolute;
                    right: 0;
                }
                .upload-btn:hover {
                    background: #1e40af;
                }
                #upload-status {
                    margin-left: 16px;
                    font-weight: 500;
                    color: #2563eb;
                }
                .filter-container {
                    margin: 18px 0 24px 0;
                    padding: 18px 18px 10px 18px;
                    background: #f1f5f9;
                    border-radius: 10px;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.03);
                }
                .filter-container h3 {
                    margin-top: 0;
                    font-size: 1.1em;
                    color: #2563eb;
                }
                .filter-options {
                    display: flex;
                    gap: 18px;
                    margin-bottom: 10px;
                    flex-wrap: wrap;
                }
                .filter-group {
                    display: flex;
                    align-items: center;
                    gap: 7px;
                }
                .search-box {
                    padding: 8px 12px;
                    width: 260px;
                    border-radius: 6px;
                    border: 1px solid #cbd5e1;
                    background: #fff;
                    font-size: 1em;
                }
                select {
                    padding: 7px 10px;
                    border-radius: 6px;
                    border: 1px solid #cbd5e1;
                    background: #fff;
                    font-size: 1em;
                }
                button[type="submit"], .type-filter-btn, .delete-btn-list {
                    font-family: inherit;
                    font-size: 1em;
                    font-weight: 600;
                    border: none;
                    border-radius: 8px;
                    padding: 7px 16px;
                    background: #2563eb;
                    color: #fff;
                    cursor: pointer;
                    margin-right: 6px;
                    transition: background 0.2s, box-shadow 0.2s;
                    box-shadow: 0 1px 4px rgba(37,99,235,0.07);
                }
                button[type="submit"]:hover, .type-filter-btn:hover, .delete-btn-list:hover {
                    background: #1e40af;
                }
                .type-filter-options {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 10px;
                    flex-wrap: wrap;
                }
                .type-filter-btn {
                    background: #e0e7ef;
                    color: #2563eb;
                    border: none;
                    border-radius: 16px;
                    padding: 6px 18px;
                    font-weight: 600;
                    transition: background 0.2s, color 0.2s;
                    box-shadow: none;
                }
                .type-filter-btn.active, .type-filter-btn:active {
                    background: #2563eb;
                    color: #fff;
                }
                .file-list {
                    margin-top: 18px;
                }
                .file-row {
                    display: flex;
                    align-items: center;
                    padding: 12px 0;
                    border-bottom: 1px solid #e5e7eb;
                    transition: background 0.15s;
                }
                .file-row:hover {
                    background: #f1f5f9;
                }
                .file-icon {
                    margin-right: 12px;
                    font-size: 1.3em;
                }
                .file-info {
                    font-size: 0.93em;
                    color: #64748b;
                    margin-left: 12px;
                }
                .file-size, .file-date, .file-type {
                    display: inline-block;
                    min-width: 80px;
                }
                .file-name {
                    font-weight: 500;
                    color: #222;
                }
                .delete-btn-list {
                    margin-left: 16px;
                    background: #ef4444;
                    color: #fff;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-size: 1em;
                    font-weight: 600;
                    transition: background 0.2s;
                }
                .delete-btn-list:hover {
                    background: #b91c1c;
                }
                /* Grid layout for images */
                .grid-container {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                    grid-gap: 18px;
                    margin-top: 18px;
                }
                .grid-item {
                    border: 1px solid #e5e7eb;
                    border-radius: 10px;
                    overflow: hidden;
                    text-align: center;
                    background: #f8fafc;
                    transition: transform 0.18s, box-shadow 0.18s;
                    position: relative;
                    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
                }
                .grid-item:hover {
                    transform: scale(1.04);
                    box-shadow: 0 4px 16px rgba(37,99,235,0.10);
                }
                .grid-item a {
                    display: block;
                    padding: 10px;
                    background: none !important;
                    margin: 0 !important;
                    text-decoration: none !important;
                }
                .grid-thumbnail {
                    width: 100%;
                    height: 120px;
                    object-fit: cover;
                    background: #e0e7ef;
                    border-bottom: 1px solid #e5e7eb;
                }
                .grid-filename {
                    display: block;
                    margin-top: 8px;
                    font-size: 1em;
                    word-break: break-word;
                    color: #222;
                    font-weight: 500;
                }
                .grid-info {
                    font-size: 0.93em;
                    color: #64748b;
                    margin-top: 5px;
                }
                .delete-btn {
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    background: #ef4444;
                    color: #fff;
                    border: none;
                    border-radius: 50%;
                    width: 28px;
                    height: 28px;
                    cursor: pointer;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10;
                    font-size: 1.1em;
                    box-shadow: 0 1px 4px rgba(239,68,68,0.10);
                    transition: background 0.2s;
                }
                .delete-btn:hover {
                    background: #b91c1c;
                }
                .warning {
                    color: #ef4444;
                    margin: 24px 0;
                    font-weight: 600;
                    background: #fef2f2;
                    border-radius: 8px;
                    padding: 12px 18px;
                }
                @media (max-width: 700px) {
                    .container { padding: 10px 2vw; }
                    .filter-container { padding: 10px 4vw; }
                    .grid-container { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
                }
                .breadcrumb-bar {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 18px;
                    position: relative;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="breadcrumb-bar" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px;">
                    <div class="breadcrumb" style="margin-bottom: 0;">
                        <a href="/browse/">Home</a>
                        {% for crumb in breadcrumbs %}
                            <span>/</span>
                            <a href="/browse/{{ crumb.path }}">{{ crumb.name }}</a>
                        {% endfor %}
                    </div>
                    <!-- Upload Button and Hidden File Input -->
                    <button class="upload-btn" onclick="document.getElementById('fileInput').click()">📤 Upload Here</button>
                    <input type="file" id="fileInput" style="display:none" onchange="uploadFile(event)">
                    <span id="upload-status"></span>
                </div>
                <div class="filter-container">
                    <h3>Filter Options</h3>
                    <form method="get" action="">
                        <input type="hidden" name="file_type" id="file_type_input" value="{{ file_type_filter }}">
                        <div class="type-filter-options">
                            <button type="button" class="type-filter-btn {% if file_type_filter == 'all' %}active{% endif %}" onclick="setFileType('all')">All Files</button>
                            <button type="button" class="type-filter-btn {% if file_type_filter == 'directory' %}active{% endif %}" onclick="setFileType('directory')">📁 Folders</button>
                            {% for type in file_types %}
                                <button type="button" class="type-filter-btn {% if file_type_filter == type %}active{% endif %}" onclick="setFileType('{{ type }}')">
                                    {{ file_icons[type] }} {{ type|capitalize }}
                                </button>
                            {% endfor %}
                        </div>
                        <div class="filter-options">
                            <div class="filter-group">
                                <label for="search">Search:</label>
                                <input type="text" id="search" name="search" class="search-box" value="{{ search_term }}" placeholder="Search by filename">
                            </div>
                            <div class="filter-group">
                                <label for="filter_by">Sort by:</label>
                                <select id="filter_by" name="filter_by">
                                    <option value="name" {% if filter_by == 'name' %}selected{% endif %}>Name</option>
                                    <option value="size" {% if filter_by == 'size' %}selected{% endif %}>Size</option>
                                    <option value="modified" {% if filter_by == 'modified' %}selected{% endif %}>Modified Date</option>
                                    <option value="type" {% if filter_by == 'type' %}selected{% endif %}>File Type</option>
                                </select>
                                <select name="sort">
                                    <option value="asc" {% if sort_order == 'asc' %}selected{% endif %}>Ascending</option>
                                    <option value="desc" {% if sort_order == 'desc' %}selected{% endif %}>Descending</option>
                                </select>
                            </div>
                        </div>
                        <button type="submit">Apply Filters</button>
                        <a href="/browse/{{ subpath }}" style="display: inline-block; margin-left: 10px; color: #ef4444; font-weight: 600;">Reset</a>
                    </form>
                </div>
                {% if filtered_items %}
                    <div style="margin-bottom: 8px; font-weight: 600; color: #2563eb;">
                        Found {{ filtered_items|length }} items{% if file_type_filter != 'all' %} ({{ file_type_filter }}){% endif %}:
                    </div>
                    {% if file_type_filter == 'image' %}
                        <div class="grid-container">
                            {% for item in filtered_items %}
                                <div class="grid-item">
                                    <button class="delete-btn" onclick="deleteFileFromList(event, '{{ item.rel_path }}', '{{ item.name }}')" title="Delete this image">🗑️</button>
                                    <a href="/view/{{ item.rel_path }}" onclick="storePrevPath(event)">
                                        <img src="/raw/{{ item.rel_path }}" alt="{{ item.name }}" class="grid-thumbnail" onerror="this.onerror=null;this.src='data:image/svg+xml;charset=utf-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\" viewBox=\"0 0 24 24\"><rect width=\"24\" height=\"24\" fill=\"%23f0f0f0\"/><text x=\"50%\" y=\"50%\" dominant-baseline=\"middle\" text-anchor=\"middle\" font-family=\"monospace\" font-size=\"10px\" fill=\"%23999\">NO PREVIEW</text></svg>'">
                                        <span class="grid-filename">{{ item.name }}</span>
                                        <span class="grid-info">{{ (item.size/1024)|round(2) }} KB</span>
                                    </a>
                                </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="file-list">
                        {% for item in filtered_items %}
                            <div class="file-row">
                                <a href="{% if item.type == 'directory' %}/browse/{{ subpath }}/{{ item.name }}{% else %}/view/{{ item.rel_path }}{% endif %}" {% if item.type != 'directory' %}onclick="storePrevPath(event)"{% endif %} style="flex: 1 1 auto;">
                                    <span class="file-icon">{{ file_icons[item.type] }}</span>
                                    <span class="file-name">{{ item.name }}</span>
                                    {% if item.type != 'directory' %}
                                    <span class="file-info">
                                        <span class="file-type">{{ item.type|upper }}</span>
                                        <span class="file-size">{{ (item.size/1024)|round(2) }} KB</span>
                                        <span class="file-date">{{ item.modified }}</span>
                                    </span>
                                    {% endif %}
                                </a>
                                {% if item.type != 'directory' %}
                                <button class="delete-btn-list" onclick="deleteFileFromList(event, '{{ item.rel_path }}', '{{ item.name }}')" title="Delete this file">🗑️</button>
                                {% endif %}
                            </div>
                        {% endfor %}
                        </div>
                    {% endif %}
                {% else %}
                    <p class="warning">No items found{% if file_type_filter != 'all' %} of type {{ file_type_filter }}{% endif %}{% if search_term %} matching "{{ search_term }}"{% endif %}</p>
                {% endif %}
                <script>
                    function setFileType(type) {
                        document.getElementById('file_type_input').value = type;
                        document.querySelectorAll('.type-filter-btn').forEach(btn => {
                            btn.classList.remove('active');
                        });
                        event.target.classList.add('active');
                    }
                    function deleteFileFromList(event, relPath, fileName) {
                        event.preventDefault();
                        if (confirm(`Are you sure you want to delete "${fileName}"? This cannot be undone.`)) {
                            fetch('/delete/' + encodeURIComponent(relPath), { method: 'DELETE' })
                            .then(response => {
                                if (response.ok) { location.reload(); }
                                else { alert('Failed to delete file. Server responded with status: ' + response.status); }
                            })
                            .catch(error => { alert('Error deleting file: ' + error.message); });
                        }
                    }
                    function storePrevPath(event) {
                        sessionStorage.setItem('prevPath', window.location.pathname + window.location.search);
                    }
                    function handleBack(event) {
                        if (event) event.preventDefault();
                        const prevPath = sessionStorage.getItem('prevPath');
                        if (prevPath) {
                            sessionStorage.removeItem('prevPath');
                            window.location.href = prevPath;
                        } else {
                            window.location.href = "/browse/";
                        }
                    }
                    function deleteCurrentFile(event, relPath) {
                        event.preventDefault();
                        if (!confirm('Are you sure you want to delete this file? This cannot be undone.')) return;
                        fetch('/delete/' + encodeURIComponent(relPath), { method: 'DELETE' })
                        .then(response => {
                            if (response.ok) { handleBack(); }
                            else { alert('Failed to delete file. Server responded with status: ' + response.status); }
                        })
                        .catch(error => { alert('Error deleting file: ' + error.message); });
                    }
                    function uploadFile(event) {
                        const file = event.target.files[0];
                        if (!file) return;
                        const status = document.getElementById('upload-status');
                        status.textContent = 'Uploading...';
                        const formData = new FormData();
                        formData.append('file', file);
                        // Send AJAX POST to /upload with ?path=current_path
                        fetch('/upload?path={{ subpath }}', {
                            method: 'POST',
                            body: formData
                        })
                        .then(async response => {
                            if (response.ok) {
                                status.textContent = 'Upload successful!';
                                setTimeout(() => { status.textContent = ''; location.reload(); }, 800);
                            } else {
                                let msg = 'Upload failed.';
                                try { const data = await response.json(); msg = data.error || msg; } catch {}
                                status.textContent = msg;
                                setTimeout(() => { status.textContent = ''; }, 2000);
                            }
                        })
                        .catch(() => {
                            status.textContent = 'Upload failed.';
                            setTimeout(() => { status.textContent = ''; }, 2000);
                        });
                    }
                </script>
            </div>
        </body>
        </html>
    ''', 
    filtered_items=filtered_items, 
    ip=local_ip, 
    filter_by=filter_by, 
    sort_order=sort_order, 
    search_term=search_term,
    file_type_filter=file_type_filter,
    file_types=FILE_TYPES,
    file_icons={k: get_file_icon(k) for k in {**FILE_TYPES, 'directory': '📁'}},
    subpath=subpath,
    breadcrumbs=breadcrumbs,
    current_path=current_path
    )

@app.route('/view/<path:filename>')
def view_file(filename):
    abs_path = os.path.join(get_base_dir(), filename)
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    
    if os.path.isdir(abs_path):
        return file_selector(filename)
    
    # Get navigation info for images
    nav_info = {}
    file_type = get_file_type(os.path.basename(filename))
    
    if file_type == 'image':
        # Get all images in the same directory
        images = get_sibling_images(abs_path)
        current_name = os.path.basename(abs_path)
        
        # Find current position and get next/previous
        for i, img in enumerate(images):
            if img['name'] == current_name:
                if i > 0:
                    # Convert to rel_path for navigation
                    nav_info['prev'] = os.path.relpath(images[i-1]['path'], get_base_dir())
                if i < len(images) - 1:
                    nav_info['next'] = os.path.relpath(images[i+1]['path'], get_base_dir())
                break
    
    preview_content, content_type = get_file_preview(abs_path)
    rel_path = filename  # filename is already relative in the route
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ filename }}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css?family=Inter:400,600&display=swap" rel="stylesheet">
            <style>
                body { margin: 0; padding: 0; background: #111; font-family: 'Inter', Arial, sans-serif; }
                .content-container {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    padding: 0;
                    box-sizing: border-box;
                    overflow: auto;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background: #111;
                }
                .toolbar {
                    position: fixed;
                    top: 18px;
                    right: 18px;
                    z-index: 100;
                    background: #18181b;
                    padding: 7px 14px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.13);
                    display: flex;
                    gap: 10px;
                }
                .toolbar a, .toolbar button {
                    display: inline-block;
                    padding: 7px 16px;
                    margin: 0 2px;
                    background: #2563eb;
                    text-decoration: none;
                    border-radius: 6px;
                    font-size: 1em;
                    color: #fff;
                    font-weight: 600;
                    border: none;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .toolbar a:hover, .toolbar button:hover {
                    background: #1e40af;
                    color: #fff;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    background: #18181b;
                    color: #f1f5f9;
                    padding: 24px;
                    border-radius: 12px;
                    font-size: 1.1em;
                    max-width: 90vw;
                    max-height: 80vh;
                    overflow: auto;
                }
                .image-container {
                    max-width: 90vw;
                    max-height: 80vh;
                    text-align: center;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .image-container img {
                    max-width: 100%;
                    max-height: 80vh;
                    object-fit: contain;
                    border-radius: 12px;
                    box-shadow: 0 2px 16px rgba(0,0,0,0.18);
                }
                .nav-arrow {
                    position: fixed;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 48px;
                    color: #fff;
                    text-decoration: none;
                    background: rgba(37,99,235,0.7);
                    width: 60px;
                    height: 100px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    opacity: 0.7;
                    transition: opacity 0.3s, background 0.2s;
                    z-index: 101;
                    border-radius: 0 12px 12px 0;
                }
                .nav-arrow.next-arrow {
                    right: 0;
                    left: auto;
                    border-radius: 12px 0 0 12px;
                }
                .nav-arrow.prev-arrow {
                    left: 0;
                    right: auto;
                }
                .nav-arrow:hover {
                    opacity: 1;
                    background: #2563eb;
                }
                .nav-arrow.hidden {
                    display: none;
                }
                .close-btn {
                    position: fixed;
                    top: 18px;
                    left: 18px;
                    z-index: 9999;
                    background: #18181b;
                    color: #fff;
                    border: none;
                    border-radius: 50%;
                    width: 44px;
                    height: 44px;
                    font-size: 1.3em;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s;
                    pointer-events: auto;
                    font-weight: 600;
                }
                .close-btn:hover {
                    background: #ef4444;
                    color: #fff;
                }
                .delete-float-btn {
                    position: fixed;
                    top: 18px;
                    right: 80px;
                    z-index: 9999;
                    background: #ef4444;
                    color: #fff;
                    border: none;
                    border-radius: 50%;
                    width: 44px;
                    height: 44px;
                    font-size: 1.3em;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s;
                    pointer-events: auto;
                    font-weight: 600;
                }
                .delete-float-btn:hover {
                    background: #b91c1c;
                }
                .delete-btn-fullview {
                    margin-left: 10px;
                    background: #ef4444;
                    color: #fff;
                    border: none;
                    border-radius: 6px;
                    padding: 7px 18px;
                    font-size: 1em;
                    font-weight: 600;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .delete-btn-fullview:hover {
                    background: #b91c1c;
                }
                @media (max-width: 700px) {
                    .toolbar { top: 8px; right: 8px; padding: 4px 6px; }
                    .close-btn, .delete-float-btn { top: 8px; left: 8px; right: 8px; width: 36px; height: 36px; font-size: 1em; }
                    .content-container { padding: 0; }
                    pre { padding: 10px; font-size: 1em; }
                }
            </style>
        </head>
        <body>
            {% if file_type == 'image' %}
            <button class="close-btn" onclick="handleBack(event)" title="Close (Esc)">✕</button>
            {% endif %}
            <div class="toolbar">
                <a href="#" onclick="handleBack(event)">Back</a>
                <a href="/download/{{ filename }}" download>Download</a>
              
            </div>
            {% if nav_info and nav_info.prev %}
                <a href="/view/{{ nav_info.prev }}" class="nav-arrow prev-arrow">❮</a>
            {% else %}
                <a class="nav-arrow prev-arrow hidden">❮</a>
            {% endif %}
            {% if nav_info and nav_info.next %}
                <a href="/view/{{ nav_info.next }}" class="nav-arrow next-arrow">❯</a>
            {% else %}
                <a class="nav-arrow next-arrow hidden">❯</a>
            {% endif %}
            <div class="content-container">
                {% if file_type == 'image' %}
                    <div class="image-container">
                        {{ content|safe }}
                    </div>
                {% else %}
                    {{ content|safe }}
                {% endif %}
            </div>
            <script>
                document.addEventListener('keydown', function(event) {
                    const prevLink = document.querySelector('.prev-arrow:not(.hidden)');
                    const nextLink = document.querySelector('.next-arrow:not(.hidden)');
                    if (event.key === 'ArrowLeft' && prevLink) {
                        window.location.href = prevLink.href;
                    } else if (event.key === 'ArrowRight' && nextLink) {
                        window.location.href = nextLink.href;
                    } else if (event.key === 'Escape') {
                        handleBack();
                    }
                });
                function handleBack(event) {
                    if (event) event.preventDefault();
                    const prevPath = sessionStorage.getItem('prevPath');
                    if (prevPath) {
                        sessionStorage.removeItem('prevPath');
                        window.location.href = prevPath;
                    } else {
                        window.location.href = "/browse/";
                    }
                }
            </script>
        </body>
        </html>
    ''', 
    filename=filename, 
    content=preview_content, 
    back_link=request.referrer or '/',
    nav_info=nav_info if file_type == 'image' else None,
    file_type=file_type
    )

@app.route('/raw/<path:filename>')
def raw_file(filename):
    """Serve raw file for embedding in preview"""
    abs_path = os.path.join(get_base_dir(), filename)
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    
    # Security check to prevent directory traversal
    if '../' in filename or not os.path.isfile(abs_path):
        abort(403, "Access denied")
    
    return send_file(abs_path)

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file"""
    abs_path = os.path.join(get_base_dir(), filename)
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    
    if not os.path.isfile(abs_path):
        abort(400, "Not a file")
    
    try:
        os.remove(abs_path)
        # Return to the directory of the deleted file
        directory = os.path.dirname(abs_path)
        return '', 204  # No content response
    except Exception as e:
        abort(500, f"Could not delete file: {str(e)}")

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    upload_path = request.args.get('path', '.')
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            # If AJAX, return JSON error
            if request.accept_mimetypes['application/json']:
                return {"error": "No file selected"}, 400
            return "No file selected", 400
        try:
            # Save to the correct subdirectory
            save_dir = os.path.join(get_base_dir(), upload_path.strip('/'))
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, file.filename)
            file.save(save_path)
            # If AJAX, return JSON success
            if request.accept_mimetypes['application/json'] or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {"success": True}, 200
            return redirect(f"/upload?path=/{upload_path.strip('./')}")
        except Exception as e:
            if request.accept_mimetypes['application/json']:
                return {"error": str(e)}, 500
            return f"Error: {str(e)}", 500
    # Only show the upload page for direct GET requests
    return render_template_string('''
        <!DOCTYPE html>
        <html><head><title>Upload File</title>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            form { margin-top: 20px; }
        </style></head><body>
        <h2>Upload File</h2>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Upload</button>
        </form>
        <p><a href="/browse/{{ upload_path.strip('./') }}">← Back</a></p>
        </body></html>
    ''', upload_path=upload_path)


@app.route('/download/<path:filename>')
def download_file(filename):
    abs_path = os.path.join(get_base_dir(), filename)
    if not os.path.exists(abs_path):
        abort(404, "File not found")
    
    return send_file(
        abs_path,
        as_attachment=True,
        download_name=os.path.basename(abs_path),
        mimetype='application/octet-stream'
    )

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"\nAccess the viewer at:")
    print(f"Local: http://localhost:8000")
    print(f"Network: http://{local_ip}:8000\n")
    app.run(host=local_ip, port=8000, debug=True)