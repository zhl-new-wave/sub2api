#!/usr/bin/env bash
# Enable only AFTER restoring the database and verifying the app.
set -euo pipefail
test "${EUID}" -eq 0
test -f /opt/sub2api/.env
test -f /opt/sub2api/backup-recipient.txt
chown root:root /opt/sub2api/labctl /opt/sub2api/backup-export.py /opt/sub2api/backup.py /opt/sub2api/health.py
chmod 700 /opt/sub2api/labctl /opt/sub2api/backup-export.py
ln -sfn /opt/sub2api/labctl /usr/local/sbin/sub2api-lab
ln -sfn /opt/sub2api/backup-export.py /usr/local/sbin/sub2api-backup-export
cat > /etc/systemd/system/sub2api-lab.service <<'EOF'
[Unit]
Description=Lab Sub2API Docker Compose stack
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/sub2api
ExecStart=/usr/local/sbin/sub2api-lab up
ExecStop=/usr/local/sbin/sub2api-lab stop
TimeoutStartSec=240
TimeoutStopSec=120
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/sub2api-backup.service <<'EOF'
[Unit]
Description=Encrypted Sub2API backup with full PostgreSQL restore verification
Requires=sub2api-lab.service
After=sub2api-lab.service
[Service]
Type=oneshot
User=root
UMask=0077
Nice=10
IOSchedulingClass=idle
WorkingDirectory=/opt/sub2api
ExecStart=/usr/bin/python3 /opt/sub2api/backup.py
TimeoutStartSec=1800
EOF
cat > /etc/systemd/system/sub2api-backup.timer <<'EOF'
[Unit]
Description=Daily Sub2API backup (03:30 Asia/Shanghai)
[Timer]
OnCalendar=*-*-* 19:30:00 UTC
RandomizedDelaySec=5m
Persistent=true
Unit=sub2api-backup.service
[Install]
WantedBy=timers.target
EOF
cat > /etc/systemd/system/sub2api-health.service <<'EOF'
[Unit]
Description=Sub2API container, HTTP and backup freshness checks
After=docker.service sub2api-lab.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/sub2api/health.py
TimeoutStartSec=45
EOF
cat > /etc/systemd/system/sub2api-health.timer <<'EOF'
[Unit]
Description=Check Sub2API health every five minutes
[Timer]
OnBootSec=5m
OnUnitActiveSec=5m
Unit=sub2api-health.service
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now sub2api-lab.service sub2api-backup.timer
systemctl start sub2api-backup.service
systemctl start sub2api-health.service
systemctl enable --now sub2api-health.timer
