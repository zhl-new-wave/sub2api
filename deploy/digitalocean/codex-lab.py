#!/usr/bin/env python3
"""Run a single read-only Codex task through the lab gateway.

Use SUB2API_LAB_KEY or --credentials pointing to a private JSON with api_key.
Uses temporary command-line configuration and ephemeral authentication.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prompt')
    parser.add_argument('--cd', type=Path, default=Path.cwd())
    parser.add_argument('--base-url', default='https://api.zhllabhub.com/v1')
    parser.add_argument('--model', default='gpt-6.1-sol')
    parser.add_argument('--credentials', type=Path, default=Path.home() / '.config/zhllabhub/credentials.json')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    binary = shutil.which('codex')
    if not binary: parser.error('Install Codex CLI first')
    if not args.cd.is_dir(): parser.error('Task directory does not exist')
    url = urlparse(args.base_url)
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ['localhost', '127.0.0.1', '::1']):
        parser.error('Use HTTPS, or HTTP over a loopback SSH tunnel')
    key = os.environ.get('SUB2API_LAB_KEY')
    if not key:
        try: key = json.loads(args.credentials.read_text())['api_key']
        except (OSError, ValueError, KeyError): parser.error('Set SUB2API_LAB_KEY or provide a private credentials JSON')
    if not isinstance(key, str) or not key.strip(): parser.error('Empty gateway key')
    config = {'model_provider': 'sub2api_lab', 'model_reasoning_effort': 'low',
              'cli_auth_credentials_store': 'ephemeral', 'web_search': 'disabled',
              'model_providers.sub2api_lab.name': 'Sub2API lab Singapore',
              'model_providers.sub2api_lab.base_url': args.base_url.rstrip('/'),
              'model_providers.sub2api_lab.env_key': 'SUB2API_LAB_KEY',
              'model_providers.sub2api_lab.wire_api': 'responses',
              'model_providers.sub2api_lab.requires_openai_auth': False,
              'model_providers.sub2api_lab.supports_websockets': False}
    command = [binary, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
               '--sandbox', 'read-only', '--model', args.model, '--cd', str(args.cd.resolve())]
    if args.json: command.append('--json')
    for name, value in config.items(): command.extend(['-c', name + '=' + json.dumps(value)])
    command.append(args.prompt)
    env = os.environ.copy()
    env['SUB2API_LAB_KEY'] = key
    return subprocess.call(command, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
