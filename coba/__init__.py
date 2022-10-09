from coba.contexts     import CobaContext
from coba.environments import Environments
from coba.experiments  import Experiment, Result, OnlineGroundedEval, OnlineOnPolicyEval

from coba.learners.bandit import EpsilonBanditLearner, UcbBanditLearner, FixedLearner, RandomLearner
from coba.learners.corral import CorralLearner
from coba.learners.vowpal import VowpalLearner, VowpalEpsilonLearner, VowpalSoftmaxLearner, VowpalBagLearner
from coba.learners.vowpal import VowpalCoverLearner, VowpalRegcbLearner, VowpalSquarecbLearner, VowpalOffPolicyLearner
from coba.learners.linucb import LinUCBLearner

from coba.backports import version, PackageNotFoundError

try:
    #Option (5) on https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
    __version__ = version('coba') 
except PackageNotFoundError: #pragma: no cover
    __version__ = "0.0.0"

__all__ = [
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
    'OnlineGroundedEval',
    'OnlineOnPolicyEval'
]
