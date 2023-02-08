from typing import Iterable, Optional, List, Any

from pandas import DataFrame

from coba.environments.primitives import Environment, LoggedInteraction
from coba.pipes import IterableSource
from coba.utilities import peek_first


class BanditReplay(Environment):
    def __init__(self,
                 df: DataFrame,
                 take: Optional[int] = None,
                 actions: Optional[List[Any]] = None):
        self._actions = actions
        self._df = df[:take] if take is not None else df

    def read(self) -> Iterable[LoggedInteraction]:
        source = IterableSource(self._df.iterrows())
        first, rows = peek_first(source.read())
        # TODO index might be iterrows specific
        for _index, row in rows:
            yield LoggedInteraction(
                context=row['context'],
                action=row['action'],
                reward=row.get('reward'),
                probability=row.get('probability'),
                actions=row.get('actions', self._actions)
            )