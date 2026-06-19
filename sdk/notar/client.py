"""
注册中心客户端：register / get_agent / verify
同步公开接口，内部通过 anyio.run() 驱动 httpx.AsyncClient。
"""
from __future__ import annotations

from typing import Any

import anyio
import httpx


class NotarClient:
    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    def _run(self, coro_fn) -> Any:
        """在新事件循环里运行 async fn，返回结果。"""
        return anyio.run(coro_fn)

    def register(self, card: dict[str, Any]) -> dict[str, Any]:
        """POST /register — 提交已签名的 card。
        成功 → {"registered": True, "did": did}。
        422（验签失败）或其他非 2xx → raise httpx.HTTPStatusError。
        """
        async def _call():
            async with httpx.AsyncClient(
                transport=self._transport,
                base_url=self._base_url,
                timeout=self._timeout,
            ) as c:
                resp = await c.post("/register", json=card)
                resp.raise_for_status()
                return resp.json()

        return self._run(_call)

    def get_agent(self, did: str) -> dict[str, Any] | None:
        """GET /agents/{did} — 查询 DID 对应的 card。
        200 → card dict；404 → None；其他非 2xx → raise httpx.HTTPStatusError。
        """
        async def _call():
            async with httpx.AsyncClient(
                transport=self._transport,
                base_url=self._base_url,
                timeout=self._timeout,
            ) as c:
                resp = await c.get(f"/agents/{did}")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()

        return self._run(_call)

    def verify(self, card: dict[str, Any]) -> dict[str, Any]:
        """POST /verify — 在线验签 + 吊销检查。
        返回 {"valid": bool, "did": str, "status": str}。
        非 2xx → raise httpx.HTTPStatusError。
        """
        async def _call():
            async with httpx.AsyncClient(
                transport=self._transport,
                base_url=self._base_url,
                timeout=self._timeout,
            ) as c:
                resp = await c.post("/verify", json=card)
                resp.raise_for_status()
                return resp.json()

        return self._run(_call)
