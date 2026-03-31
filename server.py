#!/usr/bin/env python3
"""
PS4 JB Web Server - Custom HTTP server with admin panel.
Serves static files from /web directory and provides GoldHEN update functionality.
"""

import http.server
import json
import os
import subprocess
import sys
import tempfile
import traceback
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs

# Check if running inside Home Assistant environment
IS_HA_ADDON = os.path.exists("/data/options.json")

WEB_DIR = "/web" if IS_HA_ADDON else os.path.join(os.getcwd(), "web")
PERSISTENT_DIR = "/data" if IS_HA_ADDON else os.path.join(os.getcwd(), "data")

GOLDHEN_FILENAME = "goldhen.bin"
GITHUB_API_URL = "https://api.github.com/repos/GoldHEN/GoldHEN/releases"

# Global state for update progress
update_status = {
    "running": False,
    "message": "",
    "success": False,
    "version": "",
    "logs": []
}


def log(msg):
    """Log a message to console and update_status logs."""
    print(f"[GoldHEN] {msg}", flush=True)
    update_status["logs"].append(msg)


ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PS4 JB - Admin Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: #16213e;
            border-radius: 16px;
            padding: 40px;
            width: 90%;
            max-width: 600px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 1px solid #0f3460;
        }
        h1 {
            text-align: center;
            margin-bottom: 8px;
            color: #e94560;
            font-size: 24px;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .status-box {
            background: #0f3460;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
            min-height: 60px;
        }
        .status-box .label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .status-box .value {
            font-size: 16px;
            font-weight: 500;
        }
        .status-box .value.success { color: #4ecca3; }
        .status-box .value.error { color: #e94560; }
        .status-box .value.info { color: #3282b8; }
        .btn {
            display: block;
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #e94560, #c23152);
            color: white;
        }
        .btn-primary:hover {
            background: linear-gradient(135deg, #c23152, #a02040);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(233, 69, 96, 0.4);
        }
        .btn:disabled {
            background: #333;
            color: #666;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .btn-secondary {
            background: #0f3460;
            color: #e0e0e0;
            margin-top: 10px;
        }
        .btn-secondary:hover {
            background: #1a4a80;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(15, 52, 96, 0.4);
        }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #666;
            border-top-color: #fff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .file-info {
            background: #0f3460;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
        }
        .file-info .row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
        }
        .file-info .row .key { color: #888; }
        .file-info .row .val { color: #4ecca3; font-weight: 500; }
        .log-box {
            background: #0a0a1a;
            border: 1px solid #0f3460;
            border-radius: 10px;
            padding: 12px;
            margin-top: 20px;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            color: #8892b0;
        }
        .log-box .log-line { margin: 2px 0; }
        .log-box .log-line.error { color: #e94560; }
        .log-box .log-line.success { color: #4ecca3; }
        .log-box .log-line.info { color: #3282b8; }
        .log-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            margin-top: 20px;
            margin-bottom: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>&#x1F3AE; PS4 JB Admin</h1>
        <p class="subtitle">GoldHEN Update Manager</p>

        <div class="file-info" id="fileInfo">
            <div class="row">
                <span class="key">GoldHEN Status:</span>
                <span class="val" id="fileStatus">Checking...</span>
            </div>
            <div class="row" id="fileSizeRow" style="display:none">
                <span class="key">File Size:</span>
                <span class="val" id="fileSize">-</span>
            </div>
        </div>

        <div class="status-box">
            <div class="label">Update Status</div>
            <div class="value info" id="statusText">Ready</div>
        </div>

        <button class="btn btn-primary" id="updateBtn" onclick="startUpdate()">
            &#x1F504; Update GoldHEN
        </button>

        <button class="btn btn-secondary" id="backBtn" onclick="back()">
            &#x1F504; Back
        </button>

        <div class="status-box" style="margin-top: 20px;">
            <div class="label">Manual Upload</div>
            <p style="font-size: 13px; margin-bottom: 12px; color: #aaa;">If you downloaded GoldHEN from Ko-fi, upload the file (.bin or .7z archive) here.</p>
            <input type="file" id="goldhenFile" accept=".bin,.7z" style="margin-bottom: 12px; width: 100%; color: #fff; font-size: 14px;">
            <button class="btn btn-secondary" id="uploadBtn" onclick="uploadFile()">
                &#x1F4E4; Upload Custom File
            </button>
        </div>

        <div class="log-label">Debug Log</div>
        <div class="log-box" id="logBox">
            <div class="log-line info">Waiting for action...</div>
        </div>
    </div>

    <script>
        function checkFile() {
            fetch('./_api/goldhen_status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('fileStatus').textContent =
                        data.exists ? 'Installed (' + data.version + ')' : 'Not installed';
                    if (data.exists && data.size) {
                        document.getElementById('fileSizeRow').style.display = 'flex';
                        document.getElementById('fileSize').textContent =
                            (data.size / 1024).toFixed(1) + ' KB';
                    }
                })
                .catch(e => {
                    document.getElementById('fileStatus').textContent = 'Error: ' + e.message;
                });
        }

        function addLog(msg, cls) {
            const box = document.getElementById('logBox');
            const line = document.createElement('div');
            line.className = 'log-line ' + (cls || '');
            line.textContent = msg;
            box.appendChild(line);
            box.scrollTop = box.scrollHeight;
        }

        function back() {
            //'window.location.href = './';
            window.close();
        }

        function uploadFile() {
            const fileInput = document.getElementById('goldhenFile');
            if (fileInput.files.length === 0) {
                alert('Please select a goldhen.bin file first.');
                return;
            }
            const file = fileInput.files[0];
            const btn = document.getElementById('uploadBtn');
            const status = document.getElementById('statusText');
            
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Uploading...';
            status.className = 'value info';
            status.textContent = 'Uploading custom file...';
            addLog('Starting manual upload of ' + file.name + ' (' + file.size + ' bytes)...', 'info');

            fetch('./_api/upload_goldhen', {
                method: 'POST',
                body: file,
                headers: {
                    'Content-Type': 'application/octet-stream',
                    'X-File-Name': encodeURIComponent(file.name)
                }
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    status.className = 'value success';
                    status.textContent = 'Uploaded successfully!';
                    addLog('SUCCESS: ' + data.message, 'success');
                } else {
                    status.className = 'value error';
                    status.textContent = 'Upload error: ' + data.message;
                    addLog('FAILED: ' + data.message, 'error');
                }
                btn.disabled = false;
                btn.innerHTML = '&#x1F4E4; Upload Custom File';
                fileInput.value = '';
                checkFile();
            })
            .catch(err => {
                status.className = 'value error';
                status.textContent = 'Upload network error';
                addLog('NETWORK ERROR: ' + err.message, 'error');
                btn.disabled = false;
                btn.innerHTML = '&#x1F4E4; Upload Custom File';
            });
        }

        function startUpdate() {
            const btn = document.getElementById('updateBtn');
            const status = document.getElementById('statusText');
            const logBox = document.getElementById('logBox');
            logBox.innerHTML = '';

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Updating...';
            status.className = 'value info';
            status.textContent = 'Downloading from GitHub...';
            addLog('Starting GoldHEN update...', 'info');

            fetch('./_api/update_goldhen', { method: 'POST' })
                .then(r => {
                    addLog('Response received: HTTP ' + r.status, 'info');
                    return r.json();
                })
                .then(data => {
                    // Show all log lines from server
                    if (data.logs && data.logs.length > 0) {
                        data.logs.forEach(l => addLog(l));
                    }

                    if (data.success) {
                        status.className = 'value success';
                        status.textContent = 'Updated to ' + data.version + '!';
                        addLog('SUCCESS: ' + data.message, 'success');
                    } else {
                        status.className = 'value error';
                        status.textContent = 'Error: ' + data.message;
                        addLog('FAILED: ' + data.message, 'error');
                    }
                    btn.disabled = false;
                    btn.innerHTML = '&#x1F504; Update GoldHEN';
                    checkFile();
                })
                .catch(err => {
                    status.className = 'value error';
                    status.textContent = 'Network error: ' + err.message;
                    addLog('NETWORK ERROR: ' + err.message, 'error');
                    btn.disabled = false;
                    btn.innerHTML = '&#x1F504; Update GoldHEN';
                });
        }

        checkFile();
    </script>
</body>
</html>
"""


def get_latest_prerelease():
    """Fetch the latest pre-release from GoldHEN GitHub releases."""
    log(f"Fetching releases from: {GITHUB_API_URL}")

    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "HA-PS4-JB-Addon"}
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = resp.status
            log(f"GitHub API response: HTTP {status_code}")
            raw = resp.read().decode()
            log(f"Response size: {len(raw)} bytes")
            releases = json.loads(raw)
    except urllib.error.URLError as e:
        log(f"URL Error: {e}")
        raise Exception(f"Failed to fetch releases: {e}")
    except Exception as e:
        log(f"Request error: {type(e).__name__}: {e}")
        raise

    log(f"Total releases found: {len(releases)}")

    # Find the first pre-release (they come sorted newest first)
    for i, release in enumerate(releases):
        is_pre = release.get("prerelease", False)
        tag = release.get("tag_name", "?")
        log(f"  Release #{i+1}: {tag} (prerelease={is_pre})")

        if is_pre:
            name = release["name"]
            assets = release.get("assets", [])
            log(f"  Found pre-release: {name}, assets: {len(assets)}")

            for asset in assets:
                asset_name = asset["name"]
                log(f"    Asset: {asset_name} ({asset.get('size', '?')} bytes)")

                if asset_name.endswith(".7z"):
                    download_url = asset["browser_download_url"]
                    log(f"  Selected: {asset_name}")
                    log(f"  Download URL: {download_url}")
                    return {
                        "tag": tag,
                        "name": name,
                        "download_url": download_url,
                        "filename": asset_name
                    }

            log(f"  WARNING: No .7z asset found in this pre-release")

    raise Exception("No pre-release with .7z asset found in any release")


def download_and_extract_goldhen():
    """Download latest pre-release 7z and extract goldhen.bin to web directory."""
    global update_status
    update_status = {
        "running": True,
        "message": "Finding latest pre-release...",
        "success": False,
        "version": "",
        "logs": []
    }

    try:
        log("=== Starting GoldHEN Update ===")

        # Get latest pre-release info
        release = get_latest_prerelease()
        version = release["tag"]
        download_url = release["download_url"]
        log(f"Will download: {release['filename']} (version {version})")

        # Download 7z file
        with tempfile.TemporaryDirectory() as tmpdir:
            log(f"Temp directory: {tmpdir}")
            archive_path = os.path.join(tmpdir, release["filename"])

            log(f"Downloading from: {download_url}")
            req = urllib.request.Request(download_url, headers={"User-Agent": "HA-PS4-JB-Addon"})

            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = resp.read()
                    log(f"Downloaded: {len(data)} bytes")
                    with open(archive_path, "wb") as f:
                        f.write(data)
                    log(f"Saved to: {archive_path}")
            except urllib.error.URLError as e:
                log(f"Download URL Error: {e}")
                raise Exception(f"Download failed: {e}")
            except Exception as e:
                log(f"Download error: {type(e).__name__}: {e}")
                raise

            # Check if file exists and has content
            if os.path.exists(archive_path):
                fsize = os.path.getsize(archive_path)
                log(f"Archive file size: {fsize} bytes")
            else:
                log("ERROR: Archive file was not saved!")
                raise Exception("Archive file not found after download")

            # Extract only goldhen.bin using 7z
            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            cmd = ["7z", "e", archive_path, "-o" + extract_dir, "goldhen.bin", "-r", "-y"]
            log(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=60
            )

            log(f"7z exit code: {result.returncode}")
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    log(f"  7z stdout: {line}")
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    log(f"  7z stderr: {line}")

            if result.returncode != 0:
                raise Exception(f"7z extraction failed (exit code {result.returncode})")

            # List extracted files
            log(f"Listing extracted dir: {extract_dir}")
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    full = os.path.join(root, f)
                    log(f"  Extracted file: {f} ({os.path.getsize(full)} bytes)")

            # Find goldhen.bin in extracted files
            goldhen_src = os.path.join(extract_dir, "goldhen.bin")
            if not os.path.exists(goldhen_src):
                log("goldhen.bin not in root, searching recursively...")
                found = False
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.lower() == "goldhen.bin":
                            goldhen_src = os.path.join(root, f)
                            log(f"  Found at: {goldhen_src}")
                            found = True
                            break
                    if found:
                        break

            if not os.path.exists(goldhen_src):
                # Try extracting all files as fallback
                log("goldhen.bin not found, trying to extract ALL files...")
                cmd2 = ["7z", "e", archive_path, "-o" + extract_dir, "-r", "-y"]
                log(f"Running: {' '.join(cmd2)}")
                result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
                log(f"7z exit code: {result2.returncode}")
                if result2.stdout:
                    for line in result2.stdout.strip().split('\n'):
                        log(f"  7z stdout: {line}")

                log("All extracted files:")
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        full = os.path.join(root, f)
                        log(f"  {f} ({os.path.getsize(full)} bytes)")
                        if f.lower() == "goldhen.bin":
                            goldhen_src = os.path.join(root, f)

            if not os.path.exists(goldhen_src):
                raise Exception("goldhen.bin not found in archive after full extraction")

            src_size = os.path.getsize(goldhen_src)
            log(f"goldhen.bin found: {src_size} bytes")

            # Save to persistent /data/ directory
            persistent_dest = os.path.join(PERSISTENT_DIR, GOLDHEN_FILENAME)
            log(f"Saving to persistent storage: {persistent_dest}")
            with open(goldhen_src, "rb") as src_f:
                with open(persistent_dest, "wb") as dst_f:
                    dst_f.write(src_f.read())

            final_size = os.path.getsize(persistent_dest)
            log(f"goldhen.bin saved: {final_size} bytes at {persistent_dest}")

            # Symlink into /web/ so HTTP server can serve it
            web_dest = os.path.join(WEB_DIR, GOLDHEN_FILENAME)
            if os.path.exists(web_dest) or os.path.islink(web_dest):
                os.remove(web_dest)
            os.symlink(persistent_dest, web_dest)
            log(f"Symlinked: {web_dest} -> {persistent_dest}")
            log(f"=== Update Complete: {version} ===")

            update_status.update({
                "running": False,
                "message": f"Successfully updated to {version} ({final_size} bytes)",
                "success": True,
                "version": version
            })

    except Exception as e:
        log(f"ERROR: {type(e).__name__}: {e}")
        log(traceback.format_exc())
        update_status.update({
            "running": False,
            "message": str(e),
            "success": False,
            "version": ""
        })


class PS4JBHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler that serves static files and admin API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/_admin":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(ADMIN_HTML.encode("utf-8"))
            return

        if parsed.path == "/_api/goldhen_status":
            self._handle_goldhen_status()
            return

        if parsed.path == "/_api/update_status":
            self._send_json(update_status)
            return

        # Serve static files normally
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/_api/update_goldhen":
            self._handle_update_goldhen()
            return

        if parsed.path == "/_api/upload_goldhen":
            self._handle_upload_manual()
            return

        self.send_error(404)

    def _handle_goldhen_status(self):
        goldhen_path = os.path.join(WEB_DIR, GOLDHEN_FILENAME)
        exists = os.path.exists(goldhen_path)
        result = {"exists": exists}
        if exists:
            result["size"] = os.path.getsize(goldhen_path)
            result["version"] = update_status.get("version", "unknown")
        self._send_json(result)

    def _handle_update_goldhen(self):
        if update_status.get("running"):
            self._send_json({"success": False, "message": "Update already in progress", "logs": update_status["logs"]})
            return

        # Run synchronously so the client gets the result
        download_and_extract_goldhen()
        self._send_json(update_status)

    def _handle_upload_manual(self):
        """Handle raw binary upload of goldhen.bin"""
        if update_status.get("running"):
            self._send_json({"success": False, "message": "Another update is currently running."})
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json({"success": False, "message": "No file data received."})
                return
                
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                self._send_json({"success": False, "message": "File is too large (max 10MB)."})
                return

            import urllib.parse
            filename = urllib.parse.unquote(self.headers.get('X-File-Name', 'goldhen.bin'))
            
            # Read the raw binary from the POST body
            file_data = self.rfile.read(content_length)
            
            # If it's a 7z archive, extract it first
            if filename.lower().endswith(".7z"):
                print(f"[HTTP] Uploaded file is a .7z archive: {filename}", flush=True)
                with tempfile.TemporaryDirectory() as tmpdir:
                    archive_path = os.path.join(tmpdir, "uploaded.7z")
                    with open(archive_path, "wb") as f:
                        f.write(file_data)
                    
                    extract_dir = os.path.join(tmpdir, "extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    cmd = ["7z", "e", archive_path, "-o" + extract_dir, "goldhen.bin", "-r", "-y"]
                    print(f"[HTTP] Running: {' '.join(cmd)}", flush=True)
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode != 0:
                        raise Exception(f"7z extraction failed: {result.stderr}")
                        
                    goldhen_src = os.path.join(extract_dir, "goldhen.bin")
                    if not os.path.exists(goldhen_src):
                        # fallback recursive search
                        found = False
                        for root, dirs, files in os.walk(extract_dir):
                            for f in files:
                                if f.lower() == "goldhen.bin":
                                    goldhen_src = os.path.join(root, f)
                                    found = True
                                    break
                            if found: break
                    
                    if not os.path.exists(goldhen_src):
                        # Extract all fallback
                        cmd2 = ["7z", "e", archive_path, "-o" + extract_dir, "-r", "-y"]
                        subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
                        for root, dirs, files in os.walk(extract_dir):
                            for f in files:
                                if f.lower() == "goldhen.bin":
                                    goldhen_src = os.path.join(root, f)
                                    break
                    
                    if not os.path.exists(goldhen_src):
                        raise Exception("goldhen.bin not found inside the uploaded .7z archive.")
                    
                    # Read the extracted goldhen.bin back into file_data so the rest of the flow can just save it
                    with open(goldhen_src, "rb") as f:
                        file_data = f.read()
                    print(f"[HTTP] Extracted goldhen.bin: {len(file_data)} bytes", flush=True)
            
            # Save to persistent /data/ directory
            persistent_dest = os.path.join(PERSISTENT_DIR, GOLDHEN_FILENAME)
            print(f"[HTTP] Saving manually uploaded file to {persistent_dest} ({len(file_data)} bytes)", flush=True)
            with open(persistent_dest, "wb") as dst_f:
                dst_f.write(file_data)

            # Symlink directly to /web/
            web_dest = os.path.join(WEB_DIR, GOLDHEN_FILENAME)
            if os.path.exists(web_dest) or os.path.islink(web_dest):
                os.remove(web_dest)
            os.symlink(persistent_dest, web_dest)
            
            self._send_json({"success": True, "message": f"Successfully uploaded {len(file_data)} bytes."})
        except Exception as e:
            print(f"[HTTP] Upload Error: {e}", flush=True)
            self._send_json({"success": False, "message": str(e)})

    def _send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}", flush=True)


def get_port():
    """Read port from HA addon options or fallback to default."""
    options_path = "/data/options.json"
    if os.path.exists(options_path):
        try:
            with open(options_path) as f:
                options = json.load(f)
            port = int(options.get("port", 8000))
            print(f"[CONFIG] Read port from options.json: {port}", flush=True)
            return port
        except Exception as e:
            print(f"[CONFIG] Error reading options.json: {e}", flush=True)
    # Fallback: command line arg or default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"[CONFIG] Using fallback port: {port}", flush=True)
    return port


def restore_goldhen_symlink():
    """Restore goldhen.bin symlink from /data/ to /web/ on startup."""
    persistent = os.path.join(PERSISTENT_DIR, GOLDHEN_FILENAME)
    web_link = os.path.join(WEB_DIR, GOLDHEN_FILENAME)
    if os.path.exists(persistent):
        if os.path.exists(web_link) or os.path.islink(web_link):
            os.remove(web_link)
        os.symlink(persistent, web_link)
        size = os.path.getsize(persistent)
        print(f"[STARTUP] Restored goldhen.bin symlink ({size} bytes)", flush=True)
    else:
        print(f"[STARTUP] No goldhen.bin in persistent storage", flush=True)


def main():
    port = get_port()

    os.makedirs(WEB_DIR, exist_ok=True)
    restore_goldhen_symlink()

    # List files in web directory at startup
    print(f"[STARTUP] Files in {WEB_DIR}:", flush=True)
    for item in os.listdir(WEB_DIR):
        full = os.path.join(WEB_DIR, item)
        if os.path.isfile(full):
            print(f"  {item} ({os.path.getsize(full)} bytes)", flush=True)
        else:
            print(f"  {item}/ (directory)", flush=True)

    server = http.server.HTTPServer(("0.0.0.0", port), PS4JBHandler)
    print(f"[STARTUP] PS4 JB Web Server started on port {port}", flush=True)
    print(f"[STARTUP] Serving files from {WEB_DIR}", flush=True)
    print(f"[STARTUP] Admin panel: http://0.0.0.0:{port}/_admin", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.", flush=True)
        server.server_close()


if __name__ == "__main__":
    main()
