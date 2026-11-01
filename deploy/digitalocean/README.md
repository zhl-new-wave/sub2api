# DigitalOcean 服务器运维

## 当前服务

应用位于新加坡 Droplet 的 `/opt/sub2api`，Compose 项目名为 `sub2api-lab`。

- 网页：<https://api.zhllabhub.com/login>
- API：`https://api.zhllabhub.com/v1`
- 主域名自动跳转到上述入口；HTTP 自动跳转 HTTPS。
- Sub2API v0.2.18、PostgreSQL 18、Redis 8、Caddy 2.11.7，核对后的 digest 在 `images.lock.json`。
- 当前应用直接连接上游。客户端网络、SSH 维护路径和异地备份接收端分别配置。

部分大陆网络曾出现入口连接超时；证书有效和海外可达不等于所有网络直连可用。先区分 TCP 连接、TLS 和应用响应，避免在网络故障时反复重置账号授权。

## 登录与常用命令

使用管理员已授权的 SSH Key。可在自己的 `~/.ssh/config` 添加：

```sshconfig
Host zhl-lab-do
    HostName api.zhllabhub.com
    User root
    IdentityFile ~/.ssh/your_lab_key
    IdentitiesOnly yes
```

密钥路径替换为自己的文件；不要分发同一把私钥。需要网络代理时由维护者在本机配置，仓库不固定中间跳板或个人代理。

```bash
ssh zhl-lab-do 'sub2api-lab status'
ssh zhl-lab-do 'sub2api-lab logs'
ssh zhl-lab-do 'sub2api-lab backup'
ssh zhl-lab-do 'sub2api-lab restart'
ssh zhl-lab-do 'systemctl list-timers --all sub2api-*'
ssh zhl-lab-do 'journalctl -u sub2api-backup.service -n 40 --no-pager'
ssh zhl-lab-do 'journalctl -u sub2api-health.service -n 40 --no-pager'
```

备用私有入口通过 SSH 建立，仅供隧道所在电脑使用：

```bash
ssh -N -T -L 127.0.0.1:28080:127.0.0.1:18080 zhl-lab-do
```

访问 `http://127.0.0.1:28080/login`；Codex 脚本传 `--base-url http://127.0.0.1:28080/v1`。已有同端口隧道时不要重复运行。

## 数据与配置

```text
/opt/sub2api/
  .env                      # 密码、固定 JWT/TOTP 密钥、镜像和域名，0600
  compose.yaml              # Sub2API + PostgreSQL + Redis
  compose.https.yaml        # Caddy 和受控代理网络
  .https-enabled            # 运维命令加载 HTTPS overlay 的标记
  data/app/                 # 应用运行文件和 config.yaml
  data/postgres/            # PostgreSQL 数据，PGDATA 为 18/docker
  data/redis/               # Redis AOF 与运行缓存
  data/caddy/               # HTTPS 证书和 ACME 状态
  data/caddy-config/         # Caddy 状态
  backups/                  # 加密备份与 last-success.json
  backup-recipient.txt      # age 公钥接收者，可供服务器加密
```

以上数据通过 bind mount 保存在宿主机，容器更新会继续使用。整机或磁盘故障仍需异地备份恢复；平台整机备份不替代 SQL 逻辑备份。用户、Key、余额、上游授权和调用记录主要保存在 PostgreSQL；Redis 是运行缓存，不应在迁移时盲目带入旧并发锁。

不要删除 `data/`，不要在现有实例运行 `initialize.py`，不要重新生成 JWT/TOTP 密钥。源码仓库不是运行数据备份。

## HTTPS 与网络

DNS 在腾讯云 DNSPod 管理：`api` 与 `@` 的 A 记录指向当前 Droplet IPv4，TTL 600 秒。换服务器时先核对控制台中的当前地址，避免复制历史 IP。没有 AAAA 或 CDN 代理。

服务器 `.env` 使用：

```dotenv
PUBLIC_HOST=api.zhllabhub.com
PUBLIC_APEX=zhllabhub.com
```

启用 `.https-enabled` 后，`sub2api-lab` 同时加载两份 Compose 文件。Caddy 发布 TCP 80/443，自动签发/续期证书；证书目录持久化并加入加密备份。腾讯云域名续费与 Caddy 证书续期是独立事项，负责人仍需检查域名账单和余额。

应用只发布 `127.0.0.1:18080`；PostgreSQL、Redis、Caddy 管理端口不向公网发布。独立 ingress 网段为 `172.28.80.0/29`：Caddy 为 `.2`、应用为 `.3`。应用只信任 Caddy `/32` 的代理地址，原始转发头兼容开关关闭。新主机先确认网段没有冲突。

资源限制：应用 768 MiB、Go 内存目标 640 MiB、PostgreSQL 384 MiB、Redis 128 MiB、Caddy 128 MiB。每服务 Docker 日志最多约 15 MiB。7–8 人容量取决于上游账号和并发，轻量验收不代表并发压测通过。

