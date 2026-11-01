# AI agent 工作指南

## 先读哪些文件

1. `README.md`：当前服务入口与文档索引。
2. `docs/lab-users.md`：成员接入、个人 Key、Codex 与 API 示例。
3. `docs/lab-admin.md`：上游账号、成员、分组和额度管理。
4. `deploy/digitalocean/README.md`：部署、HTTPS、备份恢复和日常运维。
5. `docs/lab-maintenance.md`：官方上游同步及发布流程。

修改子目录前，检查该目录是否有更具体的 `AGENTS.md`。不要把上游 `DEV_GUIDE.md` 中的历史开发者账号、Windows 路径或本地数据库示例当成本实验室的运行配置。

## 当前基线

- 官方上游：`https://github.com/Wei-Shaw/sub2api.git`。
- 实验室公开 fork 的 remote 为 `origin`，官方 remote 为 `upstream`；默认工作分支为 `lab`，`main` 保留官方分支。
- 线上应用基于官方 `v0.2.18` / `ac1b8f1271be0d674fa6f074403c1410f30a3a81`。
- `deploy/digitalocean/images.lock.json` 记录核对过的源码与镜像。更新源码、构建新镜像、部署到生产是三个需要分别验证的步骤。
- 保留上游 Git 历史、Go module 路径、LICENSE 和版权信息。优先将实验室改动放在文档、部署配置和独立工具中。

## 代码地图

| 路径 | 用途 |
|---|---|
| `backend/cmd/server/` | Go 服务入口、版本、Wire 装配 |
| `backend/internal/handler/` | HTTP/API handlers |
| `backend/internal/service/` | 网关转发、调度、计费等核心行为 |
| `backend/internal/repository/` | 数据访问 |
| `backend/ent/schema/` | Ent schema；生成文件在 `backend/ent/` |
| `backend/migrations/` | SQL 迁移 |
| `frontend/src/` | Vue 3 / TypeScript 用户与管理员页面 |
| `deploy/digitalocean/` | 实验室部署、Codex 试跑、备份与健康检查 |
| `.github/workflows/` | 上游 CI、安全扫描与发布工具 |

## 本地工作

先执行 `git status --short`，保护已有改动。使用功能分支，禁止覆盖他人工作或对共享分支 force-push。

Go 版本以 `backend/go.mod` 为准；前端使用 pnpm，安装时保留 lockfile。常用命令：

```bash
make -C backend test-unit
make -C backend test-integration
pnpm --dir frontend install --frozen-lockfile
make test-frontend
make build
```

修改 Ent schema 后运行 `make -C backend generate` 并检查生成差异。涉及数据库的集成测试应使用测试环境，不能指向生产数据库。

文档或独立 Python/Compose 工具的改动只运行相应检查，不为它们运行无关的全站构建。部署工具发生行为变化时，应验证成功路径、错误退出和凭据保护；不要在普通测试中消耗真实上游额度。真实模型请求只在任务授权且确有需要时执行，并限制次数。

实验室工具检查由 `.github/workflows/lab-tools.yml` 执行，本地可运行：

```bash
python3 -m compileall -q deploy/digitalocean
python3 -m unittest discover -s deploy/digitalocean -p 'test_*.py' -v
bash -n deploy/digitalocean/labctl deploy/digitalocean/install-docker-ubuntu.sh deploy/digitalocean/install-maintenance.sh
```

## 运行边界

生产目录为 `/opt/sub2api`。先读取当前状态，再选择必要操作；本地修改或 Git 推送不代表获准部署任意新版本。

- 只用 `sub2api-lab` 管理现有栈，保持 HTTPS overlay 一起加载。
- 不在已有实例运行 `initialize.py`。不删除 `data/`，不把数据库或 Redis 端口开放到公网。
- 固定 JWT/TOTP、数据库密码和账号 OAuth 状态需要保留；重建容器不能重新生成这些值。
- 修改持久数据或升级前创建加密备份并核对恢复验证结果；数据库迁移后回退按恢复流程处理。
- 不默认跟随 `latest`，不自动更新数据库大版本。同步上游代码后必须另外审查迁移与镜像。
- 当前上游白名单仅覆盖 OpenAI。接入新供应商时按实际域名扩展，保持禁止内网目标。
- OAuth 登录、验证码、首次法律承诺由账号持有人本人完成，不代为签署承诺。

## 凭据与发布

`.env`、用户 Key、OAuth token、JWT/TOTP 密钥、数据库 dump、加密备份、age 私钥、SSH 私钥和后台导出都不能进入 Git、PR 或终端输出。

只提交明确列出的文件，提交前检查 `git diff --cached`。确认 `AGENTS.md` 和实验室文档没有被上游 `.gitignore` 误忽略。不要用 `git add .` 将运行目录一起提交。

仓库只维护当前环境所需的通用代码和文档；历史机器资料、个人绝对路径及运维取证材料留在仓库外的私有归档中。不得为清理文档而删除远端备份、停用接收端或移除仍在使用的访问授权。

完成后报告改了什么、运行了哪些相关检查、是否实际部署，以及尚存的真实限制。
