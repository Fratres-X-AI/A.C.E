"""Tests for equivariant encryption prototype."""

import numpy as np

from aegis.crypto.equivariant import (
    EquivariantLinear,
    EquivariantTransform,
    equivariance_error,
    gelu,
    layer_norm,
    relu,
    rms_norm,
    silu,
)


def test_equivariant_linear() -> None:
    dim = 8
    transform = EquivariantTransform(dim=dim)
    weights = np.eye(dim)
    bias = np.zeros(dim)
    layer = EquivariantLinear(weights=weights, bias=bias, transform=transform)
    x = np.random.default_rng(0).standard_normal(dim)
    error = equivariance_error(layer, x, activation="none")
    assert error < 1e-4


def test_equivariant_activations() -> None:
    x = np.array([1.0, -1.0, 0.5, -0.5])
    assert relu(x)[0] == 1.0
    assert gelu(x).shape == x.shape
    assert silu(x).shape == x.shape


def test_norm_layers() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert layer_norm(x).shape == x.shape
    assert rms_norm(x).shape == x.shape


def test_norm_zero_mean() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0])
    normed = layer_norm(x)
    assert abs(float(np.mean(normed))) < 1e-10


def test_transform_inverse() -> None:
    transform = EquivariantTransform(dim=4)
    x = np.array([1.0, 2.0, 3.0, 4.0])
    recovered = transform.inverse(transform.transform(x))
    np.testing.assert_allclose(recovered, x, atol=1e-10)