## 定时任务与监控

- Docker 和 Compose 栈开机启动，容器进程异常退出自动重启。
- 每 5 分钟检查四个容器、HTTP、HTTPS 验证和备份新鲜度。
- 失败写入 systemd 日志，当前没有邮件、短信或外部监控通知。
- Docker healthcheck 本身不会自动重启仍在运行的进程。
- 固定镜像 digest，不自动追踪 `latest`，不自动升级应用。

## 备份

每日北京时间 03:30（UTC 19:30，加至多 5 分钟随机延迟）生成逻辑备份：

1. `pg_dump -Fc`，在临时数据库完整执行 `pg_restore`。
2. 打包数据库、固定密钥、应用文件、Compose、运维脚本和 Caddy 状态。
3. 用 age 公钥加密后发布，记录大小、SHA256 和恢复验证结果。
4. 主机保留最近 30 个完成恢复点。另由独立接收端拉取异地副本。

**age 解密私钥仅由实验室维护者离线/密码库保管，不放在服务器、接收端或 Git。** 丢失私钥无法解密备份。生产现有 recipient 应保留；恢复前不要用新的公私钥对替换它。

检查 `backups/last-success.json`、systemd 日志及接收端 `last-success.json`。新主机需要安装 Docker、Python 3 和 age；`install-maintenance.sh` 仅在应用恢复及验证完成后启用定时任务。

### 通用异地接收端

`backup-pull.py` 可部署到维护者管理的 Linux/macOS 主机，不依赖固定中间主机。它使用独立只读 SSH Key，服务端强制命令只允许导出最新加密包。

在服务端为专用接收公钥设置类似的 `authorized_keys` 限制，保留已有其他行：

```text
restrict,command="/usr/local/sbin/sub2api-backup-export" ssh-ed25519 REPLACE_WITH_RECEIVER_PUBLIC_KEY backup-reader
```

预先通过可信渠道核对服务器 SSH host key，准备独立 known_hosts 和权限为 0600 的接收私钥，然后在接收端运行：

```bash
python3 backup-pull.py   --host root@api.zhllabhub.com   --identity /private/sub2api-backup-read-key   --known-hosts /private/sub2api-known-hosts   --directory /private/sub2api-backups
```

需要代理时可显式传 `--proxy-command`，默认使用直接连接。脚本验证包结构、备份时间、文件大小和 SHA256，最多保留 35 个恢复点。使用接收端自己的 scheduler 定时运行，并验证收取结果。现有生产接收任务单独管理；清理仓库不会停用它，更换接收端前应先验证替代副本。

## 恢复到新主机

先在新主机/空数据库恢复，已有实例先停写并备份，不要直接覆盖：

1. 在可信电脑用原 age 私钥解密选定 `.tar.age`，核对 `manifest.json` 的每个文件 SHA256。
2. 通过 SSH 传送 `configuration-and-app.tar.gz` 和 `database.dump` 到新主机私有目录。
3. 在 `/opt/sub2api`（0700）恢复配置 archive，保留原 `.env`（0600）、固定密钥和应用目录。数据库和 Redis 目录应为空。不要运行 `initialize.py`。
4. 暂时移开 `.https-enabled`，先只启动数据库和 Redis，再导入 SQL：

```bash
cd /opt/sub2api
docker compose up -d --wait postgres redis
docker compose exec -T postgres pg_restore -U sub2api --exit-on-error --no-owner --no-acl -d sub2api < /PRIVATE_RESTORE/database.dump
./labctl up
```

5. 对照备份的 `database-validation.json` 核对用户、账号、Key 和记录数，验证登录和模型请求；更改 DNS 后恢复 HTTPS 标记与 Caddy，再运行健康检查。
6. 核对 host key、SSH 管理授权、异地备份接收授权和 age 公钥，安装维护定时任务；旧实例保持停写，避免同时调度同一号池。

完整 SQL 恢复校验不等于整机灾备演练，新机器仍需重建操作系统、Docker 和访问控制。

## 新建独立实例

这段只适用于全新空目录，不能用来修复现有生产服务：

1. 将本目录的无凭据文件复制到新主机 `/opt/sub2api`，安装 Docker、Python 3 和 age。
2. 核对 `images.lock.json` 与 CPU 架构后运行 `python3 initialize.py --admin-email YOUR_ADMIN_EMAIL`。
3. 通过 SSH 私有入口启动并验证；账号持有人本人处理首次承诺和 OAuth 授权。
4. 配置域名、Caddy 和受控代理，生成离线保管的 age 密钥，仅将公钥写入 `backup-recipient.txt`。
5. 验证备份恢复和异地接收后运行 `install-maintenance.sh`，再创建成员与 Key。

镜像 digest 已核对的平台为 linux/amd64；其他架构需重新验证。应用接入新供应商时同步调整出站域名白名单。升级与回退见[维护指南](../../docs/lab-maintenance.md)。
