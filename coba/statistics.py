from math import hypot, isnan, erf, sqrt
from sys import version_info
from operator import mul, sub
from bisect import bisect_left 
from itertools import repeat, accumulate
from abc import abstractmethod, ABC
from typing import Sequence, Tuple, Union, Callable
from coba.backports import Literal

from coba.exceptions import CobaException
from coba.random import CobaRandom
from coba.utilities import PackageChecker

def iqr(values: Sequence[float]) -> float:

    if len(values) <= 1: return 0.

    values = sorted(values)

    p25,p75 = percentile(values, [0.25,0.75])

    return p75-p25

def weighted_percentile(values: Sequence[float], weights: Sequence[float], percentiles: Union[float,Sequence[float]], sort: bool = True) -> Union[float, Tuple[float,...]]:

    def _percentile(values: Sequence[float], weights:Sequence[float], percentile: float) -> float:
        assert 0 <= percentile and percentile <= 1, "Percentile must be between 0 and 1 inclusive."

        if percentile == 0:
            return values[0]
        
        if percentile == 1:
            return values[-1]

        R = bisect_left(weights,percentile)
        L = R-1
        LP = (weights[R]-percentile)/(weights[R]-weights[L])

        return LP*values[L] + (1-LP)*values[R]

    if sort:
        values, weights = zip(*sorted(zip(values,weights)))
    
    weights = (0,)+weights[1:]
    weight_sum = sum(weights)
    weights    = [w/weight_sum for w in accumulate(weights) ] 

    if isinstance(percentiles,(float,int)):
        return _percentile(values, weights, percentiles)
    else:
        return tuple([_percentile(values, weights, p) for p in percentiles ])

def percentile(values: Sequence[float], percentiles: Union[float,Sequence[float]], sort: bool = True) -> Union[float, Tuple[float,...]]:

    def _percentile(values: Sequence[float], percentile: float) -> float:
        assert 0 <= percentile and percentile <= 1, "Percentile must be between 0 and 1 inclusive."

        i = percentile*(len(values)-1)
        I = int(i)
        
        if i == I:
            return values[I]
        else:
            w = (i-I)
            return (1-w)*values[I] + w*values[I+1]

    if sort:
        values = sorted(values)

    if isinstance(percentiles,(float,int)):
        return _percentile(values, percentiles)
    else:
        return tuple([_percentile(values, p) for p in percentiles ])

def phi(x: float) -> float:
    'Cumulative distribution function for the standard normal distribution'
    return (1.0 + erf(x / sqrt(2.0))) / 2.0

def mean(sample: Sequence[float]) -> float:
    #If precision is needed use a true statistics package  
    return sum(sample)/len(sample)

def var(sample: Sequence[float]) -> float:
    n = len(sample)

    if n == 1: return float('nan')

    if version_info >= (3,8): #pragma: no cover
        #In Python 3.8 hypot was extended to support any number of items
        #this provides a fast/safe way to calculate the sum of squares
        #and so we revert to the one-pass method and trust in hypot
        E_s2 = hypot(*sample)**2
        E_s = sum(sample)
        return (E_s2-E_s*E_s/n)/(n-1)
    else:
        #using the corrected two pass algo as recommended by
        #https://cpsc.yale.edu/sites/default/files/files/tr222.pdf
        #I've optimized this as much as I think is possible in python
        diffs = tuple(map(sub,sample,repeat(sum(sample)/n)))
        return sum(map(mul,diffs,diffs))/(n-1)

def stdev(sample: Sequence[float]) -> float:
    return var(sample)**(1/2)

class PointAndInterval(ABC):

    @abstractmethod
    def calculate(self, sample: Sequence[float]) -> Tuple[float, Tuple[float, float]]:
        ...

class StandardErrorOfMean(PointAndInterval):

    def __init__(self, z_score:float=1.96) -> None:
        self._z_score = z_score 

    def calculate(self, sample: Sequence[float]) -> Tuple[float, Tuple[float, float]]:
        mu = mean(sample)
        se = 0 if len(sample) == 1 else stdev(sample)/(len(sample)**(.5))
        
        return (mu, (self._z_score*se,self._z_score*se))

class BootstrapConfidenceInterval(PointAndInterval):

    def __init__(self, confidence:float, statistic:Callable[[Sequence[float]], float]) -> None:
        self._conf = confidence
        self._stat = statistic

    def calculate(self, sample: Sequence[float]) -> Tuple[float, Tuple[float, float]]:
        rng = CobaRandom(1)
        n = len(sample)

        sample_stats = [ self._stat([sample[i] for i in rng.randints(n, 0, n-1)]) for _ in range(50) ]

        lower_conf = (1-self._conf)/2
        upper_conf = (1+self._conf)/2

        point_stat = self._stat(sample)
        lower_stat,upper_stat = percentile(sample_stats,[lower_conf,upper_conf])

        return (point_stat, (point_stat-lower_stat,upper_stat-point_stat))

class BinomialConfidenceInterval(PointAndInterval):

    def __init__(self, method:Literal['wilson', 'clopper-pearson']):
        self._method = method

    def calculate(self, sample: Sequence[float]) -> Tuple[float, Tuple[float, float]]:
        if set(sample) - set([0,1]):
            raise CobaException("A binomial confidence interval can only be calculated on values of 0 and 1.")

        if self._method == "wilson":
            z_975 = 1.96 #z-score for .975 area to the left
            p_hat = sum(sample)/len(sample)
            n     = len(sample)
            Q     = z_975**2/(2*n)

            #https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
            interval_num = z_975*((p_hat*(1-p_hat))/n + Q/(2*n))**(.5)
            location_num = (p_hat+Q)
            
            interval_den = (1+2*Q)
            location_den = (1+2*Q)

            interval = interval_num/interval_den
            location = location_num/location_den

            return (p_hat, (p_hat-(location-interval), (location+interval)-p_hat))
        
        else:
            PackageChecker.sklearn("BinomialConfidenceInterval")
            from scipy.stats import beta
            lo = beta.ppf(.05/2, sum(sample), len(sample) - sum(sample) + 1)
            hi = beta.ppf(1-.05/2, sum(sample) + 1, len(sample) - sum(sample))
            p_hat = sum(sample)/len(sample)

            lo = 0.0 if isnan(lo) else lo
            hi = 1.0 if isnan(hi) else hi

            return (p_hat, (p_hat-lo,hi-p_hat))

class OnlineVariance():
    """Calculate sample variance in an online fashion.

    Remarks:
        This algorithm is known as Welford's algorithm and the implementation below
        is a modified version of the Python algorithm created by Wikepedia contributors (2020).

    References:
        Wikipedia contributors. (2020, July 6). Algorithms for calculating variance. In Wikipedia, The
        Free Encyclopedia. Retrieved 18:00, July 24, 2020, from
        https://en.wikipedia.org/w/index.php?title=Algorithms_for_calculating_variance&oldid=966329915
    """

    def __init__(self) -> None:
        """Instatiate an OnlineVariance calcualator."""
        self._count    = 0.
        self._mean     = 0.
        self._M2       = 0.
        self._variance = float("nan")

    @property
    def variance(self) -> float:
        """The variance of all given updates."""
        return self._variance

    def update(self, value: float) -> None:
        """Update the current variance with the given value."""

        (count,mean,M2) = (self._count, self._mean, self._M2)

        count   += 1
        delta   = value - mean
        mean   += delta / count
        delta2  = value - mean
        M2     += delta * delta2

        (self._count, self._mean, self._M2) = (count, mean, M2)

        if count > 1:
            self._variance = M2 / (count - 1)

class OnlineMean():
    """Calculate mean in an online fashion."""

    def __init__(self):
        self._n = 0
        self._mean = float('nan')

    @property
    def mean(self) -> float:
        """The mean of all given updates."""

        return self._mean

    def update(self, value:float) -> None:
        """Update the current mean with the given value."""

        self._n += 1

        alpha = 1/self._n

        self._mean = value if alpha == 1 else (1 - alpha) * self._mean + alpha * value
