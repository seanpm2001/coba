from pathlib import Path
from itertools import product
from typing import Sequence, Optional, Union, overload, Tuple

from coba.pipes import Pipes, DiskSink, ListSink, DiskSource, ListSource, Identity, Insert
from coba.learners import Learner
from coba.environments import Environment
from coba.multiprocessing import CobaMultiprocessor
from coba.contexts import CobaContext, ExceptLog, StampLog, NameLog, DecoratedLogger, ExceptionLogger
from coba.exceptions import CobaException

from coba.experiments.process import CreateWorkItems,  RemoveFinished, ChunkByChunk, MaxChunk, ProcessWorkItems
from coba.experiments.tasks   import EnvironmentTask, EvaluationTask, LearnerTask
from coba.experiments.tasks   import SimpleLearnerInfo, SimpleEnvironmentInfo, SimpleEvaluation, LambdaEvaluation
from coba.experiments.results import Result, TransactionDecode, TransactionEncode, TransactionResult

class Experiment:
    """An Experiment using a collection of environments and learners."""

    @overload
    def __init__(self,
        environments    : Union[Environment, Sequence[Environment]],
        learners        : Union[Learner,Sequence[Learner]],
        *,
        description     : str             = None,
        learner_task    : LearnerTask     = SimpleLearnerInfo(),
        environment_task: EnvironmentTask = SimpleEnvironmentInfo(),
        evaluation_task : EvaluationTask  = SimpleEvaluation()) -> None:
        """Instantiate an Experiment.

        Args:
            environments: The collection of environments to use in the experiment.
            learners: The collection of learners to use in the experiment.
            description: A description of the experiment for documentaiton purposes.
            learner_task: A task which describes a learner.
            environment_task: A task which describes an environment.
            evaluation_task: A task which evaluates a learner on an environment.
        """

    @overload
    def __init__(self,
        eval_pairs      : Sequence[Tuple[Learner,Environment]],
        *,
        description     : str             = None,
        learner_task    : LearnerTask     = SimpleLearnerInfo(),
        environment_task: EnvironmentTask = SimpleEnvironmentInfo(),
        evaluation_task : EvaluationTask  = SimpleEvaluation()) -> None:
        ...
        """Instantiate an Experiment.

        Args:
            eval_pairs: The collection of learners with their evaluation environments.
            learner_task: A task which describes a learner.
            environment_task: A task which describes an environment.
            evaluation_task: A task which evaluates a learner on an environment.
        """

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate an Experiment."""

        # TODO kwargs from other constructors aren't properly processed
        if len(args) == 2:
            envs = [args[0]] if hasattr(args[0],'read') else args[0]
            lrns = [args[1]] if hasattr(args[1],'predict') else args[1]
            args = [list(zip(*reversed(list(zip(*product(envs,lrns))))))]

        self._pairs            = args[0]
        self._description      = kwargs.get('description',None)
        self._learner_task     = kwargs.get('learner_task', SimpleLearnerInfo())
        self._environment_task = kwargs.get('environment_task', SimpleEnvironmentInfo())
        self._evaluation_task  = kwargs.get('evaluation_task', SimpleEvaluation())

        if callable(self._evaluation_task):
            self._evaluation_task = LambdaEvaluation(self._evaluation_task)

        if any([lrn is None for lrn,_ in self._pairs]):
            raise CobaException("A Learner was given whose value was None, which can't be processed.")

        if any([env is None for _,env in self._pairs]):
            raise CobaException("An Environment was given whose value was None, which can't be processed.")

        self._processes        : Optional[int] = None
        self._maxchunksperchild: Optional[int] = None
        self._maxtasksperchunk : Optional[int] = None

    def config(self,
        processes: int = None,
        maxchunksperchild: Optional[int] = None,
        maxtasksperchunk: Optional[int] = None) -> 'Experiment':
        """Configure how the experiment will be executed.

        A value of `None` for any item means the CobaContext.experiment will be used.

        Args:
            processes: The number of processes to create for evaluating the experiment.
            maxchunksperchild: The number of chunks each process evaluate before being restarted. A 
                value of 0 means that all processes will survive until the end of the experiment.
            maxtasksperchunk: The maximum number of tasks a chunk can have. If a chunk has too many 
                tasks it will be split into smaller chunks. A value of 0 means that chunks are never
                broken down into smaller chunks.
        """

        assert processes is None or processes > 0, "The given number of processes is invalid. Must be greater than 0."
        assert maxchunksperchild is None or maxchunksperchild >= 0, "The given number of chunks per child is invalid. Must be greater than or equal to 0 (0 for infinite)."
        assert maxtasksperchunk is None or maxtasksperchunk >= 0, "The given number of tasks per chunk is invalid. Must be greater than or equal to 0 (0 for infinite)."

        self._processes         = processes
        self._maxchunksperchild = maxchunksperchild
        self._maxtasksperchunk  = maxtasksperchunk

        return self

    @property
    def processes(self) -> int:
        """The number of processes to use when evaluating the experiment."""
        return self._processes if self._processes is not None else CobaContext.experiment.processes

    @property
    def maxchunksperchild(self) -> int:
        """The number of tasks chunks to perform per process before restarting an evaluation process."""
        return self._maxchunksperchild if self._maxchunksperchild is not None else CobaContext.experiment.maxchunksperchild

    @property
    def maxtasksperchunk(self) -> int:
        """The maximum number of tasks allowed in a chunk before breaking a chunk into smaller chunks."""
        return self._maxtasksperchunk if self._maxtasksperchunk is not None else CobaContext.experiment.maxtasksperchunk

    def run(self, result_file:str = None, quiet:bool = False, processes:int = None, seed: Optional[int] = 1) -> Result:
        """Run the experiment and return the results.

        Args:
            result_file: The file for writing and restoring results.
            quiet: Indicates that logged output should be turned off.
            processes: The number of processes to create for evaluating the experiment.
            seed: The seed that will determine all randomness within the experiment.
        """
        mp, mc, mt = (processes or self.processes), self.maxchunksperchild, self.maxtasksperchunk

        CobaContext.store['experiment_seed'] = seed
        is_multiproc = mp > 1 or mc != 0

        old_logger = CobaContext.logger

        if quiet:
            CobaContext.logger = DecoratedLogger([], ExceptionLogger(CobaContext.logger.sink), [NameLog(),StampLog()] if is_multiproc else [StampLog()])
        else:
            CobaContext.logger = DecoratedLogger([ExceptLog()], CobaContext.logger, [NameLog(),StampLog()] if is_multiproc else [StampLog()])

        if result_file and Path(result_file).exists():
            CobaContext.logger.log("Restoring existing experiment logs...")
            restored = Result.from_file(result_file)
        else:
            restored = None

        n_given_learners     = len(set([l for l,_ in self._pairs]))
        n_given_environments = len(set([e for _,e in self._pairs]))

        if restored:
            assert n_given_learners     == restored.experiment.get('n_learners',n_given_learners)        , "The current experiment doesn't match the given transaction log."
            assert n_given_environments == restored.experiment.get('n_environments',n_given_environments), "The current experiment doesn't match the given transaction log."

        meta = {'n_learners':n_given_learners,'n_environments':n_given_environments,'description':self._description,'seed':seed}

        workitems  = CreateWorkItems(self._pairs, self._learner_task, self._environment_task, self._evaluation_task)
        unfinished = RemoveFinished(restored)
        chunk      = ChunkByChunk(mp)
        max_chunk  = MaxChunk(mt)
        process    = CobaMultiprocessor(ProcessWorkItems(), mp, mc, False)
        encode     = TransactionEncode()
        sink       = DiskSink(result_file) if result_file else ListSink(foreach=True)
        source     = DiskSource(result_file) if result_file else ListSource(sink.items)
        decode     = TransactionDecode()
        result     = TransactionResult()
        preamble   = Identity() if restored else Insert([["T0",meta]])

        try:
            CobaContext.logger.log("Experiment Started")
            Pipes.join(workitems, unfinished, chunk, max_chunk, process, preamble, encode, sink).run()
            CobaContext.logger.log("Experiment Finished")
        except KeyboardInterrupt: # pragma: no cover
            CobaContext.logger.log("Experiment Aborted (aborted via Ctrl-C)")
        except Exception as ex: # pragma: no cover
            CobaContext.logger.log(ex)
            CobaContext.logger.log("Experiment Stopped")

        CobaContext.logger = old_logger
        del CobaContext.store['experiment_seed']

        return Pipes.join(source,decode,result).read()

    def evaluate(self, result_file:str = None) -> Result:
        """Evaluate the experiment and return the results (this is a backwards compatible proxy for the run method).

        Args:
            result_file: The file for writing and restoring results .
        """

        return self.run(result_file=result_file)
