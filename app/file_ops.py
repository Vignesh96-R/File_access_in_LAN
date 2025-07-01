import os
import re
import email
import mimetypes
from email import policy
from .utils import get_file_type, get_file_info, get_base_dir

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

def get_file_preview(full_path):
    if os.path.isdir(full_path):
        return None, None
    file_type = get_file_type(os.path.basename(full_path))
    base_dir = get_base_dir()
    rel_path = os.path.relpath(full_path, base_dir)
    try:
        if file_type == 'mhtml':
            content = extract_html_from_mhtml(full_path)
            content = re.sub(r'<meta[^>]+charset=[^>]+>', '', content, flags=re.IGNORECASE)
            return content, 'text/html'
        elif file_type == 'pdf':
            return f'<embed src="/raw/{rel_path}" type="application/pdf" width="100%" height="100%">', 'text/html'
        elif file_type == 'image':
            return f'<img src="/raw/{rel_path}" style="max-width: 100%; max-height: 100%;">', 'text/html'
        elif file_type == 'video':
            return f'''<video controls style="max-width: 100%; max-height: 100%;"><source src="/raw/{rel_path}" type="{mimetypes.guess_type(full_path)[0]}">Your browser does not support the video tag.</video>''', 'text/html'
        elif file_type == 'audio':
            return f'''<audio controls><source src="/raw/{rel_path}" type="{mimetypes.guess_type(full_path)[0]}">Your browser does not support the audio element.</audio>''', 'text/html'
        elif file_type in ['text', 'code']:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return f'<pre style="white-space: pre-wrap; background: #fff; color: #111; padding: 16px; border-radius: 6px;">{content}</pre>', 'text/html'
        else:
            file_info = get_file_info(os.path.dirname(full_path), os.path.basename(full_path))
            return f'''<h2>File Preview Not Available</h2><p>No preview available for this file type.</p><ul><li>Name: {file_info['name']}</li><li>Type: {file_info['type']}</li><li>Size: {(file_info['size']/1024):.2f} KB</li><li>Modified: {file_info['modified']}</li></ul><p><a href="/download/{rel_path}">Download this file</a></p>''', 'text/html'
    except Exception as e:
        return f"<h2>Error loading file</h2><pre>{str(e)}</pre>", 'text/html'

def get_sibling_images(current_path):
    directory = os.path.dirname(current_path)
    images = []
    for filename in os.listdir(directory):
        if filename.startswith('.'):
            continue
        full_path = os.path.join(directory, filename)
        if os.path.isfile(full_path) and get_file_type(filename) == 'image':
            images.append({'name': filename, 'path': full_path})
    images.sort(key=lambda x: x['name'])
    return images
