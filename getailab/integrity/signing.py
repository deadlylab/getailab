"""
Ed25519 signing for Merkle vault roots — adapted from Old Mate (old-mate-og/foundations/signing.py).

Completes the CIA triad with Merkle trees (integrity) + crush test (availability of truth).
Keys and signatures live under data/labs/<lab_id>/keys/ and .../signatures/.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    InvalidSignature = Exception  # type: ignore[misc,assignment]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _lab_root(lab_id: str, project_root: Optional[Path] = None) -> Path:
    root = project_root or _project_root()
    return root / "data" / "labs" / lab_id


def keys_dir(lab_id: str, project_root: Optional[Path] = None) -> Path:
    return _lab_root(lab_id, project_root) / "keys"


def signatures_dir(lab_id: str, project_root: Optional[Path] = None) -> Path:
    return _lab_root(lab_id, project_root) / "signatures"


def private_key_path(lab_id: str, project_root: Optional[Path] = None) -> Path:
    return keys_dir(lab_id, project_root) / "signing_key.pem"


def public_key_path(lab_id: str, project_root: Optional[Path] = None) -> Path:
    return keys_dir(lab_id, project_root) / "verify_key.pem"


def encryption_key_path(lab_id: str, project_root: Optional[Path] = None) -> Path:
    return keys_dir(lab_id, project_root) / "encryption.key"


def signing_available() -> bool:
    return _CRYPTO_AVAILABLE


def keypair_exists(lab_id: str, project_root: Optional[Path] = None) -> bool:
    return (
        private_key_path(lab_id, project_root).exists()
        and public_key_path(lab_id, project_root).exists()
    )


def signing_status(lab_id: str, project_root: Optional[Path] = None) -> Dict[str, Any]:
    latest = get_latest_signature(lab_id, project_root=project_root)
    return {
        "lab_id": lab_id,
        "crypto_available": signing_available(),
        "private_key": private_key_path(lab_id, project_root).exists(),
        "public_key": public_key_path(lab_id, project_root).exists(),
        "latest_signature": {
            "root_hash": latest.get("root_hash")[:16] + "..." if latest else None,
            "timestamp": latest.get("timestamp") if latest else None,
            "tree_name": (latest or {}).get("metadata", {}).get("tree_name"),
            "loop_id": (latest or {}).get("metadata", {}).get("loop_id"),
        } if latest else None,
    }


def generate_keypair(
    lab_id: str = "example",
    *,
    force: bool = False,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate (or return existing) Ed25519 keypair for a lab."""
    if not signing_available():
        return {
            "status": "unavailable",
            "message": "cryptography package not installed — pip install cryptography",
        }

    priv = private_key_path(lab_id, project_root)
    pub = public_key_path(lab_id, project_root)
    if priv.exists() and not force:
        return {
            "status": "exists",
            "lab_id": lab_id,
            "private_key": str(priv),
            "public_key": str(pub),
            "message": "keypair already exists; use force=True to rotate (invalidates signatures)",
        }

    kdir = keys_dir(lab_id, project_root)
    sdir = signatures_dir(lab_id, project_root)
    kdir.mkdir(parents=True, exist_ok=True)
    sdir.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv.write_bytes(private_pem)
    os.chmod(priv, 0o600)

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub.write_bytes(public_pem)
    os.chmod(pub, 0o644)
    os.chmod(kdir, 0o700)

    return {
        "status": "generated",
        "lab_id": lab_id,
        "private_key": str(priv),
        "public_key": str(pub),
        "message": "keypair generated; private key is owner-read-only (0600)",
    }


def _load_private_key(lab_id: str, project_root: Optional[Path] = None) -> Ed25519PrivateKey:
    if not signing_available():
        raise RuntimeError("cryptography package not installed")
    path = private_key_path(lab_id, project_root)
    if not path.exists():
        raise FileNotFoundError(f"No signing key at {path}. Run generate_keypair() first.")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def _load_public_key(lab_id: str, project_root: Optional[Path] = None) -> Ed25519PublicKey:
    if not signing_available():
        raise RuntimeError("cryptography package not installed")
    path = public_key_path(lab_id, project_root)
    if not path.exists():
        raise FileNotFoundError(f"No verify key at {path}. Run generate_keypair() first.")
    return serialization.load_pem_public_key(path.read_bytes())


