import os
import re
import email
import socket
import time
import mimetypes
from email import policy
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
    stat = os.stat(full_path)
    is_dir = os.path.isdir(full_path)
    return {
        'name': name,
        'path': path,
        'full_path': full_path,
        'size': stat.st_size if not is_dir else 0,
        'created': time.ctime(stat.st_ctime),
        'modified': time.ctime(stat.st_mtime),
        'timestamp': stat.st_mtime,
        'type': 'directory' if is_dir else get_file_type(name)
    }

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
    
    try:
        if file_type == 'mhtml':
            content = extract_html_from_mhtml(full_path)
            content = re.sub(r'<meta[^>]+charset=[^>]+>', '', content, flags=re.IGNORECASE)
            return content, 'text/html'
        
        elif file_type == 'pdf':
            return f'''
                <embed src="/raw/{full_path}" type="application/pdf" width="100%" height="100%">
                <p>Can't display PDF? <a href="/download/{full_path}">Download instead</a></p>
            ''', 'text/html'
        
        elif file_type == 'image':
            return f'<img src="/raw/{full_path}" style="max-width: 100%; max-height: 100%;">', 'text/html'
        
        elif file_type == 'video':
            return f'''
                <video controls style="max-width: 100%; max-height: 100%;">
                    <source src="/raw/{full_path}" type="{mimetypes.guess_type(full_path)[0]}">
                    Your browser does not support the video tag.
                </video>
            ''', 'text/html'
        
        elif file_type == 'audio':
            return f'''
                <audio controls>
                    <source src="/raw/{full_path}" type="{mimetypes.guess_type(full_path)[0]}">
                    Your browser does not support the audio element.
                </audio>
            ''', 'text/html'
        
        elif file_type in ['text', 'code']:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f'<pre style="white-space: pre-wrap;">{content}</pre>', 'text/html'
        
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
                <p><a href="/download/{full_path}">Download this file</a></p>
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

