from unittest import TestCase


class TestAwsyOpsDeps(TestCase):
    def test_has_invoke(self):
        import invoke