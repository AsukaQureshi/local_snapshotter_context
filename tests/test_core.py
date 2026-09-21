"""Tests for local_snapshotter_context.core."""

import unittest

from local_snapshotter_context import SnapshotError, capture, restore


class CaptureRestoreRoundTripTests(unittest.TestCase):
    def test_round_trip_flat_dict(self):
        original = {"alpha": "one", "beta": 2, "gamma": [1, 2, 3], "delta": None}
        token = capture(original)
        self.assertIsInstance(token, str)
        self.assertEqual(restore(token), original)

    def test_round_trip_empty_dict(self):
        token = capture({})
        self.assertEqual(restore(token), {})

    def test_round_trip_nested_json_values(self):
        original = {"nested": {"list": [1, {"x": "y"}], "bool": True}}
        token = capture(original)
        self.assertEqual(restore(token), original)

    def test_round_trip_unicode_values(self):
        original = {"greeting": "héllo wörld", "emoji": "🐍"}
        token = capture(original)
        self.assertEqual(restore(token), original)

    def test_round_trip_uncompressed(self):
        original = {"key": "value", "number": 42}
        token = capture(original, compress=False)
        self.assertEqual(restore(token), original)

    def test_token_is_ascii_only(self):
        token = capture({"key": "héllo"})
        try:
            token.encode("ascii")
        except UnicodeEncodeError:
            self.fail("token is not ASCII-only")

    def test_restore_returns_fresh_dict(self):
        original = {"a": 1}
        token = capture(original)
        first = restore(token)
        second = restore(token)
        self.assertEqual(first, second)
        first["a"] = 99
        self.assertEqual(second["a"], 1)

    def test_restore_does_not_share_reference_with_original(self):
        original = {"nested": [1, 2]}
        token = capture(original)
        decoded = restore(token)
        decoded["nested"].append(3)
        self.assertEqual(original["nested"], [1, 2])


class CaptureErrorTests(unittest.TestCase):
    def test_non_string_key_raises_type_error(self):
        with self.assertRaises(TypeError):
            capture({1: "value"})

    def test_non_serializable_value_raises_type_error(self):
        with self.assertRaises(TypeError):
            capture({"key": object()})


class RestoreErrorTests(unittest.TestCase):
    def test_restore_rejects_non_string_token(self):
        with self.assertRaises(SnapshotError):
            restore(123)

    def test_restore_rejects_invalid_base64(self):
        with self.assertRaises(SnapshotError):
            restore("not-valid-base64!")

    def test_restore_rejects_unknown_prefix(self):
        import base64

        bad_token = base64.urlsafe_b64encode(b"OTHER:payload").decode("ascii")
        with self.assertRaises(SnapshotError):
            restore(bad_token)

    def test_restore_rejects_non_object_payload(self):
        import base64
        import json
        import zlib

        payload = json.dumps([1, 2, 3]).encode("utf-8")
        compressed = zlib.compress(payload)
        raw = b"LSC1:" + compressed
        bad_token = base64.urlsafe_b64encode(raw).decode("ascii")
        with self.assertRaises(SnapshotError):
            restore(bad_token)

    def test_restore_accepts_string_keys_in_payload(self):
        import base64
        import json
        import zlib

        payload = json.dumps({"1": "value"}).encode("utf-8")
        compressed = zlib.compress(payload)
        raw = b"LSC1:" + compressed
        token = base64.urlsafe_b64encode(raw).decode("ascii")
        self.assertEqual(restore(token), {"1": "value"})


class DeterministicTokenTests(unittest.TestCase):
    def test_same_input_produces_same_token(self):
        context = {"b": 2, "a": 1}
        token1 = capture(context)
        token2 = capture(context)
        self.assertEqual(token1, token2)

    def test_key_order_does_not_affect_token(self):
        context1 = {"a": 1, "b": 2}
        context2 = {"b": 2, "a": 1}
        self.assertEqual(capture(context1), capture(context2))


if __name__ == "__main__":
    unittest.main()
