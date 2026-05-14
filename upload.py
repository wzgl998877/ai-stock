"""
AI-Stock 一键部署脚本
用法: python upload.py
配置: deploy.conf
"""

import paramiko
import tarfile
import tempfile
import os
import sys
import io

CONF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.conf")


def load_conf():
    conf = {}
    with open(CONF_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, val = line.partition("=")
            conf[key.strip()] = val.strip()
    return conf


def main():
    if not os.path.exists(CONF_PATH):
        print(f"错误: 缺少 {CONF_PATH}")
        print("请复制 deploy.conf.example 并修改")
        sys.exit(1)

    conf = load_conf()
    remote = conf.get("REMOTE", "")
    deploy_dir = conf.get("DEPLOY_DIR", "/opt/ai-stock")
    password = conf.get("SSH_PASSWORD", "")

    if not remote:
        print("错误: 请在 deploy.conf 中配置 REMOTE")
        sys.exit(1)

    user, _, host = remote.partition("@")
    if not host:
        user, host = "root", user

    port = 22

    print("=" * 42)
    print("  AI-Stock 一键部署")
    print("=" * 42)
    print(f"目标: {remote}:{deploy_dir}")
    print(f"认证: {'密码' if password else 'SSH 密钥'}")
    print()

    # --- 1. 本地打包 ---
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("[1/3] 打包必要文件...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(os.path.join(base_dir, "backend", "app"), arcname="app")
        tar.add(os.path.join(base_dir, "backend", "requirements.txt"), arcname="requirements.txt")
        dist_dir = os.path.join(base_dir, "frontend", "dist")
        if not os.path.exists(dist_dir):
            print("错误: 前端未构建，请先运行 npm run build")
            sys.exit(1)
        tar.add(dist_dir, arcname="dist")
    buf.seek(0)
    size_mb = len(buf.getvalue()) / 1024 / 1024
    print(f"  打包完成: {size_mb:.1f} MB")

    # --- 2. 上传 ---
    print("[2/3] 上传到服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if password:
        ssh.connect(host, port=port, username=user, password=password)
    else:
        ssh.connect(host, port=port, username=user)

    sftp = ssh.open_sftp()

    # 直接通过 SFTP 写入，不落本地文件
    remote_tmp = "/tmp/ai-stock-deploy.tar.gz"
    sftp.putfo(buf, remote_tmp)
    print("  上传完成")

    # --- 3. 远程部署 ---
    print("[3/3] 远程部署...")
    commands = f"""
set -e
mkdir -p {deploy_dir}/{{app,dist,logs}}
tar -xzf {remote_tmp} -C {deploy_dir}
rm -f {remote_tmp}

cd {deploy_dir}
# 清理上次失败的 venv
if [ -d ".venv" ] && [ ! -f ".venv/bin/pip" ]; then
    rm -rf .venv
fi
if [ ! -d ".venv" ]; then
    apt-get update -qq && apt-get install -y -qq python3-venv python3-pip 2>/dev/null
    python3 -m venv .venv || echo "venv failed, using system pip"
fi
if [ -d ".venv" ] && [ -f ".venv/bin/pip" ]; then
    .venv/bin/pip install -r requirements.txt -q
else
    rm -rf .venv
    pip3 install -r requirements.txt -q --break-system-packages 2>/dev/null || pip3 install -r requirements.txt -q
fi

if [ ! -f /etc/systemd/system/ai-stock.service ]; then
    cat > /etc/systemd/system/ai-stock.service << 'EOF'
[Unit]
Description=AI-Stock Backend
After=network.target

[Service]
Type=simple
WorkingDirectory={deploy_dir}
ExecStart=/bin/bash -c '{deploy_dir}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 || uvicorn app.main:app --host 0.0.0.0 --port 8000'
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
"""

    stdin, stdout, stderr = ssh.exec_command(commands)
    exit_code = stdout.channel.recv_exit_status()

    # 实时输出
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out, end="")
    if err:
        print(err, end="")

    sftp.close()
    ssh.close()

    if exit_code != 0:
        print(f"\n部署失败 (exit code: {exit_code})")
        sys.exit(1)

    print()
    print("=" * 42)
    print("  部署完成")
    print("=" * 42)
    print(f"后端: http://{host}:8000")
    print(f"前端: {deploy_dir}/dist/  (需 Nginx 代理)")
    print("日志: journalctl -u ai-stock -f")


if __name__ == "__main__":
    main()
