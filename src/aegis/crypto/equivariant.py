"""Weight obfuscation demo via orthogonal similarity transforms.

This is **not** encryption and **not** homomorphic encryption. It demonstrates
offline weight transforms ``W' = T W T^{-1}`` that preserve *linear* equivariance
under ``T``. Nonlinear activations (ReLU/GELU/SiLU) are **not** equivariant under
arbitrary orthogonal ``T`` — do not claim otherwise.

Seed is randomized per instance unless ``ACE_EE_SEED`` is set (for reproducible tests).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _gelu(x: FloatArray) -> FloatArray:
    inner = 0.5 * x * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (x + 0.044715 * x**3)))
    return np.asarray(inner, dtype=np.float64)


def _silu(x: FloatArray) -> FloatArray:
    return np.asarray(x / (1.0 + np.exp(-x)), dtype=np.float64)


@dataclass
class EquivariantTransform:
    """Random orthogonal combinatorial transform T and its inverse."""

    dim: int
    ortho: FloatArray = field(init=False)
    ortho_inv: FloatArray = field(init=False)
    perm: NDArray[np.int_] = field(init=False)
    perm_inv: NDArray[np.int_] = field(init=False)

    def __post_init__(self) -> None:
        import os

        seed_raw = os.environ.get("ACE_EE_SEED")
        seed = int(seed_raw) if seed_raw is not None else None
        rng = np.random.default_rng(seed)
        q, _ = np.linalg.qr(rng.standard_normal((self.dim, self.dim)))
        self.ortho = np.asarray(q, dtype=np.float64)
        self.ortho_inv = self.ortho.T
        self.perm = rng.permutation(self.dim)
        self.perm_inv = np.argsort(self.perm)

    @property
    def matrix(self) -> FloatArray:
        """Full transform matrix T = P @ Q (permutation rows then orthogonal)."""
        perm_matrix = np.eye(self.dim, dtype=np.float64)[self.perm]
        return np.asarray(perm_matrix @ self.ortho, dtype=np.float64)

    @property
    def matrix_inv(self) -> FloatArray:
        return np.asarray(self.matrix.T, dtype=np.float64)

    def transform(self, x: FloatArray) -> FloatArray:
        return np.asarray(self.matrix @ x, dtype=np.float64)

    def inverse(self, x: FloatArray) -> FloatArray:
        return np.asarray(self.matrix_inv @ x, dtype=np.float64)

    def transform_matrix(self, weights: FloatArray) -> FloatArray:
        """Transform weight matrix: W' = T @ W @ T^{-1}."""
        t, t_inv = self.matrix, self.matrix_inv
        return np.asarray(t @ weights @ t_inv, dtype=np.float64)


@dataclass
class EquivariantLinear:
    """Linear layer with offline weight transform for equivariance."""

    weights: FloatArray
    bias: FloatArray
    transform: EquivariantTransform
    transformed_weights: FloatArray = field(init=False)
    transformed_bias: FloatArray = field(init=False)

    def __post_init__(self) -> None:
        self.transformed_weights = self.transform.transform_matrix(self.weights)
        self.transformed_bias = self.transform.transform(self.bias)

    def forward_plain(self, x: FloatArray) -> FloatArray:
        return np.asarray(self.weights @ x + self.bias, dtype=np.float64)

    def forward_equivariant(self, tx: FloatArray) -> FloatArray:
        return np.asarray(
            self.transformed_weights @ tx + self.transformed_bias,
            dtype=np.float64,
        )


def relu(x: FloatArray) -> FloatArray:
    return np.asarray(np.maximum(0, x), dtype=np.float64)


def gelu(x: FloatArray) -> FloatArray:
    return _gelu(x)


def silu(x: FloatArray) -> FloatArray:
    return _silu(x)


def layer_norm(x: FloatArray, eps: float = 1e-5) -> FloatArray:
    mean = np.mean(x)
    var = np.var(x)
    return np.asarray((x - mean) / np.sqrt(var + eps), dtype=np.float64)


def rms_norm(x: FloatArray, eps: float = 1e-5) -> FloatArray:
    return np.asarray(x / np.sqrt(np.mean(x**2) + eps), dtype=np.float64)


def equivariance_error(
    layer: EquivariantLinear,
    x: FloatArray,
    activation: str = "none",
    tol: float = 1e-5,
) -> float:
    """Measure ||T(f(x)) - f'(T(x))|| for the *linear* map.

    Only ``activation='none'`` is expected near zero. Nonlinear activations are
    included for experiment only — they are not group-equivariant under random T.
    """
    tx = layer.transform.transform(x)
    f_x = layer.forward_plain(x)
    tf_x = layer.transform.transform(f_x)
    fprime_tx = layer.forward_equivariant(tx)
    if activation == "relu":
        tf_x = relu(tf_x)
        fprime_tx = relu(fprime_tx)
    elif activation == "gelu":
        tf_x = gelu(tf_x)
        fprime_tx = gelu(fprime_tx)
    elif activation == "silu":
        tf_x = silu(tf_x)
        fprime_tx = silu(fprime_tx)
    error = float(np.linalg.norm(tf_x - fprime_tx))
    return error if error > tol else 0.0


def norm_equivariance_error(x: FloatArray, transform: EquivariantTransform) -> float:
    """Diagnostic cosine gap after LayerNorm — not a true equivariance metric."""
    plain = layer_norm(x)
    tx = transform.transform(x)
    transformed = layer_norm(tx)
    cos_sim = float(
        np.dot(plain, transformed)
        / (np.linalg.norm(plain) * np.linalg.norm(transformed) + 1e-12),
    )
    return 1.0 - abs(cos_sim)
