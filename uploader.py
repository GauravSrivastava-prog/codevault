import os
import sqlite3
from flask import Flask, request, jsonify, send_file

# Initialize Flask app
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize SQLite database
DATABASE = 'uploads.db'

def init_db():
    """Initialize the database if it doesn't already exist."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

init_db()  # Ensure the database is set up when the app starts

# Route to upload code
@app.route('/upload', methods=['POST'])
def upload_code(file):
    # Logic to save the file
    filename = file.filename
    save_path = f"uploads/{filename}"
    file.save(save_path)

    # Insert file metadata into the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (filename, filepath) VALUES (?, ?)", (filename, save_path))
    conn.commit()
    conn.close()

    return {"filename": filename, "path": save_path}

def delete_file(file_id):
    """Delete a file from the server by its ID."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT filepath FROM files WHERE id=?", (file_id,))
    result = c.fetchone()

    if not result:
        conn.close()
        return {"error": "File not found in database"}, 404

    filepath = result[0]

    # Try to delete the file from the filesystem
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            conn.close()
            return {"error": f"Failed to delete file: {str(e)}"}, 500

    # Remove the file record from the database
    c.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()

    return {"message": "File deleted successfully"}, 200

# Route to list all uploaded files
@app.route('/files', methods=['GET'])
def list_files():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, filename FROM files")
    files = c.fetchall()
    conn.close()

    file_list = [
        {"id": file[0], "filename": file[1]}
        for file in files
    ]

    return jsonify({"files": file_list})

# Route to download a specific file by its ID
def download_file(file_id):
    """Download a file by its ID."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT filepath FROM files WHERE id=?", (file_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        return {"error": "File not found in database"}, 404

    filepath = result[0]

    if not os.path.exists(filepath):
        return {"error": "File not found on server"}, 404

    return send_file(filepath, as_attachment=True)

def clean_orphaned_files():
    """Remove database entries for files that are missing from the filesystem."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, filepath FROM files")
    records = c.fetchall()

    orphaned_ids = []
    for file_id, filepath in records:
        if not os.path.exists(filepath):
            orphaned_ids.append(file_id)

    for file_id in orphaned_ids:
        c.execute("DELETE FROM files WHERE id=?", (file_id,))

    conn.commit()
    conn.close()

    return {"message": f"Removed {len(orphaned_ids)} orphaned file records"}

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
