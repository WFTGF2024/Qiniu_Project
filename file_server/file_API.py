import os
import sys
import platform

# ---- MySQL driver selection ----
if platform.system().lower().startswith("win"):
    import pymysql
    pymysql.install_as_MySQLdb()
    print("[INFO] Using PyMySQL (Windows)")
else:
    import MySQLdb
    print("[INFO] Using MySQLdb (Linux/Unix)")

from flask import Flask, request, jsonify, send_file, abort
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---- MySQL configuration ----
MYSQL_SOCKET = "/var/lib/mysql/mysql.sock"  # Linux 默認 socket 路徑
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "Qiniu"
MYSQL_PASSWORD = "20250922"
MYSQL_DB = "Qiniu_Project"

# Default: try socket first (Linux)
if os.path.exists(MYSQL_SOCKET):
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_UNIX_SOCKET'] = MYSQL_SOCKET
else:
    app.config['MYSQL_HOST'] = MYSQL_HOST
    app.config['MYSQL_PORT'] = MYSQL_PORT

app.config['MYSQL_USER'] = MYSQL_USER
app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
app.config['MYSQL_DB'] = MYSQL_DB
mysql = MySQL(app)

# ---- File storage configuration ----
UPLOAD_ROOT = "user_data"
MAX_FILES = 20
MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200 MB


# ---- Utility functions ----
def get_folder_size(folder):
    """Calculate total folder size"""
    return sum(os.path.getsize(os.path.join(folder, f)) for f in os.listdir(folder))


def delete_oldest_file(user_folder, user_id):
    """Delete the oldest file (FIFO)"""
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT file_id, filepath FROM user_files WHERE user_id=%s ORDER BY uploaded_at ASC LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone()
    if row:
        file_id, filepath = row
        if os.path.exists(filepath):
            os.remove(filepath)
        cur.execute("DELETE FROM user_files WHERE file_id=%s", (file_id,))
        mysql.connection.commit()


# ---- Temporary storage API ----
@app.route("/files/<int:user_id>", methods=["GET"])
def list_files(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT file_id, filename FROM user_files WHERE user_id=%s", (user_id,))
    files = [{"file_id": f[0], "filename": f[1]} for f in cur.fetchall()]
    return jsonify(files)


@app.route("/upload/<int:user_id>", methods=["POST"])
def upload_file(user_id):
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    filename = secure_filename(file.filename)
    user_folder = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(user_folder, exist_ok=True)

    filepath = os.path.join(user_folder, filename)
    file.save(filepath)

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM user_files WHERE user_id=%s", (user_id,))
    file_count = cur.fetchone()[0]
    if file_count >= MAX_FILES:
        delete_oldest_file(user_folder, user_id)

    if get_folder_size(user_folder) > MAX_TOTAL_SIZE:
        os.remove(filepath)
        return jsonify({"error": "Total size exceeds 200 MB"}), 400

    cur.execute(
        "INSERT INTO user_files (user_id, filename, filepath, size) VALUES (%s,%s,%s,%s)",
        (user_id, filename, filepath, os.path.getsize(filepath)),
    )
    mysql.connection.commit()

    return jsonify({"message": "File uploaded successfully", "filename": filename})


@app.route("/download/<int:file_id>", methods=["GET"])
def download_file(file_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT filepath, filename FROM user_files WHERE file_id=%s", (file_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    filepath, filename = row
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route("/files/<int:file_id>", methods=["DELETE"])
def delete_file(file_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT filepath FROM user_files WHERE file_id=%s", (file_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    filepath = row[0]
    if os.path.exists(filepath):
        os.remove(filepath)
    cur.execute("DELETE FROM user_files WHERE file_id=%s", (file_id,))
    mysql.connection.commit()
    return jsonify({"message": "File deleted successfully"})


# ---- Permanent storage API ----
@app.route("/permanent/upload/<int:user_id>", methods=["POST"])
def upload_permanent_file(user_id):
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    filename = secure_filename(file.filename)
    user_folder = os.path.join(UPLOAD_ROOT, f"{user_id}_permanent")
    os.makedirs(user_folder, exist_ok=True)

    filepath = os.path.join(user_folder, filename)
    file.save(filepath)

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO user_permanent_files (user_id, filename, filepath, size) VALUES (%s,%s,%s,%s)",
        (user_id, filename, filepath, os.path.getsize(filepath)),
    )
    mysql.connection.commit()
    return jsonify({"message": "File uploaded permanently", "filename": filename})


@app.route("/permanent/files/<int:user_id>", methods=["GET"])
def list_permanent_files(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT file_id, filename FROM user_permanent_files WHERE user_id=%s", (user_id,))
    files = [{"file_id": f[0], "filename": f[1]} for f in cur.fetchall()]
    return jsonify(files)


@app.route("/permanent/download/<int:file_id>", methods=["GET"])
def download_permanent_file(file_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT filepath, filename FROM user_permanent_files WHERE file_id=%s", (file_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    filepath, filename = row
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route("/permanent/files/<int:file_id>", methods=["DELETE"])
def delete_permanent_file(file_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT filepath FROM user_permanent_files WHERE file_id=%s", (file_id,))
    row = cur.fetchone()
    if not row:
        abort(404)
    filepath = row[0]
    if os.path.exists(filepath):
        os.remove(filepath)
    cur.execute("DELETE FROM user_permanent_files WHERE file_id=%s", (file_id,))
    mysql.connection.commit()
    return jsonify({"message": "Permanent file deleted successfully"})


# ---- Startup DB check ----
def check_mysql_connection():
    try:
        if os.path.exists(MYSQL_SOCKET):
            conn = __import__("MySQLdb").connect(
                unix_socket=MYSQL_SOCKET,
                user=MYSQL_USER,
                passwd=MYSQL_PASSWORD,
                db=MYSQL_DB
            )
            conn.close()
            print(f"[INFO] ✅ Connected to MySQL via socket ({MYSQL_SOCKET})")
            return True
        else:
            conn = __import__("MySQLdb").connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                passwd=MYSQL_PASSWORD,
                db=MYSQL_DB
            )
            conn.close()
            print(f"[INFO] ✅ Connected to MySQL via TCP ({MYSQL_HOST}:{MYSQL_PORT})")
            return True
    except Exception as e:
        print(f"[ERROR] ❌ Cannot connect to MySQL: {e}")
        return False


# ---- Main entry ----
if __name__ == "__main__":
    if not check_mysql_connection():
        sys.exit(1)
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    app.run(host="0.0.0.0", debug=True, port=7201, use_reloader=False)
