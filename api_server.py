from fastapi import FastAPI
import time
import os

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/api/info")
def get_info():
    return {
        "app": "WitNote",
        "version": "1.3.3",
        "platform": "Linux (VNC)",
        "vault_path": os.environ.get("VAULT_ROOT", "/home/user/vault")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7861)
