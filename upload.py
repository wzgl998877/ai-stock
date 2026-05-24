"""
AI-Stock 一键部署脚本
用法: python upload.py
配置: deploy.conf
"""

import paramiko
import tarfile
import os
import sys
import io
import subprocess

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
    workers = conf.get("WORKERS", "1")

    if not remote:
        print("错误: 请在 deploy.conf 中配置 REMOTE")
        sys.exit(1)

    user, _, host = remote.partition("@")
    if not host:
        user, host = "root", user

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 检查 prod 配置文件
    backend_env_prod = os.path.join(base_dir, "backend", ".env.prod")
    if not os.path.exists(backend_env_prod):
        print("错误: 缺少 backend/.env.prod")
        sys.exit(1)
    frontend_env_prod = os.path.join(base_dir, "frontend", ".env.prod")
    if not os.path.exists(frontend_env_prod):
        print("错误: 缺少 frontend/.env.prod")
        sys.exit(1)

    # 从 .env.prod 读取服务端口
    app_port = 8000
    with open(backend_env_prod, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("PORT="):
                app_port = line.split("=", 1)[1].strip()

    print("=" * 42)
    print("  AI-Stock 一键部署")
    print("=" * 42)
    print(f"目标: {remote}:{deploy_dir}")
    print(f"端口: {app_port}")
    print(f"Workers: {workers}")
    print(f"认证: {'密码' if password else 'SSH 密钥'}")
    print()

    # --- 1. 构建前端 + 打包 ---
    print("[1/3] 构建前端...")
    frontend_dir = os.path.join(base_dir, "frontend")
    node_dir = os.path.join("D:", os.sep, "tool", "node")
    env = os.environ.copy()
    env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    ret = subprocess.call([npx_cmd, "vite", "build", "--mode", "prod"], cwd=frontend_dir, env=env)
    if ret != 0:
        print("错误: 前端构建失败")
        sys.exit(1)

    print("  打包必要文件...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(os.path.join(base_dir, "backend", "app"), arcname="app")
        tar.add(os.path.join(base_dir, "backend", "requirements.txt"), arcname="requirements.txt")
        tar.add(backend_env_prod, arcname=".env.prod")
        tar.add(os.path.join(base_dir, "frontend", "dist"), arcname="dist")
    buf.seek(0)
    size_mb = len(buf.getvalue()) / 1024 / 1024
    print(f"  打包完成: {size_mb:.1f} MB")

    # --- 2. 上传 ---
    print("[2/3] 上传到服务器...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if password:
        ssh.connect(host, port=22, username=user, password=password)
    else:
        ssh.connect(host, port=22, username=user)

    sftp = ssh.open_sftp()

    sftp.putfo(buf, "/tmp/ai-stock-deploy.tar.gz")

    # systemd 服务文件
    service_content = (
        "[Unit]\n"
        "Description=AI-Stock Backend\n"
        "After=network.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={deploy_dir}\n"
        f"ExecStart=/bin/bash -c '"
        f"{deploy_dir}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port {app_port} --workers {workers} "
        f"|| uvicorn app.main:app --host 0.0.0.0 --port {app_port} --workers {workers}'\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )
    sftp.putfo(io.BytesIO(service_content.encode()), "/tmp/ai-stock.service")

    print("  上传完成")

    # --- 3. 远程部署 ---
    print("[3/3] 远程部署...")
    commands = (
        f"set -e\n"
        f"mkdir -p {deploy_dir}/{{app,dist,logs}}\n"
        f"tar -xzf /tmp/ai-stock-deploy.tar.gz -C {deploy_dir}\n"
        f"rm -f /tmp/ai-stock-deploy.tar.gz\n"
        # .env.prod → .env（首次或更新）
        f"cp -n {deploy_dir}/.env.prod {deploy_dir}/.env 2>/dev/null || true\n"
        f"if [ ! -f {deploy_dir}/.env ]; then cp {deploy_dir}/.env.prod {deploy_dir}/.env; fi\n"
        f"\n"
        f"cd {deploy_dir}\n"
        f"if [ -d '.venv' ] && [ ! -f '.venv/bin/pip' ]; then rm -rf .venv; fi\n"
        f"if [ ! -d '.venv' ]; then\n"
        f"  apt-get update -qq && apt-get install -y -qq python3-venv python3-pip 2>/dev/null\n"
        f"  python3 -m venv .venv || echo 'venv failed, using system pip'\n"
        f"fi\n"
        f"if [ -d '.venv' ] && [ -f '.venv/bin/pip' ]; then\n"
        f"  .venv/bin/pip install -r requirements.txt -q\n"
        f"else\n"
        f"  rm -rf .venv\n"
        f"  pip3 install -r requirements.txt -q --break-system-packages 2>/dev/null || pip3 install -r requirements.txt -q\n"
        f"fi\n"
        f"\n"
        f"cp /tmp/ai-stock.service /etc/systemd/system/ai-stock.service\n"
        f"rm -f /tmp/ai-stock.service\n"
        f"systemctl daemon-reload\n"
        f"systemctl enable ai-stock\n"
        f"systemctl restart ai-stock\n"
    )

    stdin, stdout, stderr = ssh.exec_command(commands)
    exit_code = stdout.channel.recv_exit_status()

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
    print(f"后端: http://{host}:{app_port}")
    print(f"前端: http://{host}:{app_port}  (同端口，无需 Nginx)")
    print("日志: journalctl -u ai-stock -f")


if __name__ == "__main__":
    main()
