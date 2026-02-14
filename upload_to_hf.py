from huggingface_hub import HfApi
import os

def upload_files():
    api = HfApi()
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN environment variable not set.")
        return

    repo_id = "AUXteam/WitNote"

    print(f"Uploading files to {repo_id}...")

    api.upload_folder(
        folder_path=".",
        repo_id=repo_id,
        repo_type="space",
        token=token,
        ignore_patterns=[
            "node_modules/**",
            ".git/**",
            "dist-electron/**",
            "release/**",
            "build/**",
            "docs/**",
            "scripts/**",
            "*.log",
            "*.dmg",
            "*.exe",
            "*.AppImage",
            "*.deb",
            "package-lock.json",
            "upload_to_hf.py"
        ]
    )
    print("Upload complete!")

if __name__ == "__main__":
    upload_files()
