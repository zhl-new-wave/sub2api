# 成员使用指南

## 获取访问权限

网页入口为 <https://api.zhllabhub.com/login>，API Base URL 为 `https://api.zhllabhub.com/v1`。成员注册目前由管理员安排：申请个人账号和所需模型分组，首次登录后修改初始密码。

在「API 密钥」创建个人 Key，并核对它绑定的分组、额度、并发和有效期。每人使用自己的 Key；同一个人的独立实验也可分别建 Key 以追踪用量。这里的额度是网关计量单位，不等于订阅账号剩余额度或已经发生的现金支出。

## 保存个人 Key

下面的命令在终端安全输入 Key，写入本机私有文件，不在命令历史中写入真实值。已有文件时拒绝覆盖。

```bash
python3 - <<'PYKEY'
import getpass, json, os
from pathlib import Path
folder = Path.home() / '.config/zhllabhub'
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
folder.chmod(0o700)
key = getpass.getpass('个人 Lab API Key: ').strip()
if not key:
    raise SystemExit('Key 不能为空')
fd = os.open(folder / 'credentials.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as output:
    json.dump({'api_key': key}, output)
print('个人凭据文件已创建')
PYKEY
```

`getpass` 从终端读取，运行时需要交互式终端。文件默认为 `~/.config/zhllabhub/credentials.json`，也可使用其他私有路径并向脚本传 `--credentials`。Key 泄露时先在网页撤销，再创建新 Key。

## Codex 只读试跑

准备 Python 3 和 Codex CLI；验证过的客户端版本是 0.164.0。先运行 `codex --version` 确认安装，再在本仓库执行：

```bash
python3 deploy/digitalocean/codex-lab.py --cd /path/to/project '读取 README.md，并说明项目入口'
```

默认模型为 `gpt-6.1-sol`、reasoning effort 为 `low`。脚本使用 Responses 协议、只读 sandbox、临时认证和会话，禁用 web search；它不会重写日常 Codex 配置或登录文件。个人配置通过命令行覆盖，项目本身的 AGENTS/工具环境仍可能影响任务行为。模型与权限受所绑定分组限制。

可选参数：

```bash
python3 deploy/digitalocean/codex-lab.py --help
python3 deploy/digitalocean/codex-lab.py --credentials /private/my-key.json --model gpt-6.1-sol --cd /path/to/project '说明项目结构'
```

也可通过进程环境变量 `SUB2API_LAB_KEY` 提供 Key；它优先于凭据文件。不要提供 ChatGPT Cookie、上游 OAuth token 或管理员密码。

## 日常使用交互式 Codex

按当前 CLI 的 profile 文件机制，创建 `~/.codex/zhllabhub.config.toml`：

```toml
model = "gpt-6.1-sol"
model_provider = "zhllabhub"
model_reasoning_effort = "low"
web_search = "disabled"

[model_providers.zhllabhub]
name = "ZHL Lab API Hub"
base_url = "https://api.zhllabhub.com/v1"
wire_api = "responses"
env_key = "SUB2API_LAB_KEY"
requires_openai_auth = false
supports_websockets = false
```

从个人凭据文件注入环境变量并启动 profile，不将 Key 放入进程参数：

```bash
python3 -c 'import json, os, pathlib; p=pathlib.Path.home()/".config/zhllabhub/credentials.json"; os.environ["SUB2API_LAB_KEY"]=json.loads(p.read_text())["api_key"]; os.execvp("codex", ["codex", "--profile", "zhllabhub"])'
```

交互式 Codex 按本机权限设置工作，可能申请执行命令或修改项目。Skills、MCP 和本地工具来自客户端配置；网关不会自动替客户端运行它们。上述 profile 关闭搜索，联网工具和命令网络权限是另行设置的事项。

这些 provider/profile 设置应放在用户级文件中。不同版本的配置格式可能有差异，以 [OpenAI 配置文档](https://learn.chatgpt.com/docs/config-file/config-advanced)、[CLI 参数](https://learn.chatgpt.com/docs/cli/reference)和[认证说明](https://learn.chatgpt.com/docs/auth?surface=cli)为准。

## 普通 API 测试

只需 Python 标准库，下面的请求使用同一份个人凭据，输出不包含 Key：

```bash
python3 - <<'PYAPI'
import json, urllib.request
from pathlib import Path
key = json.loads((Path.home()/'.config/zhllabhub/credentials.json').read_text())['api_key']
payload = {
    'model': 'gpt-6.1-sol',
    'instructions': 'Answer briefly.',
    'input': 'Reply with exactly LAB_API_OK',
    'reasoning': {'effort': 'low'},
    'stream': True,
}
request = urllib.request.Request(
    'https://api.zhllabhub.com/v1/responses',
    data=json.dumps(payload).encode(),
    headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'},
)
with urllib.request.urlopen(request, timeout=120) as response:
    for line in response:
        print(line.decode().rstrip())
PYAPI
```

这是实际模型请求，会计入用量；成功响应包含 `response.completed` 事件。Base URL 已含 `/v1`，请求路径再追加 `/responses`。上游订阅通道对参数和工具的支持与官方 API 可能不同；不要默认全部 OpenAI API 字段都可用。

## 用量与故障排查

在网页查看自己的调用记录、余额、Key 限额和到期日。报障时提供时间、模型、HTTP 状态及请求 ID；不要转发完整 Authorization header。

| 现象 | 先检查 |
|---|---|
| 连接超时或 TLS 错误 | 客户端网络能否访问域名；未连到服务时调整 Key 无效 |
| 401 | 是否使用 Lab Key，是否被撤销或过期 |
| 403 / 无模型权限 | 分组、模型白名单、用户或 Key 状态 |
| 429 | 用户/Key 并发与速率、上游账号当前限制 |
| 余额不足 / 无可用账号 | 联系管理员核对配额、上游授权和账号状态 |
| 首字较慢 | 上游负载、推理强度、输入长度；用短请求与时间戳协助定位 |

2026-11-01 部分大陆网络直连曾超时；域名与有效证书不能保证所有网络均可达。不要把一个网络的失败直接视为服务故障。
