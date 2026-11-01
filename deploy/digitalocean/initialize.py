#!/usr/bin/env python3
"""Initialize a NEW, private lab deployment without printing credentials."""

import argparse
import json
import os
from pathlib import Path
import secrets


def private_write(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-email", default="lab-admin@lab.invalid")
    args = parser.parse_args()
    if not args.admin_email or any(c.isspace() for c in args.admin_email) or any(c in args.admin_email for c in "#$'\"\\=") or "@" not in args.admin_email:
        parser.error("Use a plain email address without spaces or dotenv syntax.")

    directory = Path(__file__).resolve().parent
    targets = [directory / ".env", directory / "admin-credentials.txt"]
    data = directory / "data"
    if any(p.exists() for p in targets) or data.exists():
        raise SystemExit("Existing credentials or data found. Refusing initialization. Follow the documented backup/restore procedure.")
    image_lock = json.loads((directory / 'images.lock.json').read_text())
    os.chmod(directory, 0o700)
    data.mkdir(mode=0o700)
    for name in ["app", "postgres", "redis", "caddy", "caddy-config"]:
        (data / name).mkdir(mode=0o700)

    values = {
        **image_lock['images'],
        "APP_PORT": "18080",
        "PUBLIC_HOST": "",
        "PUBLIC_APEX": "",
        "ADMIN_EMAIL": args.admin_email,
        "ADMIN_PASSWORD": secrets.token_urlsafe(24),
        "POSTGRES_PASSWORD": secrets.token_hex(32),
        "REDIS_PASSWORD": secrets.token_hex(32),
        "JWT_SECRET": secrets.token_hex(32),
        "TOTP_ENCRYPTION_KEY": secrets.token_hex(32),
    }
    private_write(targets[0], "".join(f"{key}={value}\n" for key, value in values.items()))
    private_write(
        targets[1],
        "Sub2API lab administrator — fresh installation\n"
        "Access through an SSH tunnel: http://127.0.0.1:28080/login\n"
        f"Email: {values['ADMIN_EMAIL']}\n"
        f"Password: {values['ADMIN_PASSWORD']}\n"
        "Keep private. Do not paste passwords, API keys, or OAuth tokens into chat.\n",
    )
    print("Initialized .env and admin-credentials.txt with mode 0600; credentials were not printed.")
    print("Private bootstrap only. No public HTTP port, account import, or legal acknowledgement was performed.")


if __name__ == "__main__":
    main()
