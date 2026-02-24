# Deployment Guide

Two deployment options are available: **Docker** (recommended — single command) or **manual Linux server** setup.

---

## Option A: Docker (Recommended)

Spins up PostgreSQL 18, Flask/Gunicorn, and Caddy (automatic HTTPS via Let's Encrypt) with a single command.

### Prerequisites

- A server with Docker and Docker Compose v2 installed
- A domain name pointed at the server's IP (required for Let's Encrypt)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/ohvoice-adam/petition-qc.git
cd petition-qc

# Create your .env from the example
cp .env.example .env
nano .env          # set DOMAIN, POSTGRES_PASSWORD, SECRET_KEY
```

Generate a strong secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Start everything:

```bash
docker compose up -d
```

The app will be available at `https://your-domain.com` within a minute or two (Caddy provisions the certificate automatically).

### Managing the Deployment

```bash
# View logs
docker compose logs -f

# Stop
docker compose down

# Deploy an update
git pull
docker compose build
docker compose up -d
```

### Backups

The upload volume (`uploads`) and database volume (`postgres_data`) are Docker named volumes. The built-in SFTP backup feature (Settings → Database Backup) works identically to the manual deployment — configure host, user, SSH key, and remote path in the web UI.

---

## Option B: Manual Linux Server

This guide covers deploying Petition QC on a Linux server (Ubuntu 22.04/24.04 or Debian 12) using Gunicorn behind Nginx with PostgreSQL.

## System Requirements

- Ubuntu 22.04+ or Debian 12+
- 2 GB RAM minimum (4 GB recommended for large voter files)
- 20 GB disk space minimum
- PostgreSQL 12+
- Python 3.10+
- Nginx

---

## 1. Install System Dependencies

```bash
sudo apt update && sudo apt install -y \
  python3 python3-pip python3-venv \
  postgresql postgresql-contrib \
  nginx \
  postgresql-client \
  git
```

`postgresql-client` is required for the database backup feature (`pg_dump`).

---

## 2. Create a System User

Run the application as a dedicated non-root user:

```bash
sudo useradd --system --create-home --shell /bin/bash petition
```

---

## 3. PostgreSQL Setup

```bash
sudo -u postgres psql
```

```sql
CREATE USER petition_user WITH PASSWORD 'your-strong-password-here';
CREATE DATABASE petition_qc OWNER petition_user;
\c petition_qc
CREATE EXTENSION IF NOT EXISTS pg_trgm;
\q
```

Verify the extension is active:

```bash
sudo -u postgres psql -d petition_qc -c "\dx"
```

---

## 4. Deploy the Application

```bash
# Switch to the petition user
sudo su - petition

# Clone the repository
git clone https://github.com/ohvoice-adam/petition-qc.git /home/petition/petition-qc
cd /home/petition/petition-qc

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 5. Configure Environment

```bash
cp .env.example .env
nano .env
```

Set the following (replace all placeholder values):

```env
DATABASE_URL=postgresql://petition_user:your-strong-password-here@localhost:5432/petition_qc
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
FLASK_DEBUG=0
UPLOAD_FOLDER=/home/petition/petition-qc/uploads
```

> **Note**: If your database password contains special characters, URL-encode them (`@` → `%40`, `:` → `%3A`).

Create the uploads directory:

```bash
mkdir -p /home/petition/petition-qc/uploads
```

---

## 6. Initialize the Database

```bash
# Still as the petition user, with venv active
cd /home/petition/petition-qc
source venv/bin/activate

# Initialize tables
python run.py
# Press Ctrl+C after you see "Running on http://0.0.0.0:5000"
```

---

## 7. Import Voter Data

Upload your voter file CSV to the server, then import via the web UI at `/imports` (after the service is running), or via the command line:

```bash
python scripts/import_voters.py /path/to/voter_file.csv
python scripts/create_indexes.py
```

---

## 8. Systemd Service

Exit back to your sudo-capable user, then create the service file:

```bash
exit  # back to your regular user

sudo nano /etc/systemd/system/petition-qc.service
```

```ini
[Unit]
Description=Petition QC
After=network.target postgresql.service

[Service]
Type=simple
User=petition
Group=petition
WorkingDirectory=/home/petition/petition-qc
EnvironmentFile=/home/petition/petition-qc/.env
ExecStart=/home/petition/petition-qc/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 3600 \
    --worker-class sync \
    --access-logfile /home/petition/petition-qc/logs/access.log \
    --error-logfile /home/petition/petition-qc/logs/error.log \
    "app:create_app()"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create the logs directory and enable the service:

