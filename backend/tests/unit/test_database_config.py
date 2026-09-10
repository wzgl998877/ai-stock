"""core.database 引擎配置单测（2026-09-10 生产事故修复）。

校验方式：AST 解析 ``database.py`` 中 ``create_async_engine(...)`` 调用的关键字
参数——不真实建连（CI/本地无生产 MySQL 依赖），也不依赖 mock（from-import 的
名字重绑定会绕过 patch，见曾试过的 spy 方案）。
"""

import ast
from pathlib import Path

DB_MODULE = Path(__file__).resolve().parents[2] / "app" / "core" / "database.py"


def _engine_call_kwargs() -> dict:
    """提取 database.py 模块级 create_async_engine(...) 的关键字参数。"""
    tree = ast.parse(DB_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "create_async_engine"
        ):
            return {
                kw.arg: ast.literal_eval(kw.value)
                if isinstance(kw.value, ast.Constant)
                else ast.unparse(kw.value)
                for kw in node.keywords
            }
    return {}


def test_engine_has_connect_timeout():
    """engine 必须带 connect_args['connect_timeout']=10，防半开建连无限等。

    2026-09-10 事故：手动重算与定时扫描叠跑，池频繁新建连接，撞上无响应
    建连后协程永久悬死（无 TCP 建连超时）。此配置由 aiomysql 透传 pymysql。
    """
    kwargs = _engine_call_kwargs()
    assert "connect_args" in kwargs, "缺少 connect_args（建连超时未配置）"
    # connect_args 是 dict 字面量，ast.unparse 后为字符串表示：直接断言内容
    assert "connect_timeout" in str(kwargs["connect_args"])
    assert "10" in str(kwargs["connect_args"])


def test_pool_params_not_regressed():
    """池参数回归锚点：recycle 1800 / size 10 / overflow 20 不回退。"""
    kwargs = _engine_call_kwargs()
    assert kwargs.get("pool_recycle") == 1800
    assert kwargs.get("pool_size") == 10
    assert kwargs.get("max_overflow") == 20


def test_async_session_factory_exported():
    """模块导出 engine + async_session（装配完整性锚点）。"""
    import app.core.database as db_mod

    assert hasattr(db_mod, "engine")
    assert hasattr(db_mod, "async_session")
