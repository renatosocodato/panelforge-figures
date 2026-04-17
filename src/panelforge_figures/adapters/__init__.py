"""Data adapters: read a source + options → return a dict or DataFrame.

Adapters are pure functions behind a tiny protocol. The package ships a few
generic adapters here; per-manuscript custom adapters live in the manuscript
repo under `figures/adapters/local/<name>.py`, referenced in the manifest as
`adapter: local.<name>`.
"""

from .base import (
    AdapterProtocol,
    AdapterRegistry,
    get_adapter,
    list_adapters,
    load_local_adapter,
    register_adapter,
)
from .numpy_npz import load_numpy_npz
from .pandas_pickle import load_pandas_pickle
from .passthrough import load_passthrough
from .tabular import load_tabular

register_adapter("tabular", load_tabular)
register_adapter("numpy_npz", load_numpy_npz)
register_adapter("pandas_pickle", load_pandas_pickle)
register_adapter("passthrough", load_passthrough)

__all__ = [
    "AdapterProtocol",
    "AdapterRegistry",
    "get_adapter",
    "list_adapters",
    "load_local_adapter",
    "load_numpy_npz",
    "load_pandas_pickle",
    "load_passthrough",
    "load_tabular",
    "register_adapter",
]
