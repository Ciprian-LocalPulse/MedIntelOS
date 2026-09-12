"""Standardized model weight serialization via ONNX.

Replaces the previous ad-hoc approach: `federated.py`'s weight dicts
(`Dict[str, np.ndarray]`) had no real serialization path at all — the only
thing touching them was `_hash_model()`'s `json.dumps({k: v.tolist()...})`,
used solely for a hash, not for storage or transport. That approach also
has a real precision problem: `json.dumps` renders floats through Python's
`repr`, which is not guaranteed to round-trip every float64 bit pattern
identically across platforms/versions, and silently loses all dtype
information (a float32 array and a float64 array with the same values
produce the same JSON).

This module uses ONNX's `ModelProto`/`TensorProto` as a portable container
for named weight tensors — the standard pattern real ONNX checkpoints use
for storing initializers, just without any computational graph nodes (there
is nothing to compute; this is purely a weight container). Serialization is
exact: dtype and every bit of every value round-trips losslessly, verified
in tests/test_model_serialization.py.

**Boundary:** this is a serialization format, not a transport protocol.
There is still no network boundary between MedIntelOS's coordinator and
participants (see federated.py's module docstring and docs/ROADMAP.md) —
these bytes aren't sent anywhere yet. This is what would be sent, once a
real transport exists.
"""

from __future__ import annotations

import hashlib
from typing import Dict

import numpy as np
import onnx
from onnx import ModelProto, helper, numpy_helper


def weights_to_onnx_bytes(weights: Dict[str, np.ndarray]) -> bytes:
    """Serializes a named-tensor weight dict to ONNX ModelProto bytes."""
    initializers = [
        numpy_helper.from_array(array, name=name) for name, array in weights.items()
    ]
    graph = helper.make_graph(
        nodes=[],
        name="medintelos_federated_weights",
        inputs=[],
        outputs=[],
        initializer=initializers,
    )
    model = helper.make_model(graph, producer_name="medintelos")
    model.ir_version = onnx.IR_VERSION
    result: bytes = model.SerializeToString()
    return result


def weights_from_onnx_bytes(data: bytes) -> Dict[str, np.ndarray]:
    """Deserializes ONNX ModelProto bytes back into a named-tensor weight
    dict, exactly as produced by `weights_to_onnx_bytes` (dtype and values
    preserved exactly)."""
    model = ModelProto()
    model.ParseFromString(data)
    return {
        initializer.name: numpy_helper.to_array(initializer)
        for initializer in model.graph.initializer
    }


def canonical_weight_hash(weights: Dict[str, np.ndarray]) -> str:
    """Deterministic SHA-256 over the ONNX-serialized weights, for use as
    `FederatedCoordinator`'s model integrity hash. Sorting by name first
    keeps the hash independent of dict insertion order; ONNX serialization
    itself keeps it independent of the float-repr issues `json.dumps` had.
    """
    if not weights:
        return hashlib.sha256(b"").hexdigest()
    ordered = {name: weights[name] for name in sorted(weights)}
    return hashlib.sha256(weights_to_onnx_bytes(ordered)).hexdigest()
