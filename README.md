# Github Sync

## Setup

* Copy `example.env` to `.env` and edit as requrired.
* Copy `example.webhook_config.json` to `webhook_config.json` and edit as requrired.
* Run `python3 -m venv venv`.
* Run `pip install -r requirements.txt`.
* Run `python main.py`.

## For Production

### Linux

To deploy in production and avoid development server issues, use Uvicorn with a systemd service and Nginx as a reverse proxy.

#### Create a Systemd Service for Uvicorn

```bash
sudo nano /etc/systemd/system/webhook.service
```

#### Add:

```ini
[Unit]
Description=Uvicorn instance for FastAPI webhook application
After=network.target

[Service]
User=your-username
Group=your-group
WorkingDirectory=/var/www/webhook
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/uvicorn --host 127.0.0.1 --port 8000 webhook_fastapi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable webhook.service
sudo systemctl start webhook.service
sudo systemctl status webhook.service
```
