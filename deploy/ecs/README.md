# 轻衡：阿里云 ECS 受限部署

适用：Ubuntu 22.04、个人使用、暂不增加应用登录。首次部署创建空数据库，不迁移本机历史。

访问路径：Windows 浏览器 → 本机 18080 → 加密 SSH 隧道 → ECS 本机 8080 → Nginx → FastAPI → PostgreSQL。
服务器仅发布 `127.0.0.1:8080`；后端和数据库不发布宿主机端口。容器内后端监听 `0.0.0.0` 是为了让 Nginx 容器连接，不代表对公网发布。

## 2026-09-22 已验证配置

- 云端项目和旧数据恢复已由用户验证成功，已有服务器无需重新初始化数据库。
- Python：`public.ecr.aws/docker/library/python:3.14-slim-bookworm`。
- Nginx：`public.ecr.aws/docker/library/nginx:stable-alpine`。
- PostgreSQL：`public.ecr.aws/docker/library/postgres:17-bookworm`。
- uv：`ghcr.io/astral-sh/uv:latest`。
- 照片识别、AI 建议、营养分析和搜索的默认模型均为 `qwen3.8-max-0902`。
- Docker 安装脚本默认使用本次成功的阿里云软件镜像源，可显式选择官方源。

这些是已验证的地址和配置，并非镜像内容的永久快照；版本系列标签和 latest 可能更新。本地包包含打包时的工作区代码，不能视为与已部署镜像逐字节一致。

## 1. 阿里云控制台

1. 启动 ECS，记录公网 IP，确认 SSH 用户名以及密码或私钥。
2. 在“网络与安全组”检查实例关联的所有安全组：仅允许你的公网 IPv4 地址 `/32` 访问 TCP 22。这里是你当前上网网络的公网 IP，不是电脑的 `192.168.x.x` 地址。
3. 不新增 80、443、8080、8001、5432、5173 的公网允许规则。如果已有全端口放行或网站端口放行，确认没有其他服务依赖后收紧。保留云控制台远程连接作为恢复入口。
4. 先添加你的 IP 并验证新 SSH 连接，再移除旧的广泛 SSH 放行规则，避免把自己锁在外面。
5. 上网公网 IP 改变后，需要更新 SSH 来源规则。

本方案只能从建立隧道的电脑访问。关闭隧道后，服务器仍运行，电脑浏览器暂时无法访问。无需域名、网站登录或 HTTPS 证书，跨公网的数据由 SSH 加密。

## 2. Windows 编译与上传

项目根目录 PowerShell 执行（需要现有 Node.js 和 npm 依赖）：

```powershell
cd C:\Users\32809\Desktop\Agents
powershell -ExecutionPolicy Bypass -File .\deploy\ecs\package.ps1
```

如果提示缺少前端依赖，先在 `Agent` 目录执行 `npm ci` 再打包。
输出 `deploy/qingheng-ecs-时间戳.tar.gz`，保留已有部署包。其中不包含实际 `.env`、Windows 虚拟环境、本机数据库或 node_modules。

将下列 `用户名`、`服务器公网IP` 替换成实际值：

```powershell
scp .\deploy\qingheng-ecs-实际时间戳.tar.gz 用户名@服务器公网IP:~/qingheng-ecs.tar.gz
ssh 用户名@服务器公网IP
```

使用私钥时，给 scp 和 ssh 加 `-i C:\路径\私钥文件`。首次连接应核对主机指纹，不要关闭主机密钥检查。

## 3. Ubuntu 解压与安装 Docker

以下命令在服务器 SSH 终端执行，使用有 sudo 权限的账号。首次部署使用新的 `~/qingheng` 目录。

```bash
mkdir -p ~/qingheng
tar -xzf ~/qingheng-ecs.tar.gz -C ~/qingheng
cd ~/qingheng/deploy/ecs
```

未安装 Docker 的新服务器：

```bash
bash install-docker-ubuntu.sh
```

