# 携程 AI 助手 — K8s 生产部署操作手册

> **适用场景**: 三台空白 Linux 服务器（x86_64，Ubuntu 22.04 / CentOS 8+），从零搭建 K8s 集群并部署本项目。

---

## 目录

- [1. 三台服务器角色规划](#1-三台服务器角色规划)
- [2. 所有节点 — 基础环境安装](#2-所有节点--基础环境安装)
- [3. 所有节点 — 安装容器运行时 (containerd)](#3-所有节点--安装容器运行时-containerd)
- [4. 所有节点 — 安装 kubeadm / kubelet / kubectl](#4-所有节点--安装-kubeadm--kubelet--kubectl)
- [5. Master 节点 — 初始化 K8s 集群](#5-master-节点--初始化-k8s-集群)
- [6. Worker 节点 — 加入集群](#6-worker-节点--加入集群)
- [7. 集群组件安装 — Ingress Controller + Storage](#7-集群组件安装--ingress-controller--storage)
- [8. 构建 Docker 镜像并推送](#8-构建-docker-镜像并推送)
- [9. 修改项目配置](#9-修改项目配置)
- [10. 部署应用](#10-部署应用)
- [11. 验证部署](#11-验证部署)
- [12. 常见问题排查](#12-常见问题排查)

---

## 1. 三台服务器角色规划

| 角色 | 主机名 (建议) | IP (示例) | CPU | 内存 | 磁盘 | 用途 |
|------|-------------|-----------|-----|------|------|------|
| **Master** | `k8s-master` | 192.168.1.10 | 4C+ | 8G+ | 50G+ | 控制平面 + 可调度 Pod |
| **Worker-1** | `k8s-worker1` | 192.168.1.11 | 4C+ | 8G+ | 100G+ | 运行业务 Pod |
| **Worker-2** | `k8s-worker2` | 192.168.1.12 | 4C+ | 8G+ | 100G+ | 运行业务 Pod |

> **说明**: Master 节点默认不允许调度业务 Pod。如果你只有 3 台机器且想充分利用资源（推荐先用于 staging），在初始化的步骤中会包含取消污点的命令。

**本项目 K8s 资源需求汇总**（基于 staging overlay，单副本）:

| 组件 | CPU Request | Mem Request | 存储 |
|------|------------|-------------|------|
| FastAPI 后端 | 500m | 512Mi | — |
| Vue 前端 (Nginx) | 100m | 128Mi | — |
| MySQL 8.0 | 500m | 1Gi | 50Gi (PVC) |
| Redis 7 | 100m | 128Mi | — |
| **合计** | **~1.2 CPU** | **~1.8 Gi** | **50Gi** |

---

## 2. 所有节点 — 基础环境安装

**在每台服务器上**以 root 用户执行以下步骤。

### 2.1 设置主机名

```bash
# Master 节点
hostnamectl set-hostname k8s-master

# Worker-1 节点
hostnamectl set-hostname k8s-worker1

# Worker-2 节点
hostnamectl set-hostname k8s-worker2
```

### 2.2 配置 hosts 文件（所有节点）

```bash
cat >> /etc/hosts <<EOF
192.168.1.10  k8s-master
192.168.1.11  k8s-worker1
192.168.1.12  k8s-worker2
EOF
```

> **注意**: 将 IP 替换为你的实际服务器 IP。

### 2.3 关闭 swap

Kubernetes 要求关闭 swap。

```bash
swapoff -a
sed -i '/swap/d' /etc/fstab
```

### 2.4 配置内核参数

```bash
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system
```

### 2.5 验证基础环境

```bash
# 确认 swap 已关闭（应返回空）
swapon --show

# 确认内核模块已加载
lsmod | grep br_netfilter
lsmod | grep overlay

# 确认网络转发已开启
sysctl net.bridge.bridge-nf-call-iptables net.ipv4.ip_forward
```

---

## 3. 所有节点 — 安装容器运行时 (containerd)

Kubernetes 1.24+ 不再直接支持 Docker，使用 containerd 作为容器运行时。

### 3.1 安装 containerd（Ubuntu）

```bash
apt-get update
apt-get install -y containerd
```

**CentOS/RHEL/Rocky**:

```bash
dnf install -y containerd
```

### 3.2 生成默认配置并启用 SystemdCgroup

```bash
mkdir -p /etc/containerd
containerd config default > /etc/containerd/config.toml
```

**关键修改**: 将 `SystemdCgroup` 改为 `true`，否则 kubelet 会报 cgroup 错误。

```bash
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
```

### 3.3 启动 containerd

```bash
systemctl restart containerd
systemctl enable containerd
```

### 3.4 验证 containerd

```bash
# 确认运行中
systemctl status containerd

# 确认可以拉取镜像
crictl pull nginx:alpine
crictl images | grep nginx
```

---

## 4. 所有节点 — 安装 kubeadm / kubelet / kubectl

### 4.1 添加 Kubernetes APT/YUM 仓库

**Ubuntu/Debian**:

```bash
apt-get install -y apt-transport-https ca-certificates curl gpg

# 添加 K8s 官方 GPG key
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | \
    gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | \
    tee /etc/apt/sources.list.d/kubernetes.list
```

> 版本说明: 本文档使用 **Kubernetes v1.30**（截至 2024 年稳定版本）。如需其他版本，修改 URL 中的 `v1.30`。

**CentOS/RHEL/Rocky**:

```bash
cat <<EOF | tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/repodata/repomd.xml.key
EOF
```

### 4.2 安装

```bash
# Ubuntu
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl   # 防止自动更新导致版本不一致

# CentOS
dnf install -y kubelet kubeadm kubectl
```

### 4.3 启动 kubelet

```bash
systemctl enable kubelet
# 注意: kubelet 在 kubeadm init 完成前会处于 CrashLoopBackOff，
# 这是正常的，等集群初始化完成即可。
```

### 4.4 验证安装

```bash
kubeadm version
kubelet --version
kubectl version --client
```

---

## 5. Master 节点 — 初始化 K8s 集群

> **仅在 Master 节点执行！**

### 5.1 初始化控制平面

```bash
# 将 192.168.1.10 替换为你的 Master 节点真实 IP
# --pod-network-cidr 用于 Calico 网络插件，不要修改
kubeadm init \
  --control-plane-endpoint "192.168.1.10:6443" \
  --apiserver-advertise-address 192.168.1.10 \
  --pod-network-cidr=10.244.0.0/16 \
  --upload-certs
```

**输出关键信息**: 初始化成功后会输出一段 `kubeadm join ...` 的命令，**请完整复制保存**，后续 Worker 节点需要用到。

示例输出:
```
kubeadm join 192.168.1.10:6443 --token abcdef.0123456789abcdef \
    --discovery-token-ca-cert-hash sha256:xxxxx...
```

### 5.2 配置 kubectl

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### 5.3 安装 Pod 网络插件 (Calico)

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28/manifests/calico.yaml
```

> 如果下载失败（网络原因），可先 `wget` 下载到本地再 apply。

### 5.4 让 Master 节点也调度 Pod（可选，推荐用于三节点小集群）

```bash
# 取消 Master 节点的污点，允许业务 Pod 调度到 Master
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

### 5.5 验证集群初始化

```bash
# 查看节点状态（应该看到 master 节点，状态 Ready）
kubectl get nodes

# 查看所有系统 Pods（都应该是 Running 状态）
kubectl get pods -A
```

---

## 6. Worker 节点 — 加入集群

> **在每台 Worker 节点执行！**

### 6.1 执行 join 命令

使用 Master 初始化时输出的 `kubeadm join` 命令:

```bash
kubeadm join 192.168.1.10:6443 --token abcdef.0123456789abcdef \
    --discovery-token-ca-cert-hash sha256:xxxxx...
```

### 6.2 如果忘记 token

在 Master 节点重新生成:

```bash
# 创建新 token
kubeadm token create --print-join-command
```

### 6.3 验证集群

回到 Master 节点:

```bash
# 应看到 3 个节点，状态都为 Ready
kubectl get nodes

# 示例输出:
# NAME          STATUS   ROLES           AGE   VERSION
# k8s-master    Ready    control-plane   5m    v1.30.x
# k8s-worker1   Ready    <none>          2m    v1.30.x
# k8s-worker2   Ready    <none>          2m    v1.30.x

# 查看所有 Pods（包括 Calico 网络组件）
kubectl get pods -A
```

---

## 7. 集群组件安装 — Ingress Controller + Storage

### 7.1 安装 Nginx Ingress Controller

本项目使用 Nginx Ingress Controller 做外部流量入口:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.0/deploy/static/provider/cloud/deploy.yaml
```

**验证 Ingress Controller**:

```bash
# 等待 ingress-nginx pod 运行（可能需要 1-2 分钟拉取镜像）
kubectl get pods -n ingress-nginx -w

# 确认 Service 已获得外部 IP（NodePort/LoadBalancer）
kubectl get svc -n ingress-nginx
```

### 7.2 配置存储类 (StorageClass)

MySQL StatefulSet 需要 PersistentVolume。在三节点集群中，推荐使用 **local-path-provisioner**（轻量）:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml
```

**验证存储类**:

```bash
kubectl get storageclass

# 示例输出:
# NAME         PROVISIONER        RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION
# local-path   rancher.io/local-path   Delete    WaitForFirstConsumer   false
```

### 7.3 （可选）安装 metrics-server（HPA 需要）

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

**验证**:

```bash
# 等 30 秒后查看（应看到 CPU/Memory 数据）
kubectl top nodes
```

---

## 8. 构建 Docker 镜像并推送

项目需要在**有 Docker 环境的机器上**（可以是你的开发机或 Master 节点）构建镜像。

### 8.1 安装 Docker（在构建机器上）

如果你的构建机器还没有 Docker:

```bash
# Ubuntu
curl -fsSL https://get.docker.com | bash

# CentOS
dnf install -y docker
systemctl start docker
```

### 8.2 构建镜像

在项目根目录（`clever-meadow/`）执行:

```bash
# 构建后端镜像 (FastAPI)
docker build -t ctrip/app:latest -f k8s/Dockerfile.app .

# 构建前端镜像 (Vue SPA + Nginx)
docker build -t ctrip/frontend:latest -f k8s/Dockerfile.frontend .

# 验证镜像
docker images | grep ctrip
```

### 8.3 分发镜像到各节点（三选一）

#### 方案 A: 推送到私有 Registry（推荐）

```bash
# 1. 在所有 K8s 节点安装 Docker 并搭建 Registry（在 Master 节点）
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# 2. 打标签并推送
docker tag ctrip/app:latest 192.168.1.10:5000/ctrip/app:latest
docker tag ctrip/frontend:latest 192.168.1.10:5000/ctrip/frontend:latest
docker push 192.168.1.10:5000/ctrip/app:latest
docker push 192.168.1.10:5000/ctrip/frontend:latest
```

> **注意**: Containerd 默认不信任非 HTTPS 的 Registry。需要在每个节点 `/etc/containerd/config.toml` 中添加:
>
> ```toml
> [plugins."io.containerd.grpc.v1.cri".registry.mirrors."192.168.1.10:5000"]
>   endpoint = ["http://192.168.1.10:5000"]
> ```
>
> 然后 `systemctl restart containerd`。

#### 方案 B: 手动导出/导入（离线环境）

```bash
# 在构建机器导出
docker save ctrip/app:latest -o ctrip-app.tar
docker save ctrip/frontend:latest -o ctrip-frontend.tar
# 复制到所有 Worker 节点，然后导入
scp ctrip-app.tar ctrip-frontend.tar root@k8s-worker1:/tmp/
scp ctrip-app.tar ctrip-frontend.tar root@k8s-worker2:/tmp/

# 在每个 Worker 节点导入
ctr -n k8s.io images import /tmp/ctrip-app.tar
ctr -n k8s.io images import /tmp/ctrip-frontend.tar
```

#### 方案 C: 使用阿里云/腾讯云容器镜像服务

```bash
# 登录
docker login --username=yourname registry.cn-hangzhou.aliyuncs.com

# 打标签并推送
docker tag ctrip/app:latest registry.cn-hangzhou.aliyuncs.com/your-namespace/ctrip-app:latest
docker push registry.cn-hangzhou.aliyuncs.com/your-namespace/ctrip-app:latest
```

---

## 9. 修改项目配置

部署前**必须修改**以下文件，替换占位符为真实值。

### 9.1 修改 Secret（⚠️ 最关键）

编辑 `k8s/base/secret.yaml`:

```yaml
stringData:
  # ── 数据库 ──
  # 格式: mysql+aiomysql://用户名:密码@mysql:3306/数据库名
  DATABASE_URL: "mysql+aiomysql://ctrip:你的MySQL密码@mysql:3306/ctrip_assistant"

  # ── JWT 签名密钥（64 个十六进制字符）──
  # 生成方式: python -c "import secrets; print(secrets.token_hex(32))"
  JWT_SECRET_KEY: "a1b2c3d4e5f6...（替换为 64 位 hex）"

  # ── LLM API Key ──
  # 替换为你的 DeepSeek 或 OpenAI API Key
  LLM_API_KEY: "sk-你的真实Key"

  # ── Embedding API Key ──
  EMBEDDING_API_KEY: "sk-你的真实Key"

  # ── MySQL Root 密码（StatefulSet 初始化用）──
  MYSQL_ROOT_PASSWORD: "你的MySQL Root密码"
```

> **安全提醒**: 不要将真实 Secret 提交到 Git！生产环境建议使用 SealedSecrets 或 External Secrets Operator。测试环境可用 `kubectl create secret generic` 手动管理。

### 9.2 修改 ConfigMap（按需）

编辑 `k8s/base/configmap.yaml`:

```yaml
data:
  # LLM 提供商: "deepseek" 或 "openai"
  LLM_PROVIDER: "deepseek"
  LLM_MODEL: "deepseek-chat"
  LLM_API_BASE: "https://api.deepseek.com/v1"

  # CORS — 添加你的实际访问域名
  CORS_ORIGINS: '["http://你的域名","https://你的域名"]'
```

### 9.3 修改 Ingress hostname

**Staging** — 编辑 `k8s/overlays/staging/ingress-patch.yaml`:

```yaml
spec:
  rules:
    - host: staging.你的域名.com   # 修改这里
```

**Production** — 编辑 `k8s/overlays/production/ingress-patch.yaml`:

```yaml
spec:
  tls:
    - hosts:
        - 你的生产域名.com
      secretName: ctrip-tls
  rules:
    - host: 你的生产域名.com      # 修改这里
```

### 9.4 修改 MySQL StatefulSet 的密码注入（BUG 修复）

`k8s/base/mysql-statefulset.yaml` 第 53-56 行有一个 bug：`MYSQL_PASSWORD` 使用了整个 `DATABASE_URL` 作为值，这是错误的。需要修复:

```bash
# 将所有节点的 Secret 中 MYSQL_PASSWORD 单独定义，然后修改 StatefulSet：

# 方式 1: 添加一个独立的 MYSQL_USER_PASSWORD 到 secret.yaml
# 方式 2: 直接修改 mysql-statefulset.yaml 的 env 部分
```

编辑 `k8s/base/secret.yaml`，在 `stringData` 中添加:

```yaml
  # MySQL 业务用户密码（需与 DATABASE_URL 中一致）
  MYSQL_USER_PASSWORD: "你的MySQL用户密码"
```

编辑 `k8s/base/mysql-statefulset.yaml`，找到第 53-56 行，将:

```yaml
            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ctrip-assistant-secret
                  key: DATABASE_URL
```

改为:

```yaml
            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ctrip-assistant-secret
                  key: MYSQL_USER_PASSWORD
```

### 9.5 修改镜像地址（如果用私有 Registry）

如果用私有 Registry（方案 A），需要修改 overlay 中的 `images` 部分。

**Staging** — `k8s/overlays/staging/kustomization.yaml`:

```yaml
images:
  - name: ctrip/app
    newTag: latest
    newName: 192.168.1.10:5000/ctrip/app    # 添加这行
  - name: ctrip/frontend
    newTag: latest
    newName: 192.168.1.10:5000/ctrip/frontend  # 添加这行
```

**Production** 同理修改 `k8s/overlays/production/kustomization.yaml`。

### 9.6 修改 replicas / resources（按需）

三台节点的小集群如果资源紧张，可以降低副本数。编辑 `k8s/base/app-deployment.yaml`:

```yaml
spec:
  replicas: 1    # 从 3 降到 1
  ...
          resources:
            requests:
              cpu: 250m       # 从 500m 降低
              memory: 256Mi   # 从 512Mi 降低
```

### 9.7 检查清单

| 修改项 | 文件 | 状态 |
|--------|------|------|
| Secret 真实值 | `k8s/base/secret.yaml` | ⬜ |
| ConfigMap 配置 | `k8s/base/configmap.yaml` | ⬜ |
| Ingress 域名 | `k8s/overlays/*/ingress-patch.yaml` | ⬜ |
| MySQL 密码 BUG | `k8s/base/mysql-statefulset.yaml` + `secret.yaml` | ⬜ |
| 镜像 Registry 地址 | `k8s/overlays/*/kustomization.yaml` | ⬜ |
| 资源限制（按需） | `k8s/base/*-deployment.yaml` | ⬜ |

---

## 10. 部署应用

### 10.1 快速部署 (staging 推荐首次使用)

```bash
# 进入 k8s 目录
cd k8s

# 先做一次 dry-run 预览（不会实际部署）
kubectl apply -k overlays/staging --dry-run=client

# 实际部署
kubectl apply -k overlays/staging
```

### 10.2 使用部署脚本

```bash
cd k8s

# 部署 staging（不运行数据库迁移）
bash deploy.sh staging

# 部署 staging + 运行数据库迁移（首次部署推荐）
bash deploy.sh staging:migrate
```

### 10.3 手动数据库迁移

如果部署脚本跳过迁移，可手动执行:

```bash
# 找到后端 Pod
kubectl get pods -n ctrip-assistant -l app.kubernetes.io/component=backend

# 执行迁移
kubectl exec -n ctrip-assistant <backend-pod-name> -- alembic upgrade head
```

### 10.4 部署到 production

```bash
cd k8s
bash deploy.sh production:migrate
```

### 10.5 查看部署状态

```bash
# 查看所有资源
kubectl get all -n ctrip-assistant

# 查看 Pod 状态
kubectl get pods -n ctrip-assistant -o wide

# 实时查看 Pod 启动日志
kubectl logs -f -n ctrip-assistant -l app.kubernetes.io/component=backend

# 查看 Ingress
kubectl get ingress -n ctrip-assistant
```

---

## 11. 验证部署

### 11.1 确认所有 Pod 运行正常

```bash
kubectl get pods -n ctrip-assistant
```

预期输出:

```
NAME                                READY   STATUS    RESTARTS   AGE
ctrip-app-backend-xxxxxxxxx-xxxxx   1/1     Running   0          5m
ctrip-frontend-xxxxxxxxx-xxxxx      1/1     Running   0          5m
mysql-0                             1/1     Running   0          5m
redis-xxxxxxxxx-xxxxx               1/1     Running   0          5m
```

### 11.2 确认 Service 可用

```bash
kubectl get svc -n ctrip-assistant
```

预期输出:

```
NAME                 TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)
ctrip-app-backend    ClusterIP   10.xx.xx.xx     <none>        8000/TCP
ctrip-frontend       ClusterIP   10.xx.xx.xx     <none>        80/TCP
mysql-headless       ClusterIP   None            <none>        3306/TCP
redis                ClusterIP   10.xx.xx.xx     <none>        6379/TCP
```

### 11.3 确认 Ingress 生效

```bash
kubectl get ingress -n ctrip-assistant
```

预期看到 Ingress 的 ADDRESS 字段不为空。

### 11.4 通过端口转发测试后端（无需外部 DNS）

```bash
# 将后端端口转发到本地 8000
kubectl port-forward -n ctrip-assistant svc/ctrip-app-backend 8000:8000

# 健康检查（另一个终端）
curl http://localhost:8000/api/v1/health

# 预期返回: {"status": "healthy", "version": "1.0.0"}
```

### 11.5 通过端口转发测试前端

```bash
kubectl port-forward -n ctrip-assistant svc/ctrip-frontend 8080:80
```

浏览器访问 `http://localhost:8080` 应看到登录页面。

### 11.6 通过 Ingress 测试（需配置 DNS）

将域名（如 `staging.你的域名.com`）解析到 Ingress Controller 的外部 IP。

**查看 Ingress IP**:

```bash
kubectl get svc -n ingress-nginx

# 如果使用 NodePort，查看任意节点的 IP + NodePort
kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.port==80)].nodePort}'
```

然后测试:

```bash
# 健康检查
curl http://staging.你的域名.com/api/v1/health

# 登录测试
curl -X POST http://staging.你的域名.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test123456","email":"test@test.com"}'

# 对话测试（需要先用上面返回的 token）
curl -X POST http://staging.你的域名.com/api/v1/graph/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_input":"你好，帮我规划一次旅行"}'
```

---

## 12. 常见问题排查

### 12.1 Pod 一直 Pending

```bash
kubectl describe pod -n ctrip-assistant <pod-name>
```

**常见原因**:
- **资源不足**: 节点 CPU/内存不够，降低 requests 或增加节点
- **PVC 无法绑定**: 没有可用的 StorageClass，确认第 7.2 步已完成
- **镜像拉取失败**: 检查镜像地址和 Registry 配置

### 12.2 MySQL Pod 启动失败

```bash
kubectl logs -n ctrip-assistant mysql-0
```

**常见原因**:
- `MYSQL_PASSWORD` 环境变量使用了 `DATABASE_URL` 作为值（参考第 9.4 节修复）
- PVC 创建失败（确认 StorageClass 已安装）

### 12.3 后端 Pod CrashLoopBackOff

```bash
kubectl logs -n ctrip-assistant -l app.kubernetes.io/component=backend --tail=50
```

**常见原因**:
- 数据库连接失败（检查 `DATABASE_URL` 在 Secret 中的值是否正确）
- LLM API Key 无效
- JWT_SECRET_KEY 格式错误

### 12.4 SSE 流式响应不工作

- 确认 `k8s/base/ingress.yaml` 中包含 `nginx.ingress.kubernetes.io/proxy-buffering: "off"`
- 确认 `proxy-read-timeout` 至少 300 秒

### 12.5 kubeadm init 失败

```bash
kubeadm reset   # 清理后重试
kubeadm init ...
```

### 12.6 Token 过期（Worker 无法加入）

在 Master 节点:

```bash
kubeadm token create --print-join-command
```

### 12.7 重新部署

```bash
# 强制重新拉取镜像
kubectl rollout restart deployment/ctrip-app-backend -n ctrip-assistant
kubectl rollout restart deployment/ctrip-frontend -n ctrip-assistant

# 或完整重建
kubectl delete ns ctrip-assistant
kubectl apply -k k8s/overlays/staging
```

---

## 附录 A: 快速命令速查表

| 操作 | 命令 |
|------|------|
| 查看节点 | `kubectl get nodes` |
| 查看所有 Pods | `kubectl get pods -n ctrip-assistant` |
| 查看 Pod 日志 | `kubectl logs -f -n ctrip-assistant <pod-name>` |
| 进入容器 | `kubectl exec -it -n ctrip-assistant <pod-name> -- bash` |
| 端口转发 | `kubectl port-forward -n ctrip-assistant svc/ctrip-app-backend 8000:8000` |
| 重启部署 | `kubectl rollout restart deploy/ctrip-app-backend -n ctrip-assistant` |
| 删除命名空间 | `kubectl delete ns ctrip-assistant` |
| 查看事件 | `kubectl get events -n ctrip-assistant --sort-by=.metadata.creationTimestamp` |
| 查看资源使用 | `kubectl top pods -n ctrip-assistant` |
| 查看 PVC | `kubectl get pvc -n ctrip-assistant` |

## 附录 B: 项目文件修改速查

部署前需要修改的所有文件:

| # | 文件 | 修改内容 |
|---|------|---------|
| 1 | `k8s/base/secret.yaml` | 填入真实 JWT/LLM/DB 密码 |
| 2 | `k8s/base/configmap.yaml` | 确认 LLM Provider 和 CORS 域名 |
| 3 | `k8s/overlays/staging/ingress-patch.yaml` | 修改 hostname |
| 4 | `k8s/overlays/production/ingress-patch.yaml` | 修改 hostname + TLS |
| 5 | `k8s/base/mysql-statefulset.yaml` | 修复 MYSQL_PASSWORD 引用 |
| 6 | `k8s/base/secret.yaml` | 添加 MYSQL_USER_PASSWORD |
| 7 | `k8s/overlays/*/kustomization.yaml` | 镜像 registry 地址（如需要）|
| 8 | `k8s/base/app-deployment.yaml` | replicas/resources（按需调整）|
