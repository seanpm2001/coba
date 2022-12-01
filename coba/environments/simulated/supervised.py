from itertools import chain, count
from typing import Any, Iterable, Union, Sequence, overload, Dict, MutableSequence, MutableMapping
from coba.backports import Literal

from coba.pipes import Pipes, Source, IterableSource, LabelRows, Reservoir, UrlSource, CsvReader
from coba.pipes import CsvReader, ArffReader, LibsvmReader, ManikReader

from coba.utilities import peek_first, Categorical

from coba.environments.primitives import SimulatedEnvironment, SimulatedInteraction
from coba.environments.primitives import L1Reward, MulticlassReward, HammingReward

class CsvSource(Source[Iterable[MutableSequence]]):
    """Load a source (either local or remote) in CSV format.

    This is primarily used by SupervisedSimulation to create Environments for Experiments.
    """

    def __init__(self, source: Union[str,Source[Iterable[str]]], has_header:bool=False, **dialect) -> None:
        """Instantiate a CsvSource.

        Args:
            source: The data source. Accepts either a string representing the source location or another Source.
            has_header: Indicates if the CSV files has a header row.
        """
        source = UrlSource(source) if isinstance(source,str) else source
        reader = CsvReader(has_header, **dialect)
        self._source = Pipes.join(source, reader)

    def read(self) -> Iterable[MutableSequence]:
        """Read and parse the csv source."""
        return self._source.read()

    @property
    def params(self) -> Dict[str, Any]:
        """Parameters describing the csv source."""
        return self._source.params

    def __str__(self) -> str:
        return str(self._source)

class ArffSource(Source[Union[Iterable[MutableSequence], Iterable[MutableMapping]]]):
    """Load a source (either local or remote) in ARFF format.

    This is primarily used by SupervisedSimulation to create Environments for Experiments.
    """

    def __init__(self,
        source: Union[str,Source[Iterable[str]]],
        cat_as_str: bool = False) -> None:
        """Instantiate an ArffSource.

        Args:
            source: The data source. Accepts either a string representing the source location or another Source.
            cat_as_str: Indicates that categorical features should be encoded as a string rather than one hot encoded.
        """
        source = UrlSource(source) if isinstance(source,str) else source
        reader = ArffReader(cat_as_str)
        self._source = Pipes.join(source, reader)

    def read(self) -> Union[Iterable[MutableSequence], Iterable[MutableMapping]]:
        """Read and parse the arff source."""
        return self._source.read()

    @property
    def params(self) -> Dict[str, Any]:
        """Parameters describing the arff source."""
        return self._source.params

    def __str__(self) -> str:
        return str(self._source)

class LibSvmSource(Source[Iterable[MutableMapping]]):
    """Load a source (either local or remote) in libsvm format.

    This is primarily used by SupervisedSimulation to create Environments for Experiments.
    """

    def __init__(self, source: Union[str,Source[Iterable[str]]]) -> None:
        """Instantiate a LibsvmSource.

        Args:
            source: The data source. Accepts either a string representing the source location or another Source.
        """
        source = UrlSource(source) if isinstance(source,str) else source
        reader = LibsvmReader()
        self._source = Pipes.join(source, reader)

    def read(self) -> Iterable[MutableMapping]:
        """Read and parse the libsvm source."""
        return self._source.read()

    @property
    def params(self) -> Dict[str, Any]:
        """Parameters describing the libsvm source."""
        return self._source.params

    def __str__(self) -> str:
        return str(self._source)

class ManikSource(Source[Iterable[MutableMapping]]):
    """Load a source (either local or remote) in Manik format.

    This is primarily used by SupervisedSimulation to create Environments for Experiments.
    """

    def __init__(self, source: Union[str,Source[Iterable[str]]]) -> None:
        """Instantiate a ManikSource.

        Args:
            source: The data source. Accepts either a string representing the source location or another Source.
        """
        source = UrlSource(source) if isinstance(source,str) else source
        reader = ManikReader()
        self._source = Pipes.join(source, reader)

    def read(self) -> Iterable[MutableMapping]:
        """Read and parse the manik source."""
        return self._source.read()

    @property
    def params(self) -> Dict[str, Any]:
        """Parameters describing the manik source."""
        return self._source.params

    def __str__(self) -> str:
        return str(self._source)

