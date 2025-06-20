from fastapi import FastAPI, Request, HTTPException, status
import subprocess
import hmac
import hashlib
import os
import json
from dotenv import load_dotenv
import threading

app = FastAPI()

# Load environment variables from .env file
load_dotenv()

# Load webhook configurations from JSON file
CONFIG_FILE = 'webhook_config.json'
try:
    with open(CONFIG_FILE, 'r') as f:
        config_data = json.load(f)
    WEBHOOK_CONFIGS = {
        entry['secret']: {
            'repo_path': entry['repo_path'],
            'restart_command': entry['restart_command'],
            'branch': entry['branch']
        }
        for entry in config_data.get('webhooks', [])
    }
except FileNotFoundError:
    raise FileNotFoundError(f"Configuration file {CONFIG_FILE} not found")
except json.JSONDecodeError:
    raise ValueError(f"Invalid JSON format in {CONFIG_FILE}")
except KeyError as e:
    raise KeyError(f"Missing required field {e} in {CONFIG_FILE}")

if not WEBHOOK_CONFIGS:
    raise ValueError("No valid webhook configurations found in JSON file")

def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    computed_sig = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_sig, signature)

def run_commands(repo_path: str, restart_command: str):
    """Run git pull and restart command sequentially, logging output."""
    try:
        os.chdir(repo_path)
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
        print(f"git pull output for {repo_path}: {result.stdout}{result.stderr}")
        result = subprocess.run([restart_command], shell=True, capture_output=True, text=True, check=True)
        print(f"Restart command output for {repo_path}: {result.stdout}{result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error in {repo_path}: {e}\n{e.stderr}")
    except Exception as e:
        print(f"Unexpected error in {repo_path}: {str(e)}")

@app.post("/webhook")
async def webhook(request: Request):
    # Get the signature from the request headers
    signature = request.headers.get('X-Hub-Signature-256', '')

    # Read the raw body
    payload = await request.body()

    # Try to match the signature with any configured secret
    matched_config = None
    for secret, config in WEBHOOK_CONFIGS.items():
        if verify_signature(payload, secret, signature):
            matched_config = config
            break

    # If no matching secret is found, return 403
    if not matched_config:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature or no matching secret")

    # Check if the event is a push to the configured branch
    if request.headers.get('X-GitHub-Event') == 'push':
        try:
            payload_json = await request.json()
            branch_ref = f"refs/heads/{matched_config['branch']}"
            if payload_json.get('ref') == branch_ref:
                # Start commands in a background thread
                thread = threading.Thread(
                    target=run_commands,
                    args=(matched_config['repo_path'], matched_config['restart_command'])
                )
                thread.start()
                return {"message": f"Pull and restart triggered for {matched_config['repo_path']} on branch {matched_config['branch']}"}
        except ValueError as e:
            print(f"JSON parsing error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {str(e)}")

    return {"message": "Event received"}

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('WEBHOOK_PORT', 8000))
    uvicorn.run(app, host='127.0.0.1', port=port)