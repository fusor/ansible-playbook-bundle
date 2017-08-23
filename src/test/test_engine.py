from unittest import TestCase

from apb import engine


class EngineTests(TestCase):

    def test_is_valid_spec_missing_keys(self):
        # Test
        result = engine.is_valid_spec({})

        # Verify
        self.assertFalse(result)