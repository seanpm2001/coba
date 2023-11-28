import math
import unittest

from coba.learners import EpsilonBanditLearner, UcbBanditLearner, RandomLearner, FixedLearner

class EpsilonBanditLearner_Tests(unittest.TestCase):

    def test_params(self):
        learner = EpsilonBanditLearner(epsilon=0.5)
        self.assertEqual({"family":"epsilon_bandit", "epsilon":0.5}, learner.params)

    def test_score_no_learn(self):
        learner = EpsilonBanditLearner(epsilon=0.5)
        self.assertEqual([.25,.25,.25,.25],[learner.score(None, [1,2,3,4],a) for a in [1,2,3,4]])

    def test_predict_no_learn(self):
        learner = EpsilonBanditLearner(epsilon=0.5)
        self.assertEqual([.25,.25,.25,.25],learner.predict(None, [1,2,3,4]))
        self.assertEqual([.25,.25,.25,.25],learner.predict(None, [1,2,3,4]))

    def test_predict_lots_of_actions(self):
        learner = EpsilonBanditLearner(epsilon=0.5)
        self.assertTrue(math.isclose(1, sum(learner.predict(None, list(range(993)))), abs_tol=.001))

    def test_learn_predict_no_epsilon(self):
        learner = EpsilonBanditLearner(epsilon=0)
        learner.learn(None, 2, 1, None)
        learner.learn(None, 1, 2, None)
        learner.learn(None, 3, 3, None)
        self.assertEqual([0,0,1],learner.predict(None, [1,2,3]))

    def test_learn_predict_epsilon(self):
        learner = EpsilonBanditLearner(epsilon=0.1)
        learner.learn(None, 2, 1, None)
        learner.learn(None, 1, 2, None)
        learner.learn(None, 2, 1, None)

        preds = learner.predict(None, [1,2])

        self.assertAlmostEqual(.95,preds[0])
        self.assertAlmostEqual(.05,preds[1])

    def test_learn_score_epsilon(self):
        learner = EpsilonBanditLearner(epsilon=0.1)

        learner.learn(None, 2, 1, None)
        learner.learn(None, 1, 2, None)
        learner.learn(None, 2, 1, None)

        self.assertAlmostEqual(.95,learner.score(None, [1,2], 1))
        self.assertAlmostEqual(.05,learner.score(None, [1,2], 2))

    def test_learn_predict_epsilon_unhashables(self):
        learner = EpsilonBanditLearner(epsilon=0.1)

        learner.learn(None, [2], 1, None)
        learner.learn(None, [1], 2, None)
        learner.learn(None, [2], 1, None)

        preds = learner.predict(None, [[1],[2]])

        self.assertAlmostEqual(.95,preds[0])
        self.assertAlmostEqual(.05,preds[1])

    def test_learn_predict_epsilon_all_equal(self):
        learner = EpsilonBanditLearner(epsilon=0.1)

        learner.learn(None, 2, 1, None)
        learner.learn(None, 1, 2, None)
        learner.learn(None, 2, 3, None)

        self.assertEqual([.5,.5],learner.predict(None, [1,2]))

