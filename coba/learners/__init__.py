"""The public API for the learners module.

This module contains the abstract interface expected for Learner implementations.
This interface is provided for type checking only. It is not required that one
inherit from this interface to implement new learners. In addition, a number 
of learners are provided out of the box for testing and baseline comparisons.
"""

from coba.learners.core import Learner, SafeLearner
from coba.learners.bandit import EpsilonBanditLearner, UcbBanditLearner, FixedLearner, RandomLearner
from coba.learners.corral import CorralLearner
from coba.learners.vowpal import VowpalLearner, VowpalMediator
from coba.learners.linUCB import LinUCBLearner

__all__ = [
    'Learner',
    'SafeLearner',
    'RandomLearner',
    'FixedLearner',
    'EpsilonBanditLearner',
    'UcbBanditLearner',
    'CorralLearner',
    'VowpalLearner',
    'LinUCBLearner',
    'VowpalMediator'
]