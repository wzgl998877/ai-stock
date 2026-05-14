#!/bin/bash
set -e

# ============================================================
#  AI-Stock 一键部署脚本
#  配置文件: deploy.conf（同目录下）
#  用法: ./deploy.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="${SCRIPT_DIR}/deploy.conf"

if [ ! -f "${CONF}" ]; then
    echo "错误: 缺少 ${CONF}"
    echo "请复制 deploy.conf.example 并修改"
    exit 1
fi

source "${CONF}"

REMOTE="${REMOTE:?请在 deploy.conf 中配置 REMOTE}"
DEPLOY_DIR="${DEPLOY_DIR:?请在 deploy.conf 中配置 DEPLOY_DIR}"

# SSH 认证：有密码用 sshpass，否则走密钥
SSH_CMD="ssh"
SCP_CMD="scp"
if [ -n "${SSH_PASSWORD}" ]; then
    if ! command -v sshpass &>/dev/null; then
        echo "错误: 使用密码登录需要 sshpass，请先安装："
        echo "  Ubuntu/Debian: apt install sshpass"
        echo "  CentOS:        yum install sshpass"
        echo "  macOS:         brew install sshpass"
        echo ""
        echo "或使用 SSH 密钥认证（推荐）：将 deploy.conf 中 SSH_PASSWORD 留空"
        exit 1
    fi
    SSH_CMD="sshpass -p ${SSH_PASSWORD} ssh -o StrictHostKeyChecking=no"
    SCP_CMD="sshpass -p ${SSH_PASSWORD} scp -o StrictHostKeyChecking=no"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PKG_NAME="ai-stock-${TIMESTAMP}.tar.gz"
TMP_DIR="${SCRIPT_DIR}/.deploy_tmp_${TIMESTAMP}"

echo "=========================================="
echo "  AI-Stock 一键部署"
echo "=========================================="
echo "目标: ${REMOTE}:${DEPLOY_DIR}"
echo "认证: $([ -n "${SSH_PASSWORD}" ] && echo "密码" || echo "SSH 密钥")"
echo ""

# --------------------------------------------------
# 1. 本地打包
# --------------------------------------------------
echo "[1/4] 构建前端..."
(cd "${SCRIPT_DIR}/frontend" && npm run build)

echo "[1/4] 打包必要文件..."
rm -rf "${TMP_DIR}"
mkdir -p "${TMP_DIR}"

cp -r "${SCRIPT_DIR}/backend/app"              "${TMP_DIR}/app"
cp    "${SCRIPT_DIR}/backend/requirements.txt"  "${TMP_DIR}/"
mkdir -p "${TMP_DIR}/dist"
cp -r "${SCRIPT_DIR}/frontend/dist/"*          "${TMP_DIR}/dist/"

# --------------------------------------------------
# 2. 压缩
# --------------------------------------------------
echo "[2/4] 压缩: ${PKG_NAME}"
tar -czf "${SCRIPT_DIR}/${PKG_NAME}" -C "${TMP_DIR}" .
rm -rf "${TMP_DIR}"

# --------------------------------------------------
# 3. 上传并部署
# --------------------------------------------------
echo "[3/4] 上传到 ${REMOTE}..."
${SCP_CMD} "${SCRIPT_DIR}/${PKG_NAME}" "${REMOTE}:/tmp/"

echo "[4/4] 远程部署..."
${SSH_CMD} "${REMOTE}" bash -s "${DEPLOY_DIR}" "${PKG_NAME}" << 'SSH_EXEC'
set -e
DEPLOY_DIR="$1"
PKG_NAME="$2"

mkdir -p "${DEPLOY_DIR}"/{app,dist,logs}
cd /tmp
tar -xzf "${PKG_NAME}" -C "${DEPLOY_DIR}"
rm -f "${PKG_NAME}"

cd "${DEPLOY_DIR}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt -q

if [ ! -f /etc/systemd/system/ai-stock.service ]; then
    cat > /etc/systemd/system/ai-stock.service << EOF
[Unit]
Description=AI-Stock Backend
After=network.target

[Service]
Type=simple
WorkingDirectory=${DEPLOY_DIR}
ExecStart=${DEPLOY_DIR}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable ai-stock
fi

systemctl restart ai-stock

echo ""
echo "=========================================="
echo "  部署完成"
echo "=========================================="
echo "后端: http://<IP>:8000"
echo "前端: ${DEPLOY_DIR}/dist/  (需 Nginx 代理)"
echo "日志: journalctl -u ai-stock -f"
SSH_EXEC

rm -f "${SCRIPT_DIR}/${PKG_NAME}"
echo ""
echo "✅ 部署完成！"