class SupervisedSimulation(SimulatedEnvironment):
    """Create a contextual bandit simulation using an existing supervised regression or classification dataset."""

    @overload
    def __init__(self,
        source: Source = None,
        label_col: Union[int,str] = None,
        label_type: Literal["c","r","m"] = None,
        take: int = None) -> None:
        """Instantiate a SupervisedSimulation.

        Args:
            source: A source object that reads the supervised data.
            label_col: The header name or index which identifies the label feature in each example. If
                label_col is None the source must return an iterable of tuple pairs where the first item
                are the features and the second item is the label.
            label_type: Indicates whether the label column is a classification or regression value. If an explicit
                label_type is not provided then the label_type will be inferred based on the data source.
            take: The number of random examples you'd like to draw from the given data set for the environment.
        """
        ...

    @overload
    def __init__(self,
        X: Sequence[Any],
        Y: Sequence[Any],
        label_type: Literal["c","r","m"]) -> None:
        """Instantiate a SupervisedSimulation.

        Args:
            X: A sequence of example features that will be used to create interaction contexts in the simulation.
            Y: A sequence of supervised labels that will be used to construct actions and rewards in the simulation.
            label_type: Indicates whether the label column is a classification or regression value.
        """
        ...

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate a SupervisedSimulation."""

        if 'source' in kwargs or (args and hasattr(args[0], 'read')):
            source     = args[0] if len(args) > 0 else kwargs['source']
            label_col  = args[1] if len(args) > 1 else kwargs.get("label_col", None)
            label_type = args[2] if len(args) > 2 else kwargs.get("label_type", None)
            take       = args[3] if len(args) > 3 else kwargs.get("take", None)
            if take      is not None: source = Pipes.join(source, Reservoir(take))
            if label_col is not None: source = Pipes.join(source, LabelRows(label_col,label_type))
            params = source.params

        else:
            X          = args[0]
            Y          = args[1]
            label_type = args[2] if len(args) > 2 else kwargs.get("label_type", None)
            params     = {"source": "[X,Y]"}
            source     = IterableSource(zip(X,Y))

        self._label_type = label_type
        self._source     = source
        self._params     = {**params, "label_type": self._label_type, "type": "SupervisedSimulation" }

    @property
    def params(self) -> Dict[str,Any]:
        return self._params

    def read(self) -> Iterable[SimulatedInteraction]:

        first, rows = peek_first(self._source.read())
        first_row_type = 0 if hasattr(first,'label') else 1

        if not rows: return []

        first_label      = first.label if first_row_type == 0 else first[1]
        first_label_type = first.tipe if first_row_type == 0 else None

        if first_label_type is None:
            label_type = self._label_type or ("r" if isinstance(first_label, (int,float)) else "c")
        else:
            label_type = self._label_type or first_label_type

        label_type = label_type.lower()
        self._params['label_type'] = label_type.upper()

        #these are the cases where we need to know all labels in the dataset to determine actions
        if label_type == "m" or (label_type == "c" and not isinstance(first_label, Categorical)):
            rows = list(rows)
            if first_row_type == 0: labels = [r.label for r in rows]
            if first_row_type == 1: labels = [r[1]    for r in rows]

        if label_type == "r":
            actions = []
            reward  = L1Reward
        elif label_type == "m":
            actions = sorted(set(list(chain(*labels))))
            action_indexes = dict(zip(actions,count()))
            reward = lambda label: HammingReward(list(map(action_indexes.__getitem__,label)))
        else:
            if isinstance(first_label,Categorical):
                actions = [ Categorical(l,first_label.levels) for l in sorted(first_label.levels) ]
            else:
                actions = sorted(set(labels))
            
            action_indexes = dict(zip(actions,count()))
            indexes = list(range(len(actions)))
            reward = lambda label: MulticlassReward(indexes, action_indexes[label])

        if first_row_type == 0:
            for row in rows:
                yield {'type':'simulated','context':row.feats,'actions':actions,'rewards':reward(row.label)}
        else:
            for row in rows:
                yield {'type':'simulated','context':row[0]   ,'actions':actions,'rewards':reward(row[1])}
