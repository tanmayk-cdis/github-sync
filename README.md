# Github Sync

## Setup

* Copy `example.env` to `.env` and edit as requrired.
* Copy `example.webhook_config.json` to `webhook_config.json` and edit as requrired.
* Run `python3 -m venv venv`.
* Run `pip install -r requirements.txt`.
* Run `python main.py`.

## For Production

uvicorn --host 127.0.0.1 --port 8201 --workers 3 main:app

## Changing Repo Permissions

sudo chown -R user:webhookgroup /var/www/repo1 /var/www/repo2
sudo chmod -R u+rwx,g+rwx /var/www/repo1 /var/www/repo2
sudo chmod -R g+s /var/www/repo1 /var/www/repo2