def sign_root_hash(
    root_hash: str,
    lab_id: str = "example",
    *,
    metadata: Optional[Dict[str, Any]] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Sign a Merkle root hash (or any attestation string)."""
    private_key = _load_private_key(lab_id, project_root)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    meta = {"lab_id": lab_id, **(metadata or {})}

    sign_payload = {
        "root_hash": root_hash,
        "timestamp": timestamp,
        "metadata": meta,
    }
    message = json.dumps(sign_payload, sort_keys=True, separators=(",", ":")).encode()
    signature = private_key.sign(message)

    record = {
        "root_hash": root_hash,
        "timestamp": timestamp,
        "metadata": meta,
        "signature": signature.hex(),
        "public_key": public_key_path(lab_id, project_root).read_text().strip(),
    }

    sdir = signatures_dir(lab_id, project_root)
    sdir.mkdir(parents=True, exist_ok=True)
    sig_file = sdir / f"sig_{time.strftime('%Y%m%d_%H%M%S')}.json"
    sig_file.write_text(json.dumps(record, indent=2))

    tree_name = meta.get("tree_name", "vault")
    latest_link = sdir / f"sig_{tree_name}_latest.json"
    latest_link.write_text(json.dumps(record, indent=2))

    record["signature_file"] = str(sig_file)
    return record


def verify_signature(
    record: Dict[str, Any],
    lab_id: Optional[str] = None,
    *,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verify a signature record produced by sign_root_hash."""
    lid = lab_id or record.get("metadata", {}).get("lab_id", "example")
    public_key = _load_public_key(lid, project_root)
    sign_payload = {
        "root_hash": record["root_hash"],
        "timestamp": record["timestamp"],
        "metadata": record.get("metadata", {}),
    }
    message = json.dumps(sign_payload, sort_keys=True, separators=(",", ":")).encode()
    signature = bytes.fromhex(record["signature"])

    try:
        public_key.verify(signature, message)
        return {
            "valid": True,
            "root_hash": record["root_hash"],
            "timestamp": record["timestamp"],
            "message": "SIGNATURE VALID",
        }
    except InvalidSignature:
        return {
            "valid": False,
            "root_hash": record["root_hash"],
            "timestamp": record["timestamp"],
            "message": "SIGNATURE INVALID — tampered or wrong key",
        }


def get_latest_signature(
    lab_id: str = "example",
    *,
    tree_name: str = "vault",
    project_root: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    sdir = signatures_dir(lab_id, project_root)
    if not sdir.exists():
        return None

    latest = sdir / f"sig_{tree_name}_latest.json"
    if latest.exists():
        return json.loads(latest.read_text())

    sig_files = sorted(sdir.glob("sig_*.json"), reverse=True)
    for path in sig_files:
        if path.name.endswith("_latest.json"):
            continue
        try:
            record = json.loads(path.read_text())
        except Exception:
            continue
        if record.get("metadata", {}).get("tree_name", "vault") == tree_name:
            return record
    return None


def sign_merkle_tree(
    lab_id: str = "example",
    *,
    tree_name: str = "vault",
    root_hash: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Sign the root hash of a saved Merkle tree (or an explicit root_hash)."""
    if root_hash is None:
        from getailab.integrity.merkle import load_tree

        tree = load_tree(tree_name, lab_id=lab_id)
        if not tree:
            return {"error": f"no Merkle tree saved: {tree_name}"}
        root_hash = tree["hash"]

    meta = {"tree_name": tree_name, **(metadata or {})}
    return sign_root_hash(root_hash, lab_id, metadata=meta, project_root=project_root)


def verify_merkle_signature(
    lab_id: str = "example",
    *,
    tree_name: str = "vault",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Verify latest signature for a Merkle tree against the current saved root hash.
    """
    from getailab.integrity.merkle import load_tree

    if not signing_available():
        return {"valid": False, "message": "cryptography not installed"}

    if not keypair_exists(lab_id, project_root):
        return {"valid": False, "message": "no keypair — POST /api/integrity/sign/keygen first"}

    tree = load_tree(tree_name, lab_id=lab_id)
    if not tree:
        return {"valid": False, "message": f"no Merkle tree: {tree_name}"}

    current_hash = tree["hash"]
    latest = get_latest_signature(lab_id, tree_name=tree_name, project_root=project_root)
    if not latest:
        return {
            "valid": False,
            "message": "no signatures found",
            "current_hash": current_hash,
        }

    if latest["root_hash"] != current_hash:
        return {
            "valid": False,
            "message": "ROOT HASH CHANGED since last signature",
            "signed_hash": latest["root_hash"],
            "current_hash": current_hash,
            "signature_valid_for_record": verify_signature(latest, lab_id, project_root=project_root),
        }

    result = verify_signature(latest, lab_id, project_root=project_root)
    result["current_hash"] = current_hash
    result["tree_name"] = tree_name
    result["signature_file"] = str(
        signatures_dir(lab_id, project_root) / f"sig_{tree_name}_latest.json"
    )
    return result


def attest_vault(
    lab_id: str = "example",
    *,
    loop_id: Optional[int] = None,
    sign: bool = True,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Scan vault Merkle tree and optionally sign the root hash.
    Called after loop archive for provenance attestation.
    """
    from getailab.integrity.verify import _lab_path
    from getailab.integrity.merkle import scan_directory

    vault_path = _lab_path(lab_id, project_root)
    if not vault_path.is_dir():
        return {"error": f"vault not found: {vault_path}"}

    scan = scan_directory(vault_path, "vault", lab_id=lab_id)
    result: Dict[str, Any] = {
        "lab_id": lab_id,
        "scan": {
            "root_hash": scan.get("root_hash"),
            "total_files": scan.get("total_files"),
            "changes_since_previous": scan.get("changes_since_previous"),
            "tree_path": scan.get("tree_path"),
        },
    }

    if not sign:
        return result

    if not signing_available():
        result["signed"] = False
        result["sign_error"] = "cryptography not installed"
        return result

    if not keypair_exists(lab_id, project_root):
        keygen = generate_keypair(lab_id, project_root=project_root)
        result["keygen"] = keygen

    try:
        signature = sign_merkle_tree(
            lab_id,
            tree_name="vault",
            root_hash=scan.get("root_hash"),
            metadata={
                "source": "attest_vault",
                "loop_id": loop_id,
            },
            project_root=project_root,
        )
        result["signed"] = True
        result["signature"] = {
            "root_hash": signature.get("root_hash"),
            "timestamp": signature.get("timestamp"),
            "signature_file": signature.get("signature_file"),
        }
    except Exception as exc:
        result["signed"] = False
        result["sign_error"] = str(exc)

    return result


# ── Optional AES-256-GCM (from Old Mate) ───────────────────────

def _get_encryption_key(lab_id: str, project_root: Optional[Path] = None) -> bytes:
    path = encryption_key_path(lab_id, project_root)
    if path.exists():
        return path.read_bytes()
    private_key = _load_private_key(lab_id, project_root)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    aes_key = hashlib.sha256(private_bytes).digest()
    kdir = keys_dir(lab_id, project_root)
    kdir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(aes_key)
    os.chmod(path, 0o600)
    return aes_key


def encrypt_bytes(plaintext: bytes, lab_id: str = "example", project_root: Optional[Path] = None) -> bytes:
    key = _get_encryption_key(lab_id, project_root)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, None)


def decrypt_bytes(encrypted: bytes, lab_id: str = "example", project_root: Optional[Path] = None) -> bytes:
    key = _get_encryption_key(lab_id, project_root)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(encrypted[:12], encrypted[12:], None)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("GetAiLab Signing Tool")
        print("  python3 -m getailab.integrity.signing keygen [--lab example] [--force]")
        print("  python3 -m getailab.integrity.signing sign [--lab example] [--tree vault]")
        print("  python3 -m getailab.integrity.signing verify [--lab example] [--tree vault]")
        print("  python3 -m getailab.integrity.signing status [--lab example]")
        print("  python3 -m getailab.integrity.signing attest [--lab example] [--loop N]")
        sys.exit(0)

    cmd = sys.argv[1]
    lab_id = "example"
    tree_name = "vault"
    loop_id: Optional[int] = None
    if "--lab" in sys.argv:
        lab_id = sys.argv[sys.argv.index("--lab") + 1]
    if "--tree" in sys.argv:
        tree_name = sys.argv[sys.argv.index("--tree") + 1]
    if "--loop" in sys.argv:
        loop_id = int(sys.argv[sys.argv.index("--loop") + 1])

    if cmd == "keygen":
        print(json.dumps(generate_keypair(lab_id, force="--force" in sys.argv), indent=2))
    elif cmd == "sign":
        print(json.dumps(sign_merkle_tree(lab_id, tree_name=tree_name), indent=2))
    elif cmd == "verify":
        print(json.dumps(verify_merkle_signature(lab_id, tree_name=tree_name), indent=2))
    elif cmd == "status":
        print(json.dumps(signing_status(lab_id), indent=2))
    elif cmd == "attest":
        print(json.dumps(attest_vault(lab_id, loop_id=loop_id), indent=2))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)