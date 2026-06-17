"""
注册中心客户端：publish / resolve / verify_remote
"""
from __future__ import annotations
from typing import Any


class NotarClient:
    def __init__(self, registry_url: str) -> None:
        # TODO: M2 实现
        self.registry_url = registry_url

    def publish(self, card: dict[str, Any]) -> dict[str, Any]:
        """向注册中心提交已签名的 agent card，返回注册结果。"""
        # TODO: M2 实现
        raise NotImplementedError

    def resolve(self, did: str) -> dict[str, Any]:
        """按 DID 从注册中心查询 agent card。"""
        # TODO: M2 实现
        raise NotImplementedError

    def verify_remote(self, did: str) -> bool:
        """向注册中心请求对指定 DID 的状态做在线验证（吊销检查等）。"""
        # TODO: M2 实现
        raise NotImplementedError