```bash
sudo -u petition mkdir -p /home/petition/petition-qc/logs

sudo systemctl daemon-reload
sudo systemctl enable petition-qc
sudo systemctl start petition-qc

# Verify it's running
sudo systemctl status petition-qc
```

> **Workers**: 4 workers is a good default. For a server with N CPU cores, use `2 * N + 1` workers. The `--timeout 3600` (1 hour) accommodates large voter file uploads.

---

## 9. Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/petition-qc
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Required for large voter file uploads (up to 1 GB)
    client_max_body_size 1G;
    client_body_timeout 3600s;

    # Serve static files directly
    location /static {
        alias /home/petition/petition-qc/app/static;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy everything else to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

Enable the site and test:

```bash
sudo ln -s /etc/nginx/sites-available/petition-qc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 10. SSL with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically update your Nginx config to redirect HTTP to HTTPS and configure SSL. Renewal is handled automatically via a systemd timer.

---

## 11. Backup Configuration

The application includes a built-in database backup feature (accessible at **Settings → Database Backup** when logged in as admin). It backs up all tables except the voter file (which can be re-imported) via SCP/SFTP to a remote server.

### Set Up SSH Key for Backups

Generate a dedicated SSH key pair on the app server (as the `petition` user):

```bash
sudo -u petition ssh-keygen -t ed25519 -f /home/petition/.ssh/backup_key -N ""
```

Copy the public key to your backup server:

```bash
sudo -u petition cat /home/petition/.ssh/backup_key.pub
# Paste this into ~/.ssh/authorized_keys on your backup server
```

Then in the Petition QC web UI (Settings page), configure:
- **SCP Host**: backup server hostname or IP
- **SCP Port**: 22 (or your custom SSH port)
- **SCP User**: username on the backup server
- **SSH Private Key**: upload the private key file (`/home/petition/.ssh/backup_key`)
- **Remote Directory**: directory on backup server (e.g., `/backups/petition-qc`)

Backups are in PostgreSQL custom format. To restore:

```bash
pg_restore -d petition_qc /path/to/backup.dump
```

### Automated Scheduled Backups

Configure the schedule directly in the web UI (Settings → Database Backup → Automatic Schedule). Options are hourly, daily (02:00 UTC), and weekly (Sunday 02:00 UTC). The app's built-in scheduler handles timing automatically — no cron setup required.

---

## 12. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## 13. Updates and Maintenance

### Deploying Updates

```bash
sudo su - petition
cd /home/petition/petition-qc
source venv/bin/activate

git pull
pip install -r requirements.txt

# Run any database migrations
flask db upgrade

exit

sudo systemctl restart petition-qc
```

### Viewing Logs

```bash
# Application logs
sudo journalctl -u petition-qc -f

# Gunicorn access/error logs
sudo tail -f /home/petition/petition-qc/logs/error.log
sudo tail -f /home/petition/petition-qc/logs/access.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Checking Service Status

```bash
sudo systemctl status petition-qc
```

---

## 14. Troubleshooting

### App won't start

Check the service logs:
```bash
sudo journalctl -u petition-qc -n 50 --no-pager
```

Common causes:
- Wrong `DATABASE_URL` in `.env`
- PostgreSQL not running: `sudo systemctl status postgresql`
- Missing `pg_trgm` extension: connect to the DB and run `CREATE EXTENSION pg_trgm;`

### 502 Bad Gateway

Gunicorn isn't running or crashed:
```bash
sudo systemctl restart petition-qc
sudo systemctl status petition-qc
```

### Large file uploads timing out

Increase the Nginx `client_body_timeout` and `proxy_read_timeout`, and the Gunicorn `--timeout` value. The current defaults in this guide (3600s) should handle files up to 1 GB.

### Database connection errors

```bash
# Test connection
sudo -u petition psql "$DATABASE_URL" -c "SELECT 1;"
```

### Backup fails

- Verify `pg_dump` is installed: `which pg_dump`
- Verify the SSH key path is correct and readable by the `petition` user
- Test SSH connectivity manually: `sudo -u petition ssh -i /home/petition/.ssh/backup_key user@backuphost`
- Check the remote path exists and is writable
