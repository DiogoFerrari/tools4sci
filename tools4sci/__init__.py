try:
    from importlib.metadata import version
    __version__ = version("tools4sci")
except:
    __version__ = ""

from .io import *
from .formulas import *
from .simulate import *
from .stats import *
from .report import *

__all__ = (
    io.__all__ +
    formulas.__all__  +
    simulate.__all__ +
    stats.__all__ +
    report.__all__
)


