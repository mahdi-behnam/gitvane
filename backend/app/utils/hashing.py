import hashlib


def compute_normalized_hash(text: str) -> str:
    """Computes SHA-256 hash over normalized whitespace text"""
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
