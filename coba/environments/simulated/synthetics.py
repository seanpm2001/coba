import math

from statistics import variance, mean
from itertools import count, islice, cycle
from typing import Sequence, Dict, Tuple, Any, Callable, Optional, overload, Iterable

from coba.exceptions import CobaException
from coba.random import CobaRandom
from coba.encodings import InteractionsEncoder, OneHotEncoder

from coba.environments.primitives import Context, Action
from coba.environments.simulated.primitives import SimulatedEnvironment, SimulatedInteraction, MemorySimulation

class LambdaSimulation(SimulatedEnvironment):
    """A simulation created from generative lambda functions.

    Remarks:
        This implementation is useful for creating a simulation from defined distributions.
    """

    @overload
    def __init__(self,
        n_interactions: Optional[int],
        context       : Callable[[int               ],Context         ],
        actions       : Callable[[int,Context       ],Sequence[Action]],
        reward        : Callable[[int,Context,Action],float           ]) -> None:
        """Instantiate a LambdaSimulation.

        Args:
            n_interactions: An optional integer indicating the number of interactions in the simulation.
            context: A function that should return a context given an index in `range(n_interactions)`.
            actions: A function that should return all valid actions for a given index and context.
            reward: A function that should return the reward for the index, context and action.
        """

    @overload
    def __init__(self, 
        n_interactions: Optional[int],
        context       : Callable[[int               ,CobaRandom],Context         ],
        actions       : Callable[[int,Context       ,CobaRandom],Sequence[Action]],
        reward        : Callable[[int,Context,Action,CobaRandom],float           ],
        seed          : int) -> None:
        """Instantiate a LambdaSimulation.

        Args:
            n_interactions: An optional integer indicating the number of interactions in the simulation.
            context: A function that should return a context given an index and random state.
            actions: A function that should return all valid actions for a given index, context and random state.
            reward: A function that should return the reward for the index, context, action and random state.
            seed: An integer used to seed the random state in order to guarantee repeatability.
        """

    def __init__(self,n_interactions,context,actions,reward,seed=None) -> None:
        """Instantiate a LambdaSimulation."""

        self._n_interactions = n_interactions
        self._context        = context
        self._actions        = actions
        self._reward         = reward
        self._seed           = seed

        self._params = {} if seed is None else {"lambda_seed": seed}

    @property
    def params(self) -> Dict[str, Any]:
        return dict(self._params)

    def read(self) -> Iterable[SimulatedInteraction]:
        rng = None if self._seed is None else CobaRandom(self._seed)

        _context = lambda i    : self._context(i    ,rng) if rng else self._context(i) 
        _actions = lambda i,c  : self._actions(i,c  ,rng) if rng else self._actions(i,c)
        _reward  = lambda i,c,a: self._reward (i,c,a,rng) if rng else self._reward(i,c,a)  

        for i in islice(count(), self._n_interactions):
            context  = _context(i)
            actions  = _actions(i, context)
            rewards  = [ _reward(i, context, action) for action in actions]

            yield SimulatedInteraction(context, actions, rewards=rewards)

    def __str__(self) -> str:
        return "LambdaSimulation"

    class Spoof(MemorySimulation):

        def __init__(self, interactions, _params, _str, _name) -> None:
            type(self).__name__ = _name
            self._str           = _str
            super().__init__(interactions, _params)

        def read(self):
            return self._interactions

        def __str__(self) -> str:
            return self._str

    def __reduce__(self) -> Tuple[object, ...]:
        if self._n_interactions is not None and self._n_interactions < 1000:
            #This is an interesting idea but maybe too wink-wink nudge-nudge in practice. It causes weird flow
            #in the logs that looks like bugs and lags because IO is happening at strange places in a manner that
            #can cause thread locks.
            return (LambdaSimulation.Spoof, (list(self.read()), self.params, str(self), type(self).__name__ ))
        else:
            message = (
                "It is not possible to pickle a LambdaSimulation due to its use of lambda methods in the constructor. "
                "This error occured because an experiment containing a LambdaSimulation tried to execute on multiple processes. "
                "If this is neccesary there are three options to get around this limitation: (1) run your experiment "
                "on a single process rather than multiple, (2) re-design your LambdaSimulation as a class that inherits "
                "from LambdaSimulation and implements __reduce__ (see coba.environments.simulations.LinearSyntheticSimulation "
                "for an example), or (3) specify a finite number for n_interactions in the LambdaSimulation constructor (this "
                "allows us to create the interactions in memory ahead of time and convert to a MemorySimulation when pickling).")
            raise CobaException(message)

