#!/usr/bin/env python3
"""Local health and stale-backup checks, reported in systemd logs."""
import datetime
import json
from pathlib import Path
import subprocess
import urllib.request

root = Path('/opt/sub2api')
status = []
compose = ['docker', 'compose', '-f', 'compose.yaml']
services = ['postgres', 'redis', 'sub2api']
https_enabled = (root / '.https-enabled').exists()
if https_enabled:
    compose += ['-f', 'compose.https.yaml']
    services.append('caddy')
for service in services:
    cid = subprocess.check_output(compose + ['ps', '-q', service], cwd=root, text=True).strip()
    if not cid: raise SystemExit(service + ': container not running')
    result = json.loads(subprocess.check_output(['docker', 'inspect', cid]))[0]
    if not result['State']['Running'] or result['State'].get('Health', {}).get('Status') != 'healthy':
        raise SystemExit(service + ': unhealthy')
    status.append(service + ':healthy')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:18080/health', timeout=10) as response:
    if response.status != 200: raise SystemExit('HTTP health check failed')
if https_enabled:
    env_values = dict(line.split('=', 1) for line in (root / '.env').read_text().splitlines()
                      if line and not line.startswith('#') and '=' in line)
    hostname = env_values['PUBLIC_HOST'].strip().strip('"\'')
    # Default certificate verification also detects failed certificate renewal.
    with opener.open('https://' + hostname + '/health', timeout=10) as response:
        if response.status != 200: raise SystemExit('Public HTTPS health check failed')
    status.append('https:verified')
metadata = json.loads((root / 'backups/last-success.json').read_text())
created = datetime.datetime.strptime(metadata['created_utc'], '%Y%m%dT%H%M%SZ').replace(tzinfo=datetime.timezone.utc)
if datetime.datetime.now(datetime.timezone.utc) - created > datetime.timedelta(hours=36):
    raise SystemExit('Latest database backup is older than 36 hours')
print(' '.join(status) + ' backup:fresh')
