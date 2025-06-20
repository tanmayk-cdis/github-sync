from fastapi import FastAPI, Request, HTTPException, status
import subprocess
import hmac
import hashlib
import os
import json
from dotenv import load_dotenv

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
                try:
                    # Pull the repository
                    repo_path = matched_config['repo_path']
                    os.chdir(repo_path)
                    subprocess.run(['git', 'pull'], check=True)

                    # Run the restart command
                    restart_command = matched_config['restart_command']
                    subprocess.run([restart_command], shell=True, check=True)
                    return {"message": f"Pull and restart successful for {repo_path} on branch {matched_config['branch']}"}
                except subprocess.CalledProcessError as e:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    return {"message": "Event received"}

if __name__ == '__main__':
    import uvicorn
    # Load port from environment variable, default to 8000
    port = int(os.getenv('WEBHOOK_PORT', 8000))
    uvicorn.run(app, host='127.0.0.1', port=port)