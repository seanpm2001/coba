import warnings
import importlib

from itertools import chain
from collections import defaultdict
from typing import TypeVar, Iterable, Tuple, Sequence

from coba.exceptions import CobaExit

def coba_exit(message:str):
    #we ignore warnings before exiting in order to make jupyter's output a little cleaner
    warnings.filterwarnings("ignore",message="To exit: use 'exit', 'quit', or Ctrl-D.")
    raise CobaExit(message) from None

class PackageChecker:

    @staticmethod
    def matplotlib(caller_name: str) -> None:
        """Raise ImportError with detailed error message if matplotlib is not installed.

        Functionality requiring matplotlib should call this helper and then lazily import.

        Args:
            caller_name: The name of the caller that requires matplotlib.

        Remarks:
            This pattern borrows heavily from sklearn. As of 6/20/2020 sklearn code could be found
            at https://github.com/scikit-learn/scikit-learn/blob/master/sklearn/utils/__init__.py
        """
        try:
            importlib.import_module('matplotlib.pyplot')
        except ImportError:
            PackageChecker._handle_import_error(caller_name, "matplotlib")

    @staticmethod
    def vowpalwabbit(caller_name: str) -> None:
        """Raise ImportError with detailed error message if vowpalwabbit is not installed.

        Functionality requiring vowpalwabbit should call this helper and then lazily import.

        Args:
            caller_name: The name of the caller that requires vowpalwabbit.

        Remarks:
            This pattern was inspired by sklearn (see `PackageChecker.matplotlib` for more information).
        """

        try:
            importlib.import_module('vowpalwabbit')
        except ImportError as e:
            PackageChecker._handle_import_error(caller_name, "vowpalwabbit")

    @staticmethod
    def pandas(caller_name: str) -> None:
        """Raise ImportError with detailed error message if pandas is not installed.

        Functionality requiring pandas should call this helper and then lazily import.

        Args:
            caller_name: The name of the caller that requires pandas.

        Remarks:
            This pattern was inspired by sklearn (see `PackageChecker.matplotlib` for more information).
        """
        try:
            importlib.import_module('pandas')
        except ImportError:
            PackageChecker._handle_import_error(caller_name, "pandas")

    @staticmethod
    def numpy(caller_name: str) -> None:
        """Raise ImportError with detailed error message if numpy is not installed.

        Functionality requiring numpy should call this helper and then lazily import.

        Args:
            caller_name: The name of the caller that requires numpy.

        Remarks:
            This pattern was inspired by sklearn (see `PackageChecker.matplotlib` for more information).
        """
        try:
            importlib.import_module('numpy')
        except ImportError:
            PackageChecker._handle_import_error(caller_name, "numpy")

    @staticmethod
    def sklearn(caller_name: str) -> None:
        """Raise ImportError with detailed error message if sklearn is not installed.

        Functionality requiring sklearn should call this helper and then lazily import.

        Args:
            caller_name: The name of the caller that requires sklearn.

        Remarks:
            This pattern was inspired by sklearn (see `PackageChecker.matplotlib` for more information).
        """
        try:
            importlib.import_module('sklearn')
        except ImportError:
            PackageChecker._handle_import_error(caller_name, "scikit-learn")

    def _handle_import_error(caller_name:str, pkg_name:str):
        coba_exit(f"ERROR: {caller_name} requires the {pkg_name} package. You can install this package via `pip install {pkg_name}`.")

class KeyDefaultDict(defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError( key )
        else:
            value = self.default_factory(key)
            self[key] = value
            return value

_T = TypeVar("_T")
def peek_first(items: Iterable[_T]) -> Tuple[_T, Iterable[_T]]:
    items = iter(items)
    try:
        first = next(items)
        return first, chain([first],items)
    except StopIteration:
        return None, []

class Categorical(str):
    __slots__ = ('levels','onehot')
    
    def __new__(cls, value:str, levels: Sequence[str]) -> str:
        return str.__new__(Categorical,value)
    
    def __init__(self, value:str, levels: Sequence[str]) -> None:
        self.levels = levels
        self.onehot = [0]*len(levels)
        self.onehot[levels.index(value)] = 1
        self.onehot = tuple(self.onehot)

    def __repr__(self) -> str:
        return f"Categorical('{self}',{self.levels})"