脚本默认使用阿里云 Docker CE Ubuntu 软件镜像源，等同于 `bash install-docker-ubuntu.sh aliyun`。需要官方源时执行 `bash install-docker-ubuntu.sh official`。两种来源使用相同安装流程及 APT 签名校验；官方源在本次 ECS 上曾连接重置。

已有 Docker 时，先检查 `sudo docker version` 和 `sudo docker compose version`；两者可用则跳过安装，不要随意卸载服务器已有容器环境。软件安装源与容器镜像仓库是两回事，安装源切换不会自动解决镜像下载问题。

## 4. 首次配置

仅在首次部署执行以下初始化；后续更新保留现有 `.env` 和数据库密码。

```bash
cd ~/qingheng/deploy/ecs
umask 077
cp -n .env.example .env
chmod 600 .env
openssl rand -hex 24
nano .env
```

将生成的十六进制密码填入 `POSTGRES_PASSWORD=`，把百炼密钥填入 `DASHSCOPE_API_KEY=`。不要把密钥发送到聊天或提交到 Git。
四项模型默认均为 `qwen3.8-max-0902`，需确认你的百炼账户可调用且有可用额度；可按实际模型权限调整。nano 保存：Ctrl+O、回车；退出：Ctrl+X。
密码限制为十六进制字符，是为了避免数据库连接 URL 中的特殊字符转义问题。

首次启动后，PostgreSQL 会把密码和数据存入持久卷。修改 `.env` 中的密码不会自动修改已经初始化的数据库密码。

Compose 优先使用服务器 `.env`，修改模板或 Compose 默认值不会覆盖已有 `.env`。如需更改模型，在服务器 `.env` 修改 VISION_MODEL、ADVICE_MODEL、NUTRITION_REACT_MODEL、NUTRITION_SEARCH_MODEL 后执行：

```bash
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate --wait --wait-timeout 180 api
```

无需重建镜像；仅 restart 不会加载新的容器环境变量。不要把服务器真实 .env 下载进部署包，也不必修改 Windows 开发环境的 .env。

## 5. 构建并启动

```bash
sudo docker compose config --quiet
sudo docker compose --progress plain build
sudo docker compose up -d --wait --wait-timeout 180
sudo docker compose ps
curl --noproxy '*' -f http://127.0.0.1:8080/api/v1/health
```

最后应返回 `{"status":"ok"}`。首次构建需要下载镜像和 Python 依赖，时间取决于 ECS 网络；基础镜像来自 Amazon ECR Public，uv 来自 GHCR。本次 Python 依赖首次下载约 13 分钟，等待构建结束后再输入下一条命令。下载报错时检查错误中的目标仓库，不要通过开放更多入站端口解决。

如果日志还在访问 `registry-1.docker.io`，先核对是否使用旧包，以及 Dockerfile 和 compose.yaml 中的地址。可分别测试：

```bash
sudo docker pull public.ecr.aws/docker/library/nginx:stable-alpine
sudo docker pull public.ecr.aws/docker/library/python:3.14-slim-bookworm
sudo docker pull public.ecr.aws/docker/library/postgres:17-bookworm
sudo docker pull ghcr.io/astral-sh/uv:latest
```

服务设置 `restart: unless-stopped`，Docker 开机启动后恢复容器。数据库存放在 `qingheng_postgres_data` 持久卷。
镜像使用版本系列标签，uv 使用 latest；今后升级前备份并在验证后固定所用镜像 digest，避免无意变更运行环境。

## 6. Windows 开启访问隧道

