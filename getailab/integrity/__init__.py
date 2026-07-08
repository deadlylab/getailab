"""Integrity primitives: Merkle snapshots, vault verification, signing (future)."""

from typing import Any

__all__ = [
    # merkle
    "build_tree",
    "compare_saved_trees",
    "compare_trees",
    "find_duplicates",
    "hash_file",
    "hash_string",
    "load_tree",
    "print_tree_summary",
    "save_tree",
    "scan_directory",
    "tree_summary",
    # verify
    "crush_test_indexes",
    "crush_test_page",
    "crush_test_vault",
    "merkle_status",
    "scan_integrity_targets",
    "verify_full",
    # signing
    "attest_vault",
    "generate_keypair",
    "sign_merkle_tree",
    "signing_available",
    "signing_status",
    "verify_merkle_signature",
]

_MERKLE_NAMES = {
    "build_tree",
    "compare_saved_trees",
    "compare_trees",
    "find_duplicates",
    "hash_file",
    "hash_string",
    "load_tree",
    "print_tree_summary",
    "save_tree",
    "scan_directory",
    "tree_summary",
}

_VERIFY_NAMES = {
    "crush_test_indexes",
    "crush_test_page",
    "crush_test_vault",
    "merkle_status",
    "scan_integrity_targets",
    "verify_full",
}

_SIGNING_NAMES = {
    "attest_vault",
    "generate_keypair",
    "sign_merkle_tree",
    "signing_available",
    "signing_status",
    "verify_merkle_signature",
}


def __getattr__(name: str) -> Any:
    if name in _MERKLE_NAMES:
        from . import merkle
        return getattr(merkle, name)
    if name in _VERIFY_NAMES:
        from . import verify
        return getattr(verify, name)
    if name in _SIGNING_NAMES:
        from . import signing
        return getattr(signing, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")