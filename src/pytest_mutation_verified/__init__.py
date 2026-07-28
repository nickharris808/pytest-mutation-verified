"""pytest-mutation-verified -- prove your regression test can actually fail."""

from .plugin import MutationSpec, mutation_verified

__version__ = "0.1.1"
__all__ = ["mutation_verified", "MutationSpec", "__version__"]