@app.route('/')
@app.route('/browse/')
@app.route('/browse/<path:subpath>')
def file_selector(subpath=''):
    # Get current directory path
    current_path = os.path.join('.', subpath)
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
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                a { display: block; padding: 8px; margin: 2px; 
                    background: #f0f0f0; text-decoration: none; }
                a:hover { background: #e0e0e0; }
                .warning { color: red; margin: 20px 0; }
                .network-info { 
                    background: #eef; padding: 10px; 
                    margin: 10px 0; border-radius: 5px;
                }
                .filter-container {
                    margin: 20px 0;
                    padding: 15px;
                    background: #f5f5f5;
                    border-radius: 5px;
                }
                .filter-options {
                    display: flex;
                    gap: 15px;
                    margin-bottom: 10px;
                    flex-wrap: wrap;
                }
                .filter-group {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }
                .search-box {
                    padding: 8px;
                    width: 300px;
                    border-radius: 4px;
                    border: 1px solid #ddd;
                }
                .file-info {
                    font-size: 0.8em;
                    color: #666;
                    margin-left: 10px;
                }
                .file-size {
                    display: inline-block;
                    width: 80px;
                }
                .file-date {
                    display: inline-block;
                    width: 160px;
                }
                .file-type {
                    display: inline-block;
                    width: 80px;
                }
                .file-icon {
                    margin-right: 5px;
                }
                .type-filter-options {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 10px;
                    flex-wrap: wrap;
                }
                .type-filter-btn {
                    padding: 5px 10px;
                    border-radius: 15px;
                    background: #e0e0e0;
                    border: none;
                    cursor: pointer;
                    white-space: nowrap;
                }
                .type-filter-btn:hover {
                    background: #d0d0d0;
                }
                .type-filter-btn.active {
                    background: #4CAF50;
                    color: white;
                }
                .breadcrumb {
                    margin: 10px 0;
                    padding: 5px;
                    background: #f0f0f0;
                    border-radius: 5px;
                }
                .breadcrumb a {
                    display: inline-block;
                    padding: 2px 5px;
                    background: none;
                    color: #0066cc;
                    text-decoration: underline;
                }
                .breadcrumb span {
                    margin: 0 5px;
                    color: #999;
                }
                
                /* Grid layout styles */
                .grid-container {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                    grid-gap: 15px;
                    margin-top: 15px;
                }
                
                .grid-item {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    overflow: hidden;
                    text-align: center;
                    background: #fafafa;
                    transition: transform 0.2s;
                    position: relative;
                }
                
                .grid-item:hover {
                    transform: scale(1.03);
                    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
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
                    background: #f0f0f0;
                }
                
                .grid-filename {
                    display: block;
                    margin-top: 8px;
                    font-size: 0.85em;
                    word-break: break-word;
                    color: #333;
                }
                
                .grid-info {
                    font-size: 0.75em;
                    color: #666;
                    margin-top: 5px;
                }
                
                /* Delete button styles */
                .delete-btn {
                    position: absolute;
                    top: 5px;
                    right: 5px;
                    background: rgba(255,0,0,0.7);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    cursor: pointer;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10;
                }
                
                .delete-btn:hover {
                    background: rgba(255,0,0,0.9);
                }
            </style>
        </head>
        <body>
            <div class="breadcrumb">
                <a href="/browse/">Home</a>
                {% for crumb in breadcrumbs %}
                    <span>/</span>
                    <a href="/browse/{{ crumb.path }}">{{ crumb.name }}</a>
                {% endfor %}
            </div>
            <p><a href="/upload?path={{ current_path }}">📤 Upload File Here</a></p>
            
            <div class="filter-container">
                <h3>Filter Options</h3>
                <form method="get" action="">
                    <input type="hidden" name="file_type" id="file_type_input" value="{{ file_type_filter }}">
                    
                    <div class="type-filter-options">
                        <button type="button" class="type-filter-btn {% if file_type_filter == 'all' %}active{% endif %}" 
                                onclick="setFileType('all')">All Files</button>
                        <button type="button" class="type-filter-btn {% if file_type_filter == 'directory' %}active{% endif %}" 
                                onclick="setFileType('directory')">📁 Folders</button>
                        {% for type in file_types %}
                            <button type="button" class="type-filter-btn {% if file_type_filter == type %}active{% endif %}" 
                                    onclick="setFileType('{{ type }}')">
                                {{ file_icons[type] }} {{ type|capitalize }}
                            </button>
                        {% endfor %}
                    </div>
                    
                    <div class="filter-options">
                        <div class="filter-group">
                            <label for="search">Search:</label>
                            <input type="text" id="search" name="search" class="search-box" 
                                   value="{{ search_term }}" placeholder="Search by filename">
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
                    <a href="/browse/{{ subpath }}" style="display: inline-block; margin-left: 10px;">Reset</a>
                </form>
            </div>
            
            {% if filtered_items %}
                <div style="margin-bottom: 5px;">
                    <strong>Found {{ filtered_items|length }} items{% if file_type_filter != 'all' %} ({{ file_type_filter }}){% endif %}:</strong>
                </div>
                
                <!-- Grid layout for images -->
                {% if file_type_filter == 'image' %}
                    <div class="grid-container">
                        {% for item in filtered_items %}
                            <div class="grid-item">
                                <button class="delete-btn" 
                                        onclick="deleteImage('{{ item.full_path }}', '{{ item.name }}')"
                                        title="Delete this image">×</button>
                                <a href="/view/{{ item.full_path }}">
                                    <img src="/raw/{{ item.full_path }}" 
                                         alt="{{ item.name }}" 
                                         class="grid-thumbnail"
                                         onerror="this.onerror=null;this.src='data:image/svg+xml;charset=utf-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\" viewBox=\"0 0 24 24\"><rect width=\"24\" height=\"24\" fill=\"%23f0f0f0\"/><text x=\"50%\" y=\"50%\" dominant-baseline=\"middle\" text-anchor=\"middle\" font-family=\"monospace\" font-size=\"10px\" fill=\"%23999\">NO PREVIEW</text></svg>'">
                                    <span class="grid-filename">{{ item.name }}</span>
                                    <span class="grid-info">{{ (item.size/1024)|round(2) }} KB</span>
                                </a>
                            </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <!-- Existing list view for other file types -->
                    {% for item in filtered_items %}
                        <a href="{% if item.type == 'directory' %}/browse/{{ subpath }}/{{ item.name }}{% else %}/view/{{ item.full_path }}{% endif %}">
                            <span class="file-icon">{{ file_icons[item.type] }}</span>
                            {{ item.name }}
                            {% if item.type != 'directory' %}
                            <span class="file-info">
                                <span class="file-type">{{ item.type|upper }}</span>
                                <span class="file-size">{{ (item.size/1024)|round(2) }} KB</span>
                                <span class="file-date">{{ item.modified }}</span>
                            </span>
                            {% endif %}
                        </a>
                    {% endfor %}
                {% endif %}
            {% else %}
                <p class="warning">No items found{% if file_type_filter != 'all' %} of type {{ file_type_filter }}{% endif %}{% if search_term %} matching "{{ search_term }}"{% endif %}</p>
            {% endif %}
            
            <script>
                function setFileType(type) {
                    document.getElementById('file_type_input').value = type;
                    // Update active button styling
                    document.querySelectorAll('.type-filter-btn').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    event.target.classList.add('active');
                }
                
                function deleteImage(fullPath, fileName) {
                    if (confirm(`Are you sure you want to delete "${fileName}"? This cannot be undone.`)) {
                        fetch('/delete/' + encodeURIComponent(fullPath), {
                            method: 'DELETE'
                        })
                        .then(response => {
                            if (response.ok) {
                                // Refresh the page after deletion
                                location.reload();
                            } else {
                                alert('Failed to delete file. Server responded with status: ' + response.status);
                            }
                        })
                        .catch(error => {
                            console.error('Error deleting file:', error);
                            alert('Error deleting file: ' + error.message);
                        });
                    }
                }
            </script>
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
    if not os.path.exists(filename):
        abort(404, "File not found")
    
    if os.path.isdir(filename):
        return file_selector(filename)
    
    # Get navigation info for images
    nav_info = {}
    file_type = get_file_type(os.path.basename(filename))
    
    if file_type == 'image':
        # Get all images in the same directory
        images = get_sibling_images(filename)
        current_name = os.path.basename(filename)
        
        # Find current position and get next/previous
        for i, img in enumerate(images):
            if img['name'] == current_name:
                if i > 0:
                    nav_info['prev'] = images[i-1]['path']
                if i < len(images) - 1:
                    nav_info['next'] = images[i+1]['path']
                break
    
    preview_content, content_type = get_file_preview(filename)
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ filename }}</title>
            <style>
                body { margin: 0; padding: 0; }
                .content-container {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    padding: 20px;
                    box-sizing: border-box;
                    overflow: auto;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background: #111;
                }
                .toolbar {
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    z-index: 100;
                    background: #000000;
                    padding: 5px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    display: flex;
                }
                .toolbar a {
                    display: inline-block;
                    padding: 5px 10px;
                    margin: 0 5px;
                    background: #000000;
                    text-decoration: none;
                    border-radius: 3px;
                    font-size: 14px;
                    color: #FFFFFF;
                }
                .toolbar a:hover {
                    background: #00FF00;
                    color: #000;
                }
                pre {
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
                .image-container {
                    max-width: 100%;
                    max-height: 100%;
                    text-align: center;
                }
                .image-container img {
                    max-width: 100%;
                    max-height: 100%;
                    object-fit: contain;
                }
                .nav-arrow {
                    position: fixed;
                    top: 50%;
                    transform: translateY(-50%);
                    font-size: 40px;
                    color: rgba(255,255,255,0.7);
                    text-decoration: none;
                    background: rgba(0,0,0,0.3);
                    width: 60px;
                    height: 100px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    opacity: 0.5;
                    transition: opacity 0.3s;
                    z-index: 101;
                }
                .nav-arrow:hover {
                    opacity: 1;
                    color: white;
                    background: rgba(0,0,0,0.7);
                }
                .prev-arrow {
                    left: 0;
                    border-radius: 0 5px 5px 0;
                }
                .next-arrow {
                    right: 0;
                    border-radius: 5px 0 0 5px;
                }
                .nav-arrow.hidden {
                    display: none;
                }
            </style>
        </head>
        <body>
            <div class="toolbar">
                <a href="{{ back_link }}">Back</a>
                <a href="/download/{{ filename }}" download>Download</a>
            </div>
            
            <!-- Navigation arrows -->
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
                // Keyboard navigation for images
                document.addEventListener('keydown', function(event) {
                    const prevLink = document.querySelector('.prev-arrow:not(.hidden)');
                    const nextLink = document.querySelector('.next-arrow:not(.hidden)');
                    
                    // Left arrow key
                    if (event.key === 'ArrowLeft' && prevLink) {
                        window.location.href = prevLink.href;
                    }
                    // Right arrow key
                    else if (event.key === 'ArrowRight' && nextLink) {
                        window.location.href = nextLink.href;
                    }
                    // Escape key
                    else if (event.key === 'Escape') {
                        window.location.href = "{{ back_link or '/' }}";
                    }
                });
                
                // Focus the content container for keyboard events
                document.querySelector('.content-container').focus();
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
    if not os.path.exists(filename):
        abort(404, "File not found")
    
    # Security check to prevent directory traversal
    if '../' in filename or not os.path.isfile(filename):
        abort(403, "Access denied")
    
    return send_file(filename)

@app.route('/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file"""
    if not os.path.exists(filename):
        abort(404, "File not found")
    
    if not os.path.isfile(filename):
        abort(400, "Not a file")
    
    try:
        os.remove(filename)
        # Return to the directory of the deleted file
        directory = os.path.dirname(filename)
        return '', 204  # No content response
    except Exception as e:
        abort(500, f"Could not delete file: {str(e)}")

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    upload_path = request.args.get('path', '.')
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return "No file selected", 400
        try:
            save_path = os.path.join(upload_path, file.filename)
            file.save(save_path)
            return redirect(f"/browse/{upload_path.strip('./')}")
        except Exception as e:
            return f"Error: {str(e)}", 500

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
    if not os.path.exists(filename):
        abort(404, "File not found")
    
    return send_file(
        filename,
        as_attachment=True,
        download_name=os.path.basename(filename),
        mimetype='application/octet-stream'
    )

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"\nAccess the viewer at:")
    print(f"Local: http://localhost:8000")
    print(f"Network: http://{local_ip}:8000\n")
    app.run(host=local_ip, port=8000, debug=True)
