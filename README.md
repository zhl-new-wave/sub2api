# ZHL Lab API Hub

实验室统一模型入口，基于 [Wei-Shaw/sub2api](https://github.com/Wei-Shaw/sub2api)。成员使用个人 Lab API Key，管理员管理上游账号、分组、额度和调用记录。

| 入口 | 地址 |
|---|---|
| 网页登录 | https://api.zhllabhub.com/login |
| API Base URL | `https://api.zhllabhub.com/v1` |
| 主域名 | https://zhllabhub.com，自动跳转到 API Hub |

## 成员快速开始

1. 向管理员申请个人账号和可用分组；首次登录后修改初始密码。
2. 在网页的「API 密钥」中创建个人 Key，核对模型、额度和有效期。
3. 按[用户指南](docs/lab-users.md)将 Key 保存到本机私有凭据文件，然后在本仓库运行：

```bash
python3 deploy/digitalocean/codex-lab.py --cd /path/to/project '阅读 README.md，用一句话说明项目用途'
```

需要 Python 3 和 Codex CLI；该脚本是只读试跑，默认禁用联网搜索。普通 API 调用、日常 Codex 配置和故障排查见[用户指南](docs/lab-users.md)。网关 Key 与 OpenAI/ChatGPT 登录凭据分别管理。

## 管理员入口

- [账号、分组、额度与成员管理](docs/lab-admin.md)
- [服务器部署、HTTPS、备份与恢复](deploy/digitalocean/README.md)
- [同步官方上游、版本管理与发布](docs/lab-maintenance.md)
- [AI agent 工作指南](AGENTS.md)

生产服务运行在新加坡 DigitalOcean Droplet，使用 Docker Compose、PostgreSQL、Redis 和 Caddy。持久数据位于服务器 `/opt/sub2api/data/`，运行密钥和数据库备份不进入仓库。公网 HTTPS 已启用；部分大陆网络曾出现连接超时，需要先确认客户端到该入口的网络可达性。

## 版本与上游

生产基线为官方 **v0.2.18**，源码提交 `ac1b8f1271be0d674fa6f074403c1410f30a3a81`。经过核对的镜像 digest 记录在 [images.lock.json](deploy/digitalocean/images.lock.json)。实验室改动集中在文档和部署工具；提交代码不会自动更新生产容器。

- `origin`：[实验室公开 fork](https://github.com/zhl-new-wave/sub2api)，默认分支 `lab`；`main` 保留官方分支。
- `upstream`：`https://github.com/Wei-Shaw/sub2api.git`，保留官方提交历史，通过分支和 PR 同步更新。
- 上游通用说明保留在 [README_CN.md](README_CN.md) / [README_JA.md](README_JA.md)。实验室操作以本 README 及其链接文档为准。

沿用上游 [LGPL-3.0 许可证](LICENSE)。账号授权和使用范围应符合实验室及上游供应商要求。
