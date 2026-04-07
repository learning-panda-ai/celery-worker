#!/bin/bash
set -e
exec > /var/log/user-data.log 2>&1

# ── System setup ────────────────────────────────────────────────────────────
apt update && apt upgrade -y
apt-get install -y libgl1 git curl netcat-openbsd

# ── NVIDIA driver (570 required for CUDA 12.8 / torch cu128) ────────────────
apt-get install -y nvidia-driver-570

# ── Miniconda ────────────────────────────────────────────────────────────────
wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
bash /tmp/miniconda.sh -b -p /root/miniconda3
rm /tmp/miniconda.sh

export PATH="/root/miniconda3/bin:$PATH"
/root/miniconda3/bin/conda init bash
source /root/.bashrc

# Accept conda ToS
/root/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
/root/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# ── Python env ───────────────────────────────────────────────────────────────
/root/miniconda3/bin/conda create -n env python=3.14 -y

# ── Clone worker ─────────────────────────────────────────────────────────────
cd /home/ubuntu
git clone https://github.com/learning-panda-ai/celery-worker
cd celery-worker

# ── Install dependencies ─────────────────────────────────────────────────────
/root/miniconda3/envs/env/bin/pip install -r requirements.txt

# ── Reinstall torch with CUDA 12.8 (matches driver 570 / CUDA 12.8) ─────────
/root/miniconda3/envs/env/bin/pip uninstall torch torchvision torchaudio -y
/root/miniconda3/envs/env/bin/pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128

# ── .env file ────────────────────────────────────────────────────────────────
# Option A: pull from AWS Secrets Manager (recommended for production)
# apt-get install -y awscli
# aws secretsmanager get-secret-value --secret-id celery-worker-env \
#     --query SecretString --output text > /home/ubuntu/celery-worker/.env

# Option B: write directly (replace placeholder values before use)
cat > /home/ubuntu/celery-worker/.env << 'EOF'
REDIS_URL=redis://:learningpanda@3.110.62.102:6379/0
MILVUS_URI=http://3.110.62.102:19530
EOF

# ── Log and run directories ───────────────────────────────────────────────────
mkdir -p /var/log/celery /var/run/celery

# ── systemd service ───────────────────────────────────────────────────────────
cat > /etc/systemd/system/celery.service << 'EOF'
[Unit]
Description=Learning Panda Celery Worker
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/home/ubuntu/celery-worker
ExecStart=/root/miniconda3/envs/env/bin/celery \
    -A worker.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --logfile=/var/log/celery/worker.log \
    --pidfile=/var/run/celery/worker.pid
ExecStop=/root/miniconda3/envs/env/bin/celery \
    -A worker.celery_app control shutdown
Environment="PATH=/root/miniconda3/envs/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="CUDA_VISIBLE_DEVICES=0"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable celery

# ── Reboot to activate NVIDIA driver ─────────────────────────────────────────
# Celery will auto-start after reboot via systemd
reboot
