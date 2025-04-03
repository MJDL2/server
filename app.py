import os
from flask import Flask, render_template, request, send_file, url_for, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from pathlib import Path
import math

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB max file size
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_file_tree(path):
    tree = []
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        relative_path = os.path.relpath(full_path, app.config['UPLOAD_FOLDER'])
        if os.path.isdir(full_path):
            tree.append({
                'name': item,
                'type': 'folder',
                'path': relative_path,
                'children': get_file_tree(full_path)
            })
        else:
            size = os.path.getsize(full_path)
            tree.append({
                'name': item,
                'type': 'file',
                'path': relative_path,
                'size': size
            })
    return tree

@app.route('/')
def index():
    file_tree = get_file_tree(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', file_tree=file_tree)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    folder = request.form.get('folder', '')
    chunk_index = int(request.form.get('chunk_index', 0))
    total_chunks = int(request.form.get('total_chunks', 1))
    
    if file.filename == '':
        return 'No selected file', 400
    
    if file:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        mode = 'wb' if chunk_index == 0 else 'ab'
        
        with open(file_path, mode) as f:
            file.save(f)
            
        if chunk_index == total_chunks - 1:
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'complete': True
            })
        else:
            return jsonify({
                'status': 'success',
                'message': f'Chunk {chunk_index + 1}/{total_chunks} uploaded',
                'complete': False
            })

@app.route('/download/<path:filepath>')
def download_file(filepath):
    def generate():
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        file_size = os.path.getsize(file_path)
        total_chunks = math.ceil(file_size / CHUNK_SIZE)
        
        with open(file_path, 'rb') as f:
            for chunk_index in range(total_chunks):
                chunk = f.read(CHUNK_SIZE)
                if chunk:
                    yield chunk
                    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
    return Response(
        stream_with_context(generate()),
        headers={
            'Content-Disposition': f'attachment; filename={os.path.basename(filepath)}',
            'Content-Length': str(os.path.getsize(file_path))
        }
    )

@app.route('/delete/<path:filepath>')
def delete_file(filepath):
    try:
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)
        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return 'File deleted successfully', 200
    except Exception as e:
        return str(e), 400

@app.route('/create_folder', methods=['POST'])
def create_folder():
    try:
        folder_path = request.form.get('path', '')
        folder_name = request.form.get('name', '')
        if not folder_name:
            return 'Folder name is required', 400
        
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_path, folder_name)
        os.makedirs(full_path, exist_ok=True)
        return 'Folder created successfully', 200
    except Exception as e:
        return str(e), 400

@app.route('/file_tree')
def get_tree():
    return jsonify(get_file_tree(app.config['UPLOAD_FOLDER']))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, max_content_length=10 * 1024 * 1024 * 1024)