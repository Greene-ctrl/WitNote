from fastapi import FastAPI, HTTPException, Request, Body, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel
import os
import json
import shutil
import base64
import hashlib
import time
from typing import List, Optional, Any
import uvicorn
import requests
from pathlib import Path

app = FastAPI()

# Root directory for the notebook vault
VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "/app/vault")).resolve()
os.makedirs(VAULT_ROOT, exist_ok=True)

# Settings storage - moved to vault to avoid permission issues in /app
SETTINGS_FILE = VAULT_ROOT / ".zennote" / "web_settings.json"
os.makedirs(SETTINGS_FILE.parent, exist_ok=True)

DEFAULT_SETTINGS = {
    "theme": "light",
    "fontFamily": "system",
    "fontSize": 17,
    "ollamaBaseUrl": "http://localhost:11434",
    "ollamaEnabled": True,
    "preferredEngine": "ollama",
    "autoFallback": True,
    "customSystemPrompt": "",
    "promptTemplates": [],
    "defaultFormat": "md",
    "smartFormatConversion": True
}

def load_settings():
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def safe_join(root: Path, *paths: str) -> Path:
    try:
        joined = (root / Path(*paths)).resolve()
        if not str(joined).startswith(str(root)):
            raise HTTPException(status_code=403, detail="Access denied")
        return joined
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

class PathModel(BaseModel):
    path: Optional[str] = None

class WriteFileModel(BaseModel):
    path: str
    content: str

class RenameModel(BaseModel):
    oldPath: str
    newPath: str

class SaveImageModel(BaseModel):
    relativeDirPath: str
    base64Data: str
    fileName: Optional[str] = None

class DownloadImageModel(BaseModel):
    imageUrl: str
    relativeDirPath: str

class ImageReferencedModel(BaseModel):
    imageRelativePath: str
    excludeFilePath: Optional[str] = None

class ChatLoadModel(BaseModel):
    filePath: str

class ChatSaveModel(BaseModel):
    filePath: str
    messages: List[Any]

class SettingModel(BaseModel):
    key: str
    value: Any

class ExportPdfModel(BaseModel):
    htmlContent: str
    outputPath: str
    title: str

class ConfigModel(BaseModel):
    config: Any

# Health endpoint
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

# --- FS API ---

@app.get("/api/fs/getVaultPath")
def get_vault_path():
    return str(VAULT_ROOT)

@app.post("/api/fs/readDirectory")
async def read_directory_api(data: PathModel):
    target_path = safe_join(VAULT_ROOT, data.path) if data.path else VAULT_ROOT
    if not target_path.exists():
        return []

    def get_nodes(dir_path: Path):
        nodes = []
        try:
            for entry in os.scandir(dir_path):
                if entry.name.startswith('.') and entry.name != '.images' and entry.name != '.zennote':
                    continue

                rel_path = os.path.relpath(entry.path, VAULT_ROOT)
                stat = entry.stat()

                node = {
                    "name": entry.name,
                    "path": rel_path.replace("\\", "/"),
                    "isDirectory": entry.is_dir(),
                    "modifiedAt": int(stat.mtime * 1000)
                }

                if entry.is_dir():
                    node["children"] = get_nodes(Path(entry.path))
                else:
                    ext = os.path.splitext(entry.name)[1].lower()
                    node["extension"] = ext

                nodes.append(node)
        except Exception as e:
            print(f"Error scanning {dir_path}: {e}")

        return sorted(nodes, key=lambda x: (not x["isDirectory"], x["name"]))

    return get_nodes(target_path)

