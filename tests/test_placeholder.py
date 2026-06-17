"""占位测试：确认 pytest 基础设施可用。M1 起逐步替换为真实测试。"""


def test_scaffold_in_place():
    """骨架已搭好，所有占位函数在被调用前应抛 NotImplementedError。"""
    from notar.identity import create_identity

    try:
        create_identity()
        assert False, "应该抛 NotImplementedError"
    except NotImplementedError:
        pass  # 符合预期