class UcbBanditLearner_Tests(unittest.TestCase):

    def test_params(self):
        learner = UcbBanditLearner()
        self.assertEqual({ "family": "UCB_bandit" }, learner.params)

    def test_predict_all_actions_first(self):

        learner = UcbBanditLearner()
        actions = [1,2,3]

        self.assertEqual([1/3, 1/3, 1/3],learner.predict(None, actions))
        learner.learn(None, 1, 0, 0)

        self.assertEqual([0,1/2,1/2],learner.predict(None, actions))
        learner.learn(None, 2, 0, 0)

        self.assertEqual([0,  0,  1],learner.predict(None, actions))
        learner.learn(None, 3, 0, 0)

        #the last time all actions have the same value so we pick randomly
        self.assertEqual([1/3, 1/3, 1/3],learner.predict(None, actions))

    def test_score_all_actions_first(self):

        learner = UcbBanditLearner()
        actions = [1,2,3]

        self.assertEqual([1/3,1/3,1/3],[learner.score(None, actions, a) for a in actions])
        learner.learn(None, 1, 0, 0)

        self.assertEqual([0,1/2,1/2],[learner.score(None, actions, a) for a in actions])
        learner.learn(None, 2, 0, 0)

        self.assertEqual([0,0,1],[learner.score(None, actions, a) for a in actions])
        learner.learn(None, 3, 0, 0)

        #the last time all actions have the same value so we pick randomly
        self.assertEqual([1/3,1/3,1/3],[learner.score(None, actions, a) for a in actions])

    def test_learn_predict_best1(self):
        learner = UcbBanditLearner()
        actions = [1,2,3,4]

        learner.learn(None, 1, 1, None)
        learner.learn(None, 2, 1, None)
        learner.learn(None, 3, 1, None)
        learner.learn(None, 4, 1, None)

        self.assertEqual([0.25,0.25,0.25,0.25], learner.predict(None, actions))

    def test_learn_predict_best2(self):
        learner = UcbBanditLearner()
        actions = [1,2,3,4]

        learner.learn(None, 1, 0, None)
        learner.learn(None, 2, 0, None)
        learner.learn(None, 3, 0, None)
        learner.learn(None, 4, 1, None)

        self.assertEqual([0, 0, 0, 1], learner.predict(None, actions))

    def test_learn_predict_best3(self):
        learner = UcbBanditLearner()
        actions = [1,2,3,4]

        learner.learn(None, 1, 0, None)
        learner.learn(None, 2, 0, None)
        learner.learn(None, 3, 0, None)
        learner.learn(None, 4, 1, None)
        learner.learn(None, 1, 0, None)
        learner.learn(None, 2, 0, None)
        learner.learn(None, 3, 0, None)
        learner.learn(None, 4, 1, None)

        self.assertEqual([0, 0, 0, 1], learner.predict(None, actions))

    def test_learn_score_best2(self):
        learner = UcbBanditLearner()
        actions = [1,2,3,4]

        learner.learn(None, 1, 0, None)
        learner.learn(None, 2, 0, None)
        learner.learn(None, 3, 0, None)
        learner.learn(None, 4, 1, None)

        self.assertEqual(0 , learner.score(None, actions, 1))
        self.assertEqual(0 , learner.score(None, actions, 2))
        self.assertEqual(0 , learner.score(None, actions, 3))
        self.assertEqual(1 , learner.score(None, actions, 4))

class FixedLearner_Tests(unittest.TestCase):

    def test_params(self):
        self.assertEqual({"family":"fixed"}, FixedLearner([1/2,1/2]).params)

    def test_create_errors(self):
        with self.assertRaises(AssertionError):
            FixedLearner([1/3, 1/2])

        with self.assertRaises(AssertionError):
            FixedLearner([-1, 2])

    def test_score(self):
        learner = FixedLearner([1/3,1/6,3/6])
        self.assertEqual(1/3 , learner.score(None, [1,2,3],1))
        self.assertEqual(1/6 , learner.score(None, [1,2,3],2))
        self.assertEqual(3/6 , learner.score(None, [1,2,3],3))

    def test_predict(self):
        learner = FixedLearner([1/3,1/3,1/3])
        self.assertEqual([1/3,1/3,1/3], learner.predict(None, [1,2,3]))

    def test_learn(self):
        FixedLearner([1/3,1/3,1/3]).learn(None, 1, .5, None)

class RandomLearner_Tests(unittest.TestCase):

    def test_params(self):
        self.assertEqual({"family":"random"}, RandomLearner().params)

    def test_score(self):
        learner = RandomLearner()
        self.assertEqual(1/2, learner.score(None, [1,2  ], 2))
        self.assertEqual(1/3, learner.score(None, [1,2,3], 3))

    def test_predict(self):
        learner = RandomLearner()
        self.assertEqual([0.25, 0.25, 0.25, 0.25], learner.predict(None, [1,2,3,4]))

    def test_learn(self):
        learner = RandomLearner()
        learner.learn(2, 1, 1, 1)

if __name__ == '__main__':
    unittest.main()