@app.post("/api/fs/readFile")
async def read_file_api(data: PathModel):
    if not data.path: raise HTTPException(status_code=400)
    full_path = safe_join(VAULT_ROOT, data.path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return full_path.read_text(encoding="utf-8")

@app.post("/api/fs/writeFile")
async def write_file_api(data: WriteFileModel):
    full_path = safe_join(VAULT_ROOT, data.path)
    os.makedirs(full_path.parent, exist_ok=True)
    full_path.write_text(data.content, encoding="utf-8")
    return True

@app.post("/api/fs/createFile")
async def create_file_api(data: PathModel):
    if not data.path: raise HTTPException(status_code=400)
    full_path = safe_join(VAULT_ROOT, data.path)
    os.makedirs(full_path.parent, exist_ok=True)
    full_path.write_text("", encoding="utf-8")
    return True

@app.post("/api/fs/createDirectory")
async def create_directory_api(data: PathModel):
    if not data.path: raise HTTPException(status_code=400)
    full_path = safe_join(VAULT_ROOT, data.path)
    os.makedirs(full_path, exist_ok=True)
    return True

@app.post("/api/fs/deleteFile")
async def delete_file_api(data: PathModel):
    if not data.path: raise HTTPException(status_code=400)
    full_path = safe_join(VAULT_ROOT, data.path)
    if full_path.is_dir():
        shutil.rmtree(full_path)
    elif full_path.exists():
        os.remove(full_path)
    return True

@app.post("/api/fs/renameFile")
async def rename_file_api(data: RenameModel):
    old_full = safe_join(VAULT_ROOT, data.oldPath)
    new_full = safe_join(VAULT_ROOT, data.newPath)
    os.rename(old_full, new_full)
    return True

@app.post("/api/fs/readFileBuffer")
async def read_file_buffer_api(data: PathModel):
    if not data.path: raise HTTPException(status_code=400)
    full_path = safe_join(VAULT_ROOT, data.path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    content = full_path.read_bytes()
    return Response(content=content, media_type="application/octet-stream")

@app.post("/api/fs/saveImage")
async def save_image_api(data: SaveImageModel):
    image_dir = safe_join(VAULT_ROOT, data.relativeDirPath, ".images")
    os.makedirs(image_dir, exist_ok=True)

    base64Data = data.base64Data
    if "," in base64Data:
        header, base64Data = base64Data.split(",", 1)
        ext = header.split("/")[1].split(";")[0]
        if ext == "jpeg": ext = "jpg"
    else:
        ext = "png"

    img_data = base64.b64decode(base64Data)
    fileName = data.fileName
    if not fileName:
        fileName = f"image_{int(time.time() * 1000)}.{ext}"

    img_path = image_dir / fileName
    img_path.write_bytes(img_data)

    return f".images/{fileName}"

@app.post("/api/fs/downloadAndSaveImage")
async def download_and_save_image_api(data: DownloadImageModel):
    try:
        response = requests.get(data.imageUrl, timeout=10)
        response.raise_for_status()
        content = response.content

        # Determine extension
        ext = "jpg"
        content_type = response.headers.get("content-type", "")
        if "png" in content_type: ext = "png"
        elif "gif" in content_type: ext = "gif"
        elif "webp" in content_type: ext = "webp"

        image_dir = safe_join(VAULT_ROOT, data.relativeDirPath, ".images")
        os.makedirs(image_dir, exist_ok=True)

        img_hash = hashlib.md5(content).hexdigest()[:8]
        file_name = f"web_{int(time.time())}_{img_hash}.{ext}"
        img_path = image_dir / file_name

        img_path.write_bytes(content)

        return f".images/{file_name}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/fs/isImageReferenced")
async def is_image_referenced_api(data: ImageReferencedModel):
    image_name = os.path.basename(data.imageRelativePath)
    image_dir = os.path.dirname(data.imageRelativePath)
    search_dir_rel = os.path.dirname(image_dir)
    search_path = safe_join(VAULT_ROOT, search_dir_rel)

    if not search_path.exists():
        return False

    for file in os.listdir(search_path):
        if data.excludeFilePath and file == os.path.basename(data.excludeFilePath):
            continue
        if not (file.endswith(".md") or file.endswith(".txt")):
            continue

        file_path = search_path / file
        if file_path.is_dir():
            continue

        if image_name in file_path.read_text(encoding="utf-8"):
            return True
    return False

# --- Chat API ---

@app.post("/api/chat/load")
async def chat_load_api(data: ChatLoadModel):
    chat_key = base64.b64encode(data.filePath.encode()).decode().replace("/", "_").replace("+", "_").replace("=", "_")
    chat_path = VAULT_ROOT / ".zennote" / "chats" / f"{chat_key}.json"
    if chat_path.exists():
        return json.loads(chat_path.read_text(encoding="utf-8"))
    return []

@app.post("/api/chat/save")
async def chat_save_api(data: ChatSaveModel):
    chat_key = base64.b64encode(data.filePath.encode()).decode().replace("/", "_").replace("+", "_").replace("=", "_")
    chats_dir = VAULT_ROOT / ".zennote" / "chats"
    os.makedirs(chats_dir, exist_ok=True)
    chat_path = chats_dir / f"{chat_key}.json"
    chat_path.write_text(json.dumps(data.messages, indent=2), encoding="utf-8")
    return True

@app.post("/api/chat/deleteAll")
async def chat_delete_all_api():
    chats_dir = VAULT_ROOT / ".zennote" / "chats"
    if chats_dir.exists():
        shutil.rmtree(chats_dir)
    return True

# --- Settings API ---

@app.get("/api/settings/get")
def get_settings_api():
    return load_settings()

@app.post("/api/settings/set")
async def set_setting_api(data: SettingModel):
    settings = load_settings()
    settings[data.key] = data.value
    save_settings(settings)
    return True

@app.post("/api/settings/reset")
def reset_settings_api():
    save_settings(DEFAULT_SETTINGS)
    return True

# --- Vault API ---

@app.post("/api/vault/syncSettings")
def sync_vault_settings_api():
    settings = load_settings()
    sync_dir = VAULT_ROOT / ".zennote" / "settings"
    os.makedirs(sync_dir, exist_ok=True)
    (sync_dir / "app_settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return True

@app.get("/api/vault/loadSettings")
def load_vault_settings_api():
    path = VAULT_ROOT / ".zennote" / "settings" / "app_settings.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

@app.post("/api/vault/saveEngineConfig")
def save_engine_config_api(data: ConfigModel):
    os.makedirs(VAULT_ROOT / ".zennote", exist_ok=True)
    path = VAULT_ROOT / ".zennote" / "engine_config.json"
    path.write_text(json.dumps(data.config, indent=2), encoding="utf-8")
    return True

@app.get("/api/vault/loadEngineConfig")
def load_engine_config_api():
    path = VAULT_ROOT / ".zennote" / "engine_config.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

# --- App API ---

@app.get("/api/app/getVersion")
def get_version_api():
    return "1.3.3"

# --- Ollama Mock API ---

@app.get("/api/ollama/listModels")
async def ollama_list_models_api():
    return {"success": True, "models": []}

# --- PDF Export ---
@app.post("/api/export-markdown-to-pdf")
async def export_pdf_api(data: ExportPdfModel):
    return {"success": False, "error": "PDF export not implemented in web version yet"}

# --- Serve static files ---

@app.get("/local-file/{path:path}")
async def serve_local_file(path: str):
    full_path = safe_join(VAULT_ROOT, path)
    if full_path.exists():
        return FileResponse(str(full_path))
    raise HTTPException(status_code=404)

# We'll serve the static files from /app/dist
if os.path.exists("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
