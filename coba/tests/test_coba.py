import unittest
import unittest.mock

class Coba_Tests(unittest.TestCase):

    def test_version(self):
        from coba import __version__
        self.assertEqual("4.9.0",__version__)

if __name__ == '__main__':
    unittest.main()