class LinearSyntheticSimulation(LambdaSimulation):
    """A synthetic simulation whose rewards are linear with respect to the given reward features.

    The simulation's rewards are linear with respect to the given reward features. When no context or action 
    features are requested reward features are calculted using a constant feature of 1 for non-existant features.
    """

    def __init__(self, 
        n_interactions:int, 
        n_actions:int = 10,
        n_context_features:int = 10,
        n_action_features:int = 10,
        reward_features:Sequence[str] = ["a","xa"],
        seed:int = 1) -> None:
        """Instantiate a LinearSyntheticSimulation.

        Args:
            n_interactions: The number of interactions the simulation should have.
            n_actions: The number of actions each interaction should have.
            n_context_features: The number of features each context should have.
            n_action_features: The number of features each action should have.
            reward_features: The features in the simulation's linear reward function.
            seed: The random number seed used to generate all features, weights and noise in the simulation.
        """

        self._args = (n_interactions, n_actions, n_context_features, n_action_features, reward_features, seed)

        self._n_actions          = n_actions
        self._n_context_features = n_context_features
        self._n_action_features  = n_action_features
        self._reward_features    = reward_features
        self._seed               = seed

        rng          = CobaRandom(seed)
        feat_encoder = InteractionsEncoder(reward_features)

        # we use a log-normal distribution for features because their product will also be log-normal
        # We use a feature distribution with E of 1. This gives a more stable E[reward] though it still isn't fixed.
        # To deal with shifting means and variance we estimate these statistic for reward distribution and control for them.

        sig = 1/3
        var = sig**2
        mu  = -var/2 #this makes the mean of our log-normal distribution 1

        if n_action_features or n_context_features:
            feature_count = len(feat_encoder.encode(x=[1]*(n_context_features or 1),a=[1]*(n_action_features or 1)))
        else:
            feature_count = 1

        if n_action_features > 0:
            #there is only one partition in this case because of action overlap
            action_weights = [ rng.randoms(feature_count) ]
        else:
            #there is a partition per action because actions will never overlap
            action_weights = [ rng.randoms(feature_count) for _ in range(n_actions) ]

        if n_action_features or n_context_features:
            #normalize to make final expectation more stable
            action_weights = [ [ w/sum(weights) for w in weights] for weights in action_weights ] 
        
        self._action_weights = action_weights

        action_gen  = lambda: list(map(math.exp, rng.gausses(n_action_features,mu,sig))) if n_action_features else 1
        context_gen = lambda: list(map(math.exp, rng.gausses(n_context_features,mu,sig))) if n_context_features else 1

        rs = []
        for feats in (feat_encoder.encode(x=context_gen(),a=action_gen()) for _ in range(10000)):
            rs.append([sum([w*f for w,f in zip(weights,feats)]) for weights in action_weights])

        #estimate via MC methods. Analytical solutions are too complex due to RV correlations.
        r_vars  = [ variance(r) for r in zip(*rs)] 
        r_means = [ mean(r) for r in zip(*rs)    ]

        def context(index:int, rng: CobaRandom) -> Context:
            return tuple(map(math.exp, rng.gausses(n_context_features,mu,sig))) if n_context_features else None

        def actions(index:int, context: Context, rng: CobaRandom) -> Sequence[Action]:
            if n_action_features:
                return  [ tuple(map(math.exp, rng.gausses(n_action_features,mu,sig))) for _ in range(n_actions)] 
            else:
                return OneHotEncoder().fit_encodes(range(n_actions))

        def reward(index:int, context:Context, action:Action, rng: CobaRandom) -> float:

            X = context if n_context_features else [1]
            A = action  if n_action_features  else [1] 
            
            if n_action_features or n_context_features:
                F = feat_encoder.encode(x=X,a=A)
            else:
                F = [1]
            
            W = action_weights[0 if n_action_features else action.index(1)]
            V = r_vars[0 if n_action_features else action.index(1)]
            E = r_means[0 if n_action_features else action.index(1)]

            r = sum([w*f for w,f in zip(W,F)])

            if V != 0:
                scalar = 1/(5*math.sqrt(V))
                bias   = 0.5 - E*scalar
                r      = bias + scalar*r

            return r

        super().__init__(n_interactions, context, actions, reward, seed)

    @property
    def params(self) -> Dict[str, Any]:
        return {"reward_features": self._reward_features, "seed" : self._seed}

    def __reduce__(self) -> Tuple[object, ...]:
        return (LinearSyntheticSimulation, self._args)

    def __str__(self) -> str:
        return f"LinearSynth(A={self._n_actions},c={self._n_context_features},a={self._n_action_features},R={self._reward_features},seed={self._seed})"

