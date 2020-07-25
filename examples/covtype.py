"""
This is an example script that creates a ClassificationSimulation using the covertype dataset.
This script requires that the matplotlib and vowpalwabbit packages be installed.
"""

from coba.simulations import ClassificationSimulation, ShuffleSimulation
from coba.learners import RandomLearner, EpsilonLearner, VowpalLearner, UcbTunedLearner
from coba.benchmarks import UniversalBenchmark
from coba.analysis import Plots

csv_path   = "./examples/data/covtype.data"
label_col  = 54

print("loading simulation data...")
#sim = ClassificationSimulation.from_csv_path(csv_path, label_col)
#sim = ClassificationSimulation.from_openml(1116)
sim = ClassificationSimulation.from_openml(150)

print("shuffling simulation data...")
sim = ShuffleSimulation(sim)

print("defining the benchmark...")
benchmark = UniversalBenchmark([sim], batch_size = lambda i: 100 + i*100)

print("creating the learners...")
learner_factories = [ lambda: RandomLearner(), lambda: EpsilonLearner(1/10), lambda: UcbTunedLearner(), lambda: VowpalLearner(bag=5) ]

print("evaluating the learners...")
results = benchmark.evaluate(learner_factories)

Plots.standard_plot(results)