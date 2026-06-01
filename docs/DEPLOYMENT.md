# Deployment Guide

## Pre-Deployment Checklist

- [ ] Environment variables configured in `.env`
- [ ] Database credentials secured
- [ ] SSL certificates obtained (production)
- [ ] Backup strategy in place
- [ ] Monitoring/alerting configured
- [ ] Documentation reviewed
- [ ] Tests passing locally
- [ ] Docker images built successfully

## Local Development Deployment

### Using Docker Compose

```bash
# Clone repository
git clone <repo-url>
cd Lionexai

# Verify .env file exists
ls -la .env

# Build and start services
docker-compose up -d

# Verify all services running
docker-compose ps

# Check logs
docker-compose logs -f

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Troubleshooting Local Deployment

```bash
# View service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db
docker-compose logs redis

# Restart specific service
docker-compose restart backend

# Recreate all services
docker-compose down
docker-compose up -d

# Check database connection
docker exec nexa_db psql -U nexa_admin -d nexa_mvp -c "SELECT version();"

# Check Redis connection
docker exec nexa_redis redis-cli ping
```

## Production Deployment

### VPS Prerequisites

- Ubuntu 20.04+ or equivalent
- 4GB+ RAM
- 20GB+ SSD storage
- Open ports: 80, 443, 5432 (internal), 6379 (internal)
- SSH access configured

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 2: Clone Repository

```bash
cd /opt
sudo git clone <repo-url> nexa
cd nexa
sudo chown -R $USER:$USER .
```

### Step 3: Configure Environment

```bash
# Create production .env
cat > .env << EOF
ENVIRONMENT=production
PROJECT_NAME="UnifyX NEXA"

# Database
POSTGRES_USER=nexa_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=nexa_prod
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Frontend (API calls are relative, so this can be the main domain or empty)
NEXT_PUBLIC_API_URL=https://yourdomain.com
EOF

# Secure .env file
chmod 600 .env
```

### Step 4: Setup Reverse Proxy (Nginx)

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/nexa > /dev/null << 'EOF'
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /api/ws/ {
        proxy_pass http://backend/api/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400; # Keep connection open
    }

    # Health check
    location /api/health {
        proxy_pass http://backend;
        access_log off;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/nexa /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx config
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 5: Obtain SSL Certificate

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (requires email)
sudo certbot certonly --standalone \
    -d yourdomain.com \
    -d www.yourdomain.com \
    --email admin@yourdomain.com \
    --agree-tos

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Step 6: Deploy Services

```bash
cd /opt/nexa

# Start services
docker-compose -f docker-compose.yml up -d

# Wait for services to start (30-60 seconds)
sleep 30

# Verify services
docker-compose ps

# Check logs for errors
docker-compose logs --tail=50
```

### Step 7: Verification

```bash
# Test frontend
curl -I https://yourdomain.com
# Should return 200 OK

# Test API
curl -I https://yourdomain.com/api/health
# Should return 200 OK

# Check database
docker exec nexa_db psql -U nexa_prod -d nexa_prod -c "SELECT COUNT(*) FROM mandates;"

# Check WebSocket
curl -I -N -H "Connection: Upgrade" -H "Upgrade: websocket" https://yourdomain.com/ws/market
```

## Backup & Recovery

### Database Backup

```bash
# Manual backup
docker exec nexa_db pg_dump \
    -U nexa_prod \
    nexa_prod > backup_$(date +%Y%m%d).sql

# Compressed backup
docker exec nexa_db pg_dump \
    -U nexa_prod \
    nexa_prod | gzip > backup_$(date +%Y%m%d).sql.gz

# S3 backup (requires AWS CLI)
docker exec nexa_db pg_dump -U nexa_prod nexa_prod | \
    gzip | \
    aws s3 cp - s3://your-bucket/backups/nexa_$(date +%Y%m%d).sql.gz
```

### Automated Daily Backup

```bash
# Create backup script
cat > /opt/nexa/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/nexa/backups"
mkdir -p $BACKUP_DIR
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

docker exec nexa_db pg_dump -U nexa_prod nexa_prod | \
    gzip > $BACKUP_DIR/backup_$TIMESTAMP.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: backup_$TIMESTAMP.sql.gz"
EOF

chmod +x /opt/nexa/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/nexa/backup.sh") | crontab -
```

### Database Recovery

```bash
# From local backup
gzip -dc backup_20240601.sql.gz | \
    docker exec -i nexa_db psql -U nexa_prod nexa_prod

# Verify recovery
docker exec nexa_db psql -U nexa_prod -d nexa_prod -c "SELECT COUNT(*) FROM trades;"
```

## Monitoring

### Log Aggregation

```bash
# View backend logs
docker-compose logs backend -f --tail=100