class NeighborsSyntheticSimulation(LambdaSimulation):
    """A synthetic simulation whose reward values are determined by neighborhoodS. 

    The simulation's rewards are determined by the location of given context and action pairs. These locations
    indicate which neighborhood the context action pair belongs to. Neighborhood rewards are determined by 
    random assignment.
    """

    def __init__(self,
        n_interactions:int,
        n_actions:int = 10,
        n_context_features:int = 10,
        n_action_features:int = 10,
        n_neighborhoods:int = 10,
        seed: int = 1) -> None:
        """Instantiate a NeighborsSyntheticSimulation.

        Args:
            n_interactions: The number of interactions the simulation should have.
            n_actions: The number of actions each interaction should have.
            n_context_features: The number of features each context should have.
            n_action_features: The number of features each action should have.
            n_neighborhoods: The number of neighborhoods the simulation should have.
            seed: The random number seed used to generate all contexts and action rewards.
        """

        self._args = (n_interactions, n_actions, n_context_features, n_action_features, n_neighborhoods, seed)

        self._n_interactions  = n_interactions
        self._n_actions       = n_actions
        self._n_context_feats = n_context_features
        self._n_action_feats  = n_action_features
        self._n_neighborhoods = n_neighborhoods
        self._seed            = seed

        rng = CobaRandom(self._seed)

        def context_gen():
            return tuple(rng.gausses(n_context_features,0,1))

        def actions_gen():
            if not n_action_features:
                return OneHotEncoder().fit_encodes(range(n_actions))
            else:
                return [ tuple(rng.gausses(n_action_features,0,1)) for _ in range(n_actions) ]

        contexts               = [ context_gen() for _ in range(self._n_neighborhoods) ]
        context_actions        = { c: actions_gen() for c in contexts }
        context_action_rewards = { (c,a):rng.random() for c in contexts for a in context_actions[c] }

        context_iter = iter(islice(cycle(contexts),n_interactions))

        def context_generator(index:int, rng: CobaRandom):
            return next(context_iter)

        def action_generator(index:int, context:Tuple[float,...], rng: CobaRandom):
            return context_actions[context]

        def reward_function(index:int, context:Tuple[float,...], action: Tuple[int,...], rng: CobaRandom):
            return context_action_rewards[(context,action)]

        return super().__init__(self._n_interactions, context_generator, action_generator, reward_function, seed)

    @property
    def params(self) -> Dict[str, Any]:
        return { "n_neighborhoods": self._n_neighborhoods,"seed": self._seed }

    def __str__(self) -> str:
        return f"NeighborsSynth(A={self._n_actions},c={self._n_context_feats},a={self._n_action_feats},N={self._n_neighborhoods},seed={self._seed})"

    def __reduce__(self) -> Tuple[object, ...]:
        return (NeighborsSyntheticSimulation, self._args)
