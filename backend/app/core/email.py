"""邮件发送工具 — SMTP"""

import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str, html: bool = True) -> bool:
    """发送邮件

    环境变量配置:
        SMTP_HOST: SMTP 服务器地址（默认 smtp.qq.com）
        SMTP_PORT: SMTP 端口（默认 465）
        SMTP_USER: 发件邮箱
        SMTP_PASSWORD: 授权码
        MAIL_FROM: 发件人显示名称
    """
    smtp_host = getattr(settings, "smtp_host", "smtp.qq.com")
    smtp_port = getattr(settings, "smtp_port", 465)
    smtp_user = getattr(settings, "smtp_user", "")
    smtp_password = getattr(settings, "smtp_password", "")
    mail_from = getattr(settings, "mail_from", smtp_user)

    if not smtp_user or not smtp_password:
        logger.warning("SMTP 未配置，邮件发送跳过: %s", to_email)
        return False

    msg = MIMEText(body, "html" if html else "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(mail_from, [to_email], msg.as_string())
        logger.info("邮件发送成功: %s", to_email)
        return True
    except Exception as e:
        logger.error("邮件发送失败: %s, error=%s", to_email, e)
        return False
