from __future__ import annotations

import pkgutil
import importlib

__all__ = []

for m in pkgutil.iter_modules(__path__):
    name = m.name
    mod = importlib.import_module(f"{__name__}.{name}")
    fn = getattr(mod, name, None)
    globals()[name] = fn
    __all__.append(name)
