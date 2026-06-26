# NEXA Platform: Production Deployment Guide

This document provides a comprehensive, step-by-step guide for deploying the UnifyX NEXA platform to a production Linux server using Docker, Nginx, and Let's Encrypt.

---

## 1. Prerequisites

Before you begin, ensure you have the following:

*   **A Linux Server:** A fresh instance of Ubuntu 22.04 LTS is recommended.
*   **A Domain Name:** A registered domain (e.g., `nexa-quant.com`) with DNS records pointing to your server's IP address. You will need at least two A records:
    *   `nexa-quant.com` -> `YOUR_SERVER_IP`
    *   `api.nexa-quant.com` -> `YOUR_SERVER_IP`
*   **Root or Sudo Access:** Administrative privileges on the server.
*   **Software Installed:**
    *   `git`
    *   `docker`
    *   `docker-compose`

---

## 2. Initial Server Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd Lionexai
    ```

2.  **Create Production Environment File:**
    Copy the example environment file to create your production configuration. **Never commit `.env` to version control.**
    ```bash
    cp .env.example .env
    ```

3.  **Configure `.env`:**
    Open the `.env` file with a text editor (e.g., `nano .env`) and update it with your production secrets.

    *   **`POSTGRES_PASSWORD`**: Change this to a long, secure, randomly generated password.
    *   **`SECRET_KEY`**: Generate a new secret key for JWT signing. You can use `openssl rand -hex 32` to create one.
    *   **`NEXT_PUBLIC_API_URL`**: Set this to your public API domain (e.g., `https://api.nexa-quant.com`).
    *   **`BINANCE_API_KEY`, `BINANCE_SECRET_KEY`**: Enter your **production** Binance API keys.
    *   **`BYBIT_API_KEY`, `BYBIT_SECRET_KEY`**: Enter your **production** Bybit API keys.

---

## 3. Running the Application

Use the production Docker Compose file to build and start all services.

```bash
# Build the images and start all services in detached mode
docker-compose -f docker-compose.prod.yml up --build -d
```

*   `--build`: Forces a rebuild of the Docker images to include your latest code.
*   `-d`: Runs the containers in the background (detached mode).

**Verify Services:** Check that all containers are running and healthy.
```bash
docker-compose -f docker-compose.prod.yml ps
```
You should see `nexa_backend_prod`, `nexa_frontend_prod`, `nexa_db_prod`, and `nexa_redis_prod` with a status of `Up`.

**Post-Deploy Validation Setup:**

```bash
# Apply database migrations (including validation tables)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Seed demo environment (optional)
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_demo_environment.py

# Refresh validation snapshots
docker compose -f docker-compose.prod.yml exec backend python -c \
  "from app.services.validation_service import update_validation_snapshots_job; update_validation_snapshots_job()"
```

**Note:** Validation PDF chart embedding requires matplotlib in the backend image. Rebuild backend after pulling dependency changes:

```bash
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d
```

---

## 4. Nginx Reverse Proxy Setup

Nginx will act as a reverse proxy to route traffic to your frontend and backend containers and handle SSL termination.

1.  **Install Nginx:**
    ```bash
    sudo apt update
    sudo apt install nginx
    ```

2.  **Create Nginx Configuration File:**
    Create a new configuration file for your site.
    ```bash
    sudo nano /etc/nginx/sites-available/nexa
    ```

3.  **Paste the following configuration.** Replace `nexa-quant.com` and `api.nexa-quant.com` with your actual domain names.

    ```nginx
    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name nexa-quant.com api.nexa-quant.com;
        return 301 https://$host$request_uri;
    }

    # Frontend Service (Next.js)
    server {
        listen 443 ssl;
        server_name nexa-quant.com;

        # SSL settings will be added by Certbot

        location / {
            proxy_pass http://localhost:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

    # Backend Service (FastAPI)
    server {
        listen 443 ssl;
        server_name api.nexa-quant.com;

        # SSL settings will be added by Certbot

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
    ```

4.  **Enable the Site and Restart Nginx:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/nexa /etc/nginx/sites-enabled/
    sudo nginx -t # Test configuration
    sudo systemctl restart nginx
    ```

---

## 5. Securing with SSL/TLS (Let's Encrypt)

Use Certbot to automatically obtain and install free SSL certificates.

1.  **Install Certbot:**
    ```bash
    sudo apt install certbot python3-certbot-nginx
    ```

2.  **Run Certbot:**
    This command will automatically detect your domains from the Nginx config, obtain certificates, and configure Nginx for SSL.
    ```bash
    sudo certbot --nginx -d nexa-quant.com -d api.nexa-quant.com
    ```
    Follow the on-screen prompts. Certbot will also set up a cron job for automatic renewal.

---

## 6. Automated Database Backups

It is critical to back up your PostgreSQL database regularly.

1.  **Create a Backup Script:**
    ```bash
    mkdir -p /opt/nexa_backups
    nano /opt/nexa_backups/backup.sh
    ```

2.  **Paste the following script.** This script uses `docker exec` to run `pg_dump` inside the database container.

    ```bash
    #!/bin/bash
    set -euo pipefail # Exit on error, undefined variable, or pipe failure

    BACKUP_DIR="/opt/nexa_backups"
    DATE=$(date +%Y-%m-%d_%H-%M-%S)
    CONTAINER_NAME="nexa_db_prod"

    # Read from the .env file in the project directory to get DB credentials
    # IMPORTANT: Replace '/path/to/your/Lionexai' with the absolute path to your project root
    DB_USER=$(grep POSTGRES_USER /path/to/your/Lionexai/.env | cut -d '=' -f2)
    DB_NAME=$(grep POSTGRES_DB /path/to/your/Lionexai/.env | cut -d '=' -f2)

    # Dump the database
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_DIR/nexa_backup_$DATE.sql.gz"

    # Optional: Clean up old backups (older than 7 days)
    find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +7 -delete
    ```

3.  **Make the script executable:**
    ```bash
    chmod +x /opt/nexa_backups/backup.sh
    ```

4.  **Create a Cron Job:**
    Run `crontab -e` and add the following line to run the backup script every day at 3:00 AM.
    ```cron
    0 3 * * * /opt/nexa_backups/backup.sh > /dev/null 2>&1
    ```

---

## 7. Maintenance & Updates

*   **Viewing Logs:** `docker-compose -f docker-compose.prod.yml logs -f <service_name>` (e.g., `nexa_backend_prod`)
---

## 8. Post-Deploy Demo Bootstrap

After first deploy, seed institutional demo data:

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python scripts/seed_phase4.py
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_institutional_demo.py --confirm
docker compose -f docker-compose.prod.yml exec backend python scripts/run_alpha_optimization.py --phase all
docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend
```

**Demo login:** `admin@google.com` / `password123`

See [docs/README.md](../README.md) for full account list and [Demo Guide](../guides/demo_guide.md) for presentation scripts.