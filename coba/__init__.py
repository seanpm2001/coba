from coba.contexts     import CobaContext, NullLogger
from coba.environments import Environments, ArffSource, CsvSource, LibSvmSource, ManikSource
from coba.environments import Interaction, SimulatedInteraction, LoggedInteraction, GroundedInteraction, LambdaSimulation
from coba.experiments  import Experiment, Result, SimpleEvaluation, SimpleLearnerInfo, SimpleEnvironmentInfo
from coba.experiments  import ExplorationEvaluation, OnPolicyEvaluation, OffPolicyEvaluation

from coba.random import CobaRandom

from coba.learners.primitives import Learner, ActionProb, PMF
from coba.learners.safety import SafeLearner
from coba.learners.bandit import EpsilonBanditLearner, UcbBanditLearner, FixedLearner, RandomLearner
from coba.learners.corral import CorralLearner
from coba.learners.vowpal import VowpalLearner, VowpalEpsilonLearner, VowpalSoftmaxLearner, VowpalBagLearner, VowpalRndLearner
from coba.learners.vowpal import VowpalCoverLearner, VowpalRegcbLearner, VowpalSquarecbLearner, VowpalOffPolicyLearner
from coba.learners.linucb import LinUCBLearner

from coba.utilities import peek_first

from coba.exceptions import CobaException

from coba.backports import version, PackageNotFoundError

try:
    #Option (5) on https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
    __version__ = version('coba') 
except PackageNotFoundError: #pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "CobaException",
    "CobaContext",
    "Environments",
    "Experiment",
    "Result",
    'RandomLearner',
    'FixedLearner',
    'EpsilonBanditLearner',
    'UcbBanditLearner',
    'CorralLearner',
    'LinUCBLearner',
    'VowpalLearner',
    'VowpalEpsilonLearner',
    'VowpalSoftmaxLearner',
    'VowpalBagLearner',
    'VowpalCoverLearner',
    'VowpalRegcbLearner',
    'VowpalSquarecbLearner',
    'VowpalOffPolicyLearner',
    'VowpalRndLearner',
    'OnlineGroundedEval',
    'OnlineOnPolicyEval',
    'CobaRandom',
    'NullLogger',
    'ArffSource',
    'CsvSource',
    'LibSvmSource',
    'ManikSource',
    'SimulatedInteraction',
    'LoggedInteraction',
    'GroundedInteraction',
    'SimpleEvaluation', 
    'SimpleLearnerInfo', 
    'SimpleEnvironmentInfo',
    'LambdaSimulation',
    'Learner',
    'SafeLearner',
    'ExplorationEvaluation',
    'OnPolicyEvaluation',
    'OffPolicyEvaluation',
    'peek_first',
    'ActionProb', 
    'PMF',
    'Interaction'
]
