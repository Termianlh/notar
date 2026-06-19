"""
Minimal Notar-enabled demo agent.

Two of these — run by two *different* AI agents (e.g. Claude Code and Codex) —
verify each other's identity through Notar before trusting a message.

Each agent:
  - gets a Notar identity and registers its signed card to the live registry
  - listens on  POST /inbox   for messages from other agents
  - verifies every incoming sender's card BEFORE trusting it
  - is driven by its operator via  POST /control  ("send" / "forge")

Run it (it stays running and prints its DID):
    python examples/agent.py --name Alice --port 8001

Then, from the same machine, the operator drives it over HTTP:

    # send a verified message to a peer (you need the peer's DID):
    curl -s -X POST localhost:8001/control -H 'content-type: application/json' \
         -d '{"to":"<PEER_DID>","message":"hello"}'

    # try to impersonate someone (claim their DID, sign with your own key -> rejected):
    curl -s -X POST localhost:8001/control -H 'content-type: application/json' \
         -d '{"forge":"<VICTIM_DID>","to":"<PEER_DID>","message":"trust me"}'

    # ask an agent who it is:
    curl -s localhost:8001/whoami
"""
import argparse
import asyncio
import json
import os
from functools import partial

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response

from notar import create_identity, sign_card, verify_card, NotarClient

DEFAULT_REGISTRY = os.environ.get(
    "NOTAR_REGISTRY", "https://notar-registry.onrender.com"
)


def main() -> None:
    ap = argparse.ArgumentParser(description="A minimal Notar-enabled agent.")
    ap.add_argument("--name", required=True, help="display name, e.g. Alice")
    ap.add_argument("--port", type=int, required=True, help="local port to listen on")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = ap.parse_args()

    # --- identity + registration -------------------------------------------
    ident = create_identity()
    endpoint = f"http://127.0.0.1:{args.port}/inbox"
    my_card = sign_card(
        {"issuer": ident.did, "name": args.name, "endpoint": endpoint},
        ident.private_key,
    )

    nc = NotarClient(args.registry)
    print(f"\n[{args.name}] registering to {args.registry} ...", flush=True)
    print("[..] (first call may take ~30-60s if the free registry is waking up)", flush=True)
    nc.register(my_card)

    print(f"\n========== {args.name} is online ==========")
    print(f"DID:     {ident.did}")
    print(f"inbox:   {endpoint}")
    print(f"control: POST http://127.0.0.1:{args.port}/control")
    print(f">>> give your peer this DID so they can reach you <<<\n", flush=True)

    # --- server ------------------------------------------------------------
    app = FastAPI()

    def _safe_json(r):
        try:
            return r.json()
        except Exception:
            return r.text

    @app.get("/whoami")
    def whoami():
        return {"name": args.name, "did": ident.did}

    @app.post("/inbox")
    async def inbox(req: Request):
        body = await req.json()
        from_card = body.get("from_card", {})
        message = body.get("message", "")
        sender = from_card.get("name", "?")
        sender_did = from_card.get("issuer", "?")

        if verify_card(from_card):
            print(f"\n✅ VERIFIED message from {sender}  [{sender_did[:32]}…]")
            print(f'   "{message}"\n', flush=True)
            return {
                "status": "accepted",
                "reply": f"{args.name} here — I verified your identity via Notar. Message received.",
            }

        print(
            f"\n❌ REJECTED: sender claims to be {sender} [{sender_did[:32]}…] "
            f"but the signature does not match that identity.\n",
            flush=True,
        )
        return Response(
            status_code=403,
            media_type="application/json",
            content=json.dumps({"status": "rejected", "reason": "identity verification failed"}),
        )

    @app.post("/control")
    async def control(req: Request):
        body = await req.json()
        peer_did = body.get("to")
        message = body.get("message", "")
        forge_victim = body.get("forge")  # optional: a DID to impersonate

        if not peer_did:
            return {"ok": False, "error": "missing 'to' (peer DID)"}

        loop = asyncio.get_event_loop()

        # 1) discover + verify the peer through the registry (the trust path)
        try:
            peer = await loop.run_in_executor(None, partial(nc.get_agent, peer_did))
        except Exception as e:
            return {"ok": False, "error": f"peer not found in registry: {e}"}
        if not peer or not verify_card(peer):
            return {"ok": False, "error": "peer's own card failed verification"}

        # 2) build the card we'll present to the peer
        if forge_victim:
            try:
                victim_card = await loop.run_in_executor(None, partial(nc.get_agent, forge_victim))
                victim_name = victim_card.get("name", "someone") if victim_card else "someone"
            except Exception:
                victim_name = "someone"
            # forge: claim the victim's DID, but sign with OUR key -> must be rejected
            card_to_send = sign_card(
                {"issuer": forge_victim, "name": victim_name, "endpoint": endpoint},
                ident.private_key,
            )
            print(f"\n[operator] forging identity of {victim_name} "
                  f"[{forge_victim[:32]}…] toward {peer.get('name')}", flush=True)
        else:
            card_to_send = my_card
            print(f"\n[operator] sending a verified message to {peer.get('name')}", flush=True)

        # 3) deliver directly to the peer's endpoint (the data path)
        try:
            r = httpx.post(
                peer["endpoint"],
                json={"from_card": card_to_send, "message": message},
                timeout=15,
            )
            return {
                "ok": True,
                "peer": peer.get("name"),
                "http_status": r.status_code,
                "peer_response": _safe_json(r),
            }
        except Exception as e:
            return {"ok": False, "error": f"delivery failed: {e}"}

    uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning")
    ).run()


if __name__ == "__main__":
    main()
