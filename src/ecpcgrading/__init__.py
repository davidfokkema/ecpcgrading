import importlib.metadata

try:
    __version__ = importlib.metadata.version("ecpcgrading")
except importlib.metadata.PackageNotFoundError:
    __version__ = None
