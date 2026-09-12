from __future__ import annotations

import numpy as np
import pytest

from medintelos.model_serialization import (
    canonical_weight_hash,
    weights_from_onnx_bytes,
    weights_to_onnx_bytes,
)


def test_round_trip_preserves_values_and_shape():
    weights = {"layer1": np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)}
    restored = weights_from_onnx_bytes(weights_to_onnx_bytes(weights))
    np.testing.assert_array_equal(restored["layer1"], weights["layer1"])
    assert restored["layer1"].shape == weights["layer1"].shape


@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.int32, np.int64])
def test_round_trip_preserves_dtype(dtype):
    weights = {"w": np.array([1, 2, 3], dtype=dtype)}
    restored = weights_from_onnx_bytes(weights_to_onnx_bytes(weights))
    assert restored["w"].dtype == dtype


def test_round_trip_preserves_multiple_named_tensors():
    weights = {
        "encoder.weight": np.random.default_rng(42).normal(size=(8, 4)).astype(np.float32),
        "encoder.bias": np.zeros(4, dtype=np.float32),
        "decoder.weight": np.ones((4, 8), dtype=np.float64),
    }
    restored = weights_from_onnx_bytes(weights_to_onnx_bytes(weights))
    assert set(restored) == set(weights)
    for name in weights:
        np.testing.assert_array_equal(restored[name], weights[name])


def test_empty_weights_round_trip():
    restored = weights_from_onnx_bytes(weights_to_onnx_bytes({}))
    assert restored == {}


def test_round_trip_preserves_exact_float_bits_not_just_approximate_value():
    """The precision problem being fixed: json.dumps(array.tolist()) goes
    through Python's float repr, which is not guaranteed to reconstruct the
    exact same bit pattern in every case. ONNX's binary serialization must
    not lose precision at all -- checked here with a value chosen to be
    awkward in decimal (not exactly representable), not just a round
    number that any serialization would get right by luck."""
    weights = {"w": np.array([0.1 + 0.2, np.pi, 1.0 / 3.0], dtype=np.float64)}
    restored = weights_from_onnx_bytes(weights_to_onnx_bytes(weights))
    assert np.array_equal(restored["w"].view(np.uint64), weights["w"].view(np.uint64)), (
        "bit pattern changed across serialization round-trip"
    )


def test_canonical_hash_is_deterministic():
    weights = {"a": np.array([1.0, 2.0]), "b": np.array([3.0])}
    assert canonical_weight_hash(weights) == canonical_weight_hash(weights)


def test_canonical_hash_is_independent_of_dict_insertion_order():
    forward = {"a": np.array([1.0]), "b": np.array([2.0])}
    backward = {"b": np.array([2.0]), "a": np.array([1.0])}
    assert canonical_weight_hash(forward) == canonical_weight_hash(backward)


def test_canonical_hash_distinguishes_different_dtypes_with_same_values():
    """The exact gap in the old json.dumps-based hash: a float32 array and
    a float64 array with identical values produced identical JSON (and
    therefore identical hashes), silently treating them as the same
    model."""
    as_f32 = {"w": np.array([1.0, 2.0, 3.0], dtype=np.float32)}
    as_f64 = {"w": np.array([1.0, 2.0, 3.0], dtype=np.float64)}
    assert canonical_weight_hash(as_f32) != canonical_weight_hash(as_f64)


def test_canonical_hash_changes_with_any_value_change():
    base = {"w": np.array([1.0, 2.0, 3.0])}
    changed = {"w": np.array([1.0, 2.0, 3.0001])}
    assert canonical_weight_hash(base) != canonical_weight_hash(changed)


def test_canonical_hash_of_empty_weights_is_stable_sha256_of_empty_bytes():
    import hashlib

    assert canonical_weight_hash({}) == hashlib.sha256(b"").hexdigest()


def test_onnx_bytes_are_a_valid_onnx_model():
    """Round-trips through the real onnx library's own parser/checker, not
    just this module's own functions -- confirms the output is genuinely
    standard ONNX, not merely bytes this module happens to be able to read
    back itself."""
    import onnx

    weights = {"w": np.array([1.0, 2.0], dtype=np.float32)}
    data = weights_to_onnx_bytes(weights)
    model = onnx.ModelProto()
    model.ParseFromString(data)
    onnx.checker.check_model(model, full_check=False)
    assert model.graph.initializer[0].name == "w"
