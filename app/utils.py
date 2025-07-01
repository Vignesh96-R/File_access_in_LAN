import os
import platform
import socket
import time
from .config import FILE_TYPES

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_base_dir():
    current_path = os.path.abspath(__file__)
    normalized_path = os.path.normpath(current_path)
    path_parts = normalized_path.split(os.sep)
    if platform.system() == 'Windows':
        if 'Desktop' in path_parts:
            desktop_index = path_parts.index('Desktop')
            base_path = os.sep.join(path_parts[:desktop_index + 1])
            return os.path.join(base_path, 'LAN Network file share', 'Project code')
    else:
        if 'Desktop' in path_parts:
            desktop_index = path_parts.index('Desktop')
            base_path = os.sep.join(path_parts[:desktop_index + 1])
            return os.path.join(base_path, 'LANDataCenter')
    return os.path.expanduser('~/Desktop/LAN Network file share/Project code')

def get_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    for file_type, extensions in FILE_TYPES.items():
        if ext in extensions:
            return file_type
    return 'other'

def get_file_icon(file_type):
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

def get_file_info(path, name):
    full_path = os.path.join(path, name)
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
