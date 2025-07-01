from flask import render_template, request, abort, send_file, redirect
import os
from .utils import get_local_ip, get_base_dir, get_file_info, get_file_icon, get_file_type
from .file_ops import get_file_preview, get_sibling_images
from .config import FILE_TYPES

def init_app(app):
    @app.route('/')
    @app.route('/browse/')
    @app.route('/browse/<path:subpath>')
    def file_selector(subpath=''):
        current_path = os.path.join(get_base_dir(), subpath)
        if not os.path.exists(current_path):
            abort(404, "Directory not found")
        filter_by = request.args.get('filter_by', 'name')
        sort_order = request.args.get('sort', 'asc')
        search_term = request.args.get('search', '').lower()
        file_type_filter = request.args.get('file_type', 'all')
        all_items = []
        for name in os.listdir(current_path):
            if name.startswith('.'):
                continue
            all_items.append(get_file_info(current_path, name))
        filtered_items = all_items
        if file_type_filter != 'all':
            if file_type_filter == 'directory':
                filtered_items = [f for f in filtered_items if f['type'] == 'directory']
            else:
                filtered_items = [f for f in filtered_items if f['type'] == file_type_filter]
        if search_term:
            filtered_items = [f for f in filtered_items if search_term in f['name'].lower()]
        if filter_by == 'name':
            filtered_items.sort(key=lambda x: x['name'], reverse=(sort_order == 'desc'))
        elif filter_by == 'size':
            filtered_items.sort(key=lambda x: x['size'], reverse=(sort_order == 'desc'))
        elif filter_by == 'modified':
            filtered_items.sort(key=lambda x: x['timestamp'], reverse=(sort_order == 'desc'))
        elif filter_by == 'type':
            filtered_items.sort(key=lambda x: x['type'], reverse=(sort_order == 'desc'))
        breadcrumbs = []
        path_parts = subpath.split('/')
        for i in range(len(path_parts)):
            if path_parts[i]:
                breadcrumbs.append({'name': path_parts[i], 'path': '/'.join(path_parts[:i+1])})
        local_ip = get_local_ip()
        return render_template(
            'browse.html',
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
        nav_info = {}
        file_type = get_file_type(os.path.basename(filename))
        if file_type == 'image':
            images = get_sibling_images(abs_path)
            current_name = os.path.basename(abs_path)
            for i, img in enumerate(images):
                if img['name'] == current_name:
                    if i > 0:
                        nav_info['prev'] = os.path.relpath(images[i-1]['path'], get_base_dir())
                    if i < len(images) - 1:
                        nav_info['next'] = os.path.relpath(images[i+1]['path'], get_base_dir())
                    break
        preview_content, content_type = get_file_preview(abs_path)
        rel_path = filename
        return render_template(
            'view.html',
            filename=filename,
            content=preview_content,
            back_link=request.referrer or '/',
            nav_info=nav_info if file_type == 'image' else None,
            file_type=file_type
        )

    @app.route('/raw/<path:filename>')
    def raw_file(filename):
        abs_path = os.path.join(get_base_dir(), filename)
        if not os.path.exists(abs_path):
            abort(404, "File not found")
        if '../' in filename or not os.path.isfile(abs_path):
            abort(403, "Access denied")
        return send_file(abs_path)

    @app.route('/delete/<path:filename>', methods=['DELETE'])
    def delete_file(filename):
        abs_path = os.path.join(get_base_dir(), filename)
        if not os.path.exists(abs_path):
            abort(404, "File not found")
        if not os.path.isfile(abs_path):
            abort(400, "Not a file")
        try:
            os.remove(abs_path)
            return '', 204
        except Exception as e:
            abort(500, f"Could not delete file: {str(e)}")

    @app.route('/upload', methods=['GET', 'POST'])
    def upload_file():
        upload_path = request.args.get('path', '.')
        if request.method == 'POST':
            file = request.files.get('file')
            if not file or file.filename == '':
                if request.accept_mimetypes['application/json']:
                    return {"error": "No file selected"}, 400
                return "No file selected", 400
            try:
                save_dir = os.path.join(get_base_dir(), upload_path.strip('/'))
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, file.filename)
                file.save(save_path)
                if request.accept_mimetypes['application/json'] or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return {"success": True}, 200
                return redirect(f"/upload?path=/{upload_path.strip('./')}")
            except Exception as e:
                if request.accept_mimetypes['application/json']:
                    return {"error": str(e)}, 500
                return f"Error: {str(e)}", 500
        return render_template(
            'upload.html',
            upload_path=upload_path
        )

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