另开一个 Windows PowerShell，执行：

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:18080:127.0.0.1:8080 用户名@服务器公网IP
```

认证后终端没有输出、持续等待是正常现象。保持该窗口打开，在浏览器访问：

http://127.0.0.1:18080

网页数据来自 ECS。按 Ctrl+C 关闭隧道。下一次访问只需重新执行隧道命令，不需要重新部署。

## 7. 验收

- `docker compose ps` 显示 db/api 健康、web 运行；Ports 只有 web 的 `127.0.0.1:8080->80/tcp` 宿主机映射。
- 建立隧道后，完成建档、手动记录、历史查询、照片识别、AI 建议和追问。
- 检查浏览器地址为 `127.0.0.1:18080`，没有误开本机开发端口 5173。
- 不通过隧道，从其他电脑或外部网络访问 `http://服务器公网IP:8080` 应失败。
- 关闭隧道后，本机刷新页面无法加载新的 API 数据；服务端容器仍保持运行。

## 日常操作

在服务器 `~/qingheng/deploy/ecs` 目录：

```bash
# 状态与最近日志（不要公开 .env 或完整配置）
sudo docker compose ps
sudo docker compose logs --tail 100 api
sudo docker compose logs --tail 100 web
sudo docker compose logs --tail 100 db

# 暂停与恢复
sudo docker compose stop
sudo docker compose start
```

首次使用前和每次升级前做数据库备份，并把备份复制到服务器之外：

```bash
umask 077
mkdir -p ~/qingheng-backups
backup_file="$HOME/qingheng-backups/qingheng-$(date +%Y%m%d-%H%M%S).dump"
sudo docker compose exec -T db pg_dump -U qingheng -d qingheng -Fc > "${backup_file:?请先设置备份路径}" && echo "数据库备份成功"
sudo docker compose exec -T db pg_restore --list < "${backup_file:?请先设置备份路径}"
```

不要执行 `docker compose down -v`，其中 `-v` 会删除数据库持久卷。

上述命令逐条执行。若要记录一个明确的更新前状态，可先 `sudo docker compose stop web api` 再备份，数据库保持运行。必须确认 pg_dump 成功；归档目录可读不等于完成了试恢复。

后续更新：先备份；本机重新打包上传；服务器解压到相同项目目录（包中无实际 .env），运行 `sudo docker compose build` 和 `sudo docker compose up -d --wait --wait-timeout 180`。如果删除或重命名后端文件，覆盖解压会留下旧文件，应改用新的发布目录并保留原配置；Compose 项目名固定为 qingheng，会继续使用同一个数据库卷。

更新前另外保留当前发布目录、服务器 .env 和旧镜像。新的发布目录必须复制现有 .env（限制为 600 权限），不要从模板生成新密码。更新完核对历史记录、照片识别、AI 建议和宿主机端口映射。数据库迁移可能影响旧代码兼容性；需要回退时配套恢复更新前的代码/镜像与数据库备份，不仅回退前端。

## 常见问题

- SSH 超时：实例是否运行、公网 IP 是否正确、安全组是否允许你现在的公网 IP、服务器 SSH 服务是否启动。
- `Address already in use`：本机 18080 已占用，可改为 18081，并使用对应浏览器地址。
- `administratively prohibited`：SSH 服务禁止 TCP 转发，需要允许该账号转发到 `127.0.0.1:8080`。
- 502：查看 api 日志和健康状态，检查数据库连接或迁移是否成功。
- AI 失败：检查百炼密钥、模型权限及出站网络；数据库和手动记录可以单独验证。
- `AllocationQuota.FreeTierOnly`：模型免费额度已耗尽/失效且启用用完即停。本次 qwen3.5-plus 曾因此返回 403，照片接口转为 503。核对实际运行模型、额度和计费设置；换模型不保证免费，也不要自动关闭费用保护。
- 构建被 Killed / 退出码 137：检查 `free -h` 与内核日志确认是否内存不足；停下其他不必要工作、增加内存，或在兼容 Linux 环境中预构建镜像。

## 参考

- Docker Ubuntu 安装：https://docs.docker.com/engine/install/ubuntu/
- Docker 本机端口发布：https://docs.docker.com/engine/network/port-publishing/
- uv 容器构建：https://docs.astral.sh/uv/guides/integration/docker/
- SSH 本地转发：https://man.openbsd.org/ssh
