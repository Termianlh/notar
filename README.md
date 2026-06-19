# Notar

**Verifiable identity for AI agents.** A neutral, open-source layer that lets an agent prove who it is — and verify others aren't impostors — in a few lines of Python.

<!-- badges (add once published): pip version · license · tests -->

## Why

AI agents are starting to act on our behalf — booking, negotiating, transacting with *other people's* agents. That raises one unavoidable question: **is this agent who it claims to be?**

Notar gives every agent a cryptographic identity and a tamper-proof "agent card," so a stranger's agent can be verified *before* you trust it. Built on standard crypto (Ed25519 + W3C `did:key`), not tied to any framework, and verifiable **offline** — no server needed to check a signature.

## Quickstart

```bash
# from source (PyPI release coming)
git clone https://github.com/Termianlh/notar
cd notar
pip install -e .
```

```python
from notar import create_identity, sign_card, verify_card

# 1. Give your agent a verifiable identity
ident = create_identity()
print(ident.did)          # did:key:z6Mk...

# 2. Sign an agent card — your agent's "business card"
card = sign_card({
    "issuer": ident.did,
    "name": "Alice",
    "capabilities": ["booking"],
    "endpoint": "https://alice.example.com/a2a",
}, ident.private_key)

# 3. Anyone can verify it — offline, no server
verify_card(card)         # True

# 4. Tamper with it → verification fails
card["name"] = "evil-alice"
verify_card(card)         # False
```

That's it. The **private key never leaves your machine**; the card carries only public data plus a signature.

## The registry (optional)

Verifying a signature needs no server — `did:key` is self-certifying. The registry adds **discovery** (find agents by DID), **status** (revocation), and — soon — **reputation**.

```bash
uvicorn registry.app:app --reload
```

```python
from notar import NotarClient

nc = NotarClient("http://localhost:8000")
nc.register(card)              # stored only if the signature checks out
nc.get_agent(ident.did)        # look up a card by DID
nc.verify(card)                # {"valid": True, "did": ..., "status": "active"}
```

The registry **only stores cards whose signature matches their claimed identity** — you can't register a card impersonating someone else, because you'd need their private key.

## How it works (30 seconds)

- Each agent holds an **Ed25519 keypair**. Its public key is encoded into its **`did:key`** identifier, so the DID is self-certifying.
- An **agent card** is a small signed JSON object (identity + endpoint + capabilities). The signature covers the whole card, so nothing can be tampered with undetected.
- To verify: pull the public key out of the card's `issuer` DID and check the signature. An impostor can *claim* your DID but can't *sign* like you.
- The **registry** sits on the *trust path*, not the data path: agents discover and verify each other through it, but message each other **directly**.

## Status

Early and evolving. Working today: identity, signed cards, offline verification, and a registry with register / lookup / verify — fully tested.

Coming next: revocation, reputation, human-readable handles.

## Looking for feedback

If you're building agents and have hit (or expect to hit) the *"is this other agent real?"* problem, I'd genuinely like to hear from you — open an issue or reach out. This is early, and real builders' input shapes where it goes.

## License

[MIT](LICENSE)
