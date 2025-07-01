import os

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

# You can add more config variables here as needed
