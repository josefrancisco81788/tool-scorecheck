import hashlib

import numpy as np


class Streams:
    """The only constructor of numpy Generators in src/.

    Each draw site asks for a child stream by a stable name, so adding or skipping a draw never
    shifts another column, and overrides or weights never consume randomness. Names are keyed by
    SHA-256 rather than ``hash()`` so PYTHONHASHSEED cannot change a draw.
    """

    def __init__(self, seed: int, namespace: str) -> None:
        self.seed = seed
        self.namespace = namespace
        self._issued: set[str] = set()

    def __call__(self, name: str) -> np.random.Generator:
        if name in self._issued:
            raise ValueError(f"stream {self.namespace}/{name} was already issued")
        self._issued.add(name)
        digest = hashlib.sha256(f"{self.namespace}/{name}".encode("utf-8")).digest()[:16]
        key = tuple(int.from_bytes(digest[i:i + 4], "big") for i in range(0, 16, 4))
        return np.random.default_rng(np.random.SeedSequence(self.seed, spawn_key=key))