# View frontend logs
docker-compose logs frontend -f --tail=100

# View database logs
docker-compose logs db -f --tail=50

# Save logs to file
docker-compose logs > logs_$(date +%Y%m%d).txt
```

### System Monitoring

```bash
# Check container resource usage
docker stats

# Check disk usage
df -h

# Check memory usage
free -h

# Check network connectivity
docker exec nexa_backend curl -I http://db:5432
docker exec nexa_backend curl -I http://redis:6379
```

### Alerts Setup (Optional)

```bash
# Monitor critical events (requires additional setup)
# - Database connection failures
# - Kill switch triggers
# - Error rate spikes
# - Disk space warnings
```

## Scaling

### Horizontal Scaling

For multiple servers:

1. **Separate Database Server**
   ```bash
   # Run database on dedicated server
   # Update POSTGRES_HOST in .env pointing to separate server
   ```

2. **Load Balancer**
   ```
   Load Balancer (HAProxy/Nginx)
       │
       ├─► Backend 1
       ├─► Backend 2
       └─► Backend 3
   
   All connecting to shared:
   - PostgreSQL
   - Redis
   ```

3. **Redis Cluster** (for high availability)
   ```bash
   # Replace single Redis with Redis Sentinel/Cluster setup
   ```

### Vertical Scaling

```bash
# Increase container resource limits in docker-compose.yml

services:
  backend:
    ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

## Maintenance

### Regular Tasks

**Daily:**
- Monitor disk space
- Check error logs
- Verify backups completed

**Weekly:**
- Review performance metrics
- Check for security updates
- Test backup recovery

**Monthly:**
- Update dependencies
- Security audit
- Capacity planning

### Update Procedure

```bash
cd /opt/nexa

# Stop services
docker-compose down

# Backup database
./backup.sh

# Update code
git pull origin main

# Rebuild images
docker-compose build

# Start services
docker-compose up -d

# Verify
docker-compose logs --tail=20
```

## Security Hardening

### Firewall Configuration

```bash
# UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 5432/tcp    # PostgreSQL (internal only)
sudo ufw allow 6379/tcp    # Redis (internal only)
sudo ufw enable
```

### SSH Key-Only Access

```bash
# Disable password authentication
sudo sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Environment Variable Security

```bash
# Keep secrets out of version control
echo ".env" >> /opt/nexa/.gitignore
echo ".env.local" >> /opt/nexa/.gitignore

# Use strong, unique passwords
# Change default credentials before production
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Port already in use: Change port in docker-compose.yml
# - Database not ready: Wait 30 seconds, then retry
# - Out of disk space: Free up space or expand volume
```

### Database Connection Issues

```bash
# Test connection
docker exec nexa_backend psql -h db -U nexa_prod -d nexa_prod -c "\dt"

# Check environment variables
docker exec nexa_backend env | grep POSTGRES

# Verify network connectivity
docker network ls
docker network inspect nexa_default
```

### Performance Issues

```bash
# Check container resource usage
docker stats nexa_backend

# Increase resources if needed:
# Edit docker-compose.yml resource limits
# Restart: docker-compose restart backend

# Check database query performance
docker exec nexa_db psql -U nexa_prod nexa_prod -c "EXPLAIN ANALYZE SELECT * FROM trades LIMIT 10;"
```

### WebSocket Connection Issues

```bash
# Check WebSocket endpoint
curl -v -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  https://yourdomain.com/ws/market

# Verify Nginx WebSocket configuration
grep -A 5 "location /ws/" /etc/nginx/sites-enabled/nexa
```

## Health Checks

### Automated Health Monitoring

```bash
# Create health check script
cat > /opt/nexa/health_check.sh << 'EOF'
#!/bin/bash

echo "=== NEXA Health Check ==="
echo "Timestamp: $(date)"

# Check services running
echo -n "Docker services: "
docker-compose ps | grep -c "Up" | xargs echo "running"

# Check API health
echo -n "API status: "
curl -s http://localhost:8000/health | jq .status

# Check database
echo -n "Database: "
docker exec nexa_db psql -U nexa_prod -d nexa_prod -c "SELECT 'OK'" 2>/dev/null | grep OK || echo "FAIL"

# Check Redis
echo -n "Redis: "
docker exec nexa_redis redis-cli ping

# Check disk space
echo -n "Disk space: "
df /opt/nexa | tail -1 | awk '{print $5}'

echo "=== End Health Check ==="
EOF

chmod +x /opt/nexa/health_check.sh

# Run periodically
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/nexa/health_check.sh >> /opt/nexa/health.log") | crontab -
```

---

For additional support or deployment issues, refer to the main README and architecture documentation.
