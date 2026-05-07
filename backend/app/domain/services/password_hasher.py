"""密码哈希工具 — sha256 + 随机 salt"""

import hashlib
import os


def hash_password(password: str) -> tuple[str, str]:
    """对密码进行哈希，返回 (hashed, salt)"""
    salt = os.urandom(32).hex()
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码是否匹配"""
    computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return computed == hashed
