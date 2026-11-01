# 仓库维护与上游同步

## 仓库关系

实验室使用官方项目的公开 fork，保留 Git 历史与 GitHub 上游关系。`lab` 是实验室默认分支，`main` 保留官方分支。推荐 remote 关系：

```text
origin    https://github.com/zhl-new-wave/sub2api.git
upstream  https://github.com/Wei-Shaw/sub2api.git
```

新克隆只会得到 `origin`，需要补上官方 remote：

```bash
git clone https://github.com/zhl-new-wave/sub2api.git
cd sub2api
git remote add upstream https://github.com/Wei-Shaw/sub2api.git
git fetch upstream --tags
```

GitHub 页面显示官方父仓库；Git remote `upstream` 是每个 clone 的本地配置，需要分别添加。Fork 的关系及权限见 [GitHub 官方说明](https://docs.github.com/en/pull-requests/reference/forks)。

当前生产源代码为官方 `v0.2.18` 的 `ac1b8f1271be0d674fa6f074403c1410f30a3a81`。完整锁定信息见 `deploy/digitalocean/images.lock.json`。实验室提交叠加在此基线上，核心应用源码保持原样。

## 同步官方更新

通过功能分支和 PR 更新，优先选择审查过的正式版本；不要在生产目录执行 `git pull` 自动追随上游 main。

```bash
git switch lab
git pull --ff-only origin lab
git fetch upstream --tags
git switch -c maintenance/upstream-VERSION
# 将 vX.Y.Z 替换成已经审查的真实版本。
git merge --no-ff vX.Y.Z
```

处理冲突时重点保留实验室 `README.md`、`AGENTS.md`、`docs/lab-*.md`、`deploy/digitalocean/` 和它们的忽略规则。不要用 `--allow-unrelated-histories`、重建 `.git` 或 force-push 来“修复”同步。

检查 release notes、数据库迁移、协议变化、镜像平台和客户端兼容性，完成相关测试后发 PR。保持上游原 tag 不变，不复用官方 `v*` tag 为实验室部署打标签。

将更新分支推送到 `origin`，发 PR 合并到 `lab`。GitHub 的 Sync fork 可用于跟进 `main`，不会自动升级 `lab` 或生产服务。不要将实验室提交直接推到官方仓库。

## 源码与运行镜像必须对应

代码合并不会自动修改服务器 `.env`。生产当前仍运行官方固定 digest 的镜像；只修改本地源码并不会让改动出现在这个镜像里。

- 纯文档或客户端工具变动：无需重建生产应用。
- 更新至新官方版本：验证镜像的 `org.opencontainers.image.revision` 与目标 tag 对应后，再更新锁文件及服务器 `.env`。
- 修改应用源码：从审核后的实验室提交构建自有镜像，记录 commit 和 digest；不能继续使用未包含改动的官方镜像。
- 数据库或 Redis 大版本更新另做迁移计划，不能直接替换镜像期待自动兼容。

上游 Release workflow 通过 `v*` tag 或手动操作触发，普通 Git 推送不会 SSH 部署当前 Droplet。不要在没有发布需求时触发镜像/二进制发布。CI 状态应与实际改动一起检查。

## 生产更新

1. 确认代码 PR 和目标镜像已审核；安排短维护窗口，避免配置修改和备份同时进行。
2. 暂停应用写入，创建加密逻辑备份并确认完整恢复验证通过，核对平台快照或另存的离线副本。
3. 保留原 `.env`、Compose 文件、镜像 digest 和固定 JWT/TOTP 密钥。
4. 显式更新目标镜像，使用 `sub2api-lab up` 加载主配置和 HTTPS overlay。
5. 核对四个容器、HTTPS、原管理员登录、原成员 Key 和一次 Codex 请求，再记录结果与创建新备份。

有 SQL 迁移时，旧程序不一定兼容新库。回退需要按运维文档恢复升级前逻辑备份，并考虑切换后产生的用户用量和 OAuth 状态。

## 提交范围

仓库保存代码、无密钥的配置模板和当前运维文档；运行目录、数据库、账号导出和历史机器取证资料不进入仓库。提交前显式检查暂存列表与差异，避免把凭据或数据一起推送。

## 2026-11-01 验证记录

实验室工具 CI 和 6 项备份完整性测试通过，应用源码与生产 `v0.2.18` 保持一致。继承的 [Security Scan](https://github.com/zhl-new-wave/sub2api/actions/runs/41286954007) 未通过：govulncheck 报告 `golang.org/x/net` 告警，前端 audit 报告 Vue I18n 相关包、`decode-uri-component` 和 `follow-redirects` 告警。

这些是当前基线的依赖扫描结果，本次没有升级应用依赖或生产镜像。后续应单独审查修复版本、生成依赖锁文件并验证，再安排生产更新；不要通过禁用扫描或新增宽泛例外消除失败状态。
