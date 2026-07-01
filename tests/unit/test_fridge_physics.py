"""Tests unitaires pour le modèle de physique du frigo (fonctions pures).

``FridgePhysics.step(current_c, state, dt_sec, rng)`` est un déclin
exponentiel d'ordre 1 vers un setpoint mobile ; on teste les trois régimes
(OK / DOOR_OPEN / COMPRESSOR_FAIL) avec un bruit à ~0 via un RNG déterministe.
"""
from __future__ import annotations

import math
import random

from simulator.model import FridgePhysics, FridgeState


def _zero_noise() -> FridgePhysics:
    return FridgePhysics(
        setpoint_c=4.0,
        ambient_c=22.0,
        tau_ok_sec=600.0,
        tau_door_sec=600.0,
        tau_fail_sec=3600.0,
        noise_c=0.0,
    )


def test_steady_state_returns_to_setpoint():
    fp = _zero_noise()
    rng = random.Random(0)
    t = 10.0
    for _ in range(720):   # 2 h à 10 s / pas
        t = fp.step(t, FridgeState.OK, 10.0, rng)
    assert abs(t - 4.0) < 0.1


def test_door_open_drives_toward_ambient():
    fp = _zero_noise()
    rng = random.Random(0)
    t = 4.0
    for _ in range(30):    # 5 min
        t = fp.step(t, FridgeState.DOOR_OPEN, 10.0, rng)
    assert t > 4.5         # hausse mesurable
    assert t < 22.0


def test_compressor_fail_monotonic_rise():
    fp = _zero_noise()
    rng = random.Random(42)
    t = 4.0
    falling = 0
    for _ in range(360):   # 1 h à 10 s / pas
        t_next = fp.step(t, FridgeState.COMPRESSOR_FAIL, 10.0, rng)
        if t_next < t:
            falling += 1
        t = t_next
    # avec noise=0 on attend une montée strictement monotone ; quelques égalités tolérées
    assert falling <= 5


def test_tau_matches_exponential_decay_constant():
    """Après ``tau`` secondes, on doit atteindre ~(1 - 1/e) ≈ 63 % de l'écart."""
    fp = _zero_noise()
    rng = random.Random(0)
    t = 4.0
    tau = fp.tau_door_sec                          # 600 s
    steps = int(tau / 10.0)                        # 10-second ticks
    for _ in range(steps):
        t = fp.step(t, FridgeState.DOOR_OPEN, 10.0, rng)
    gap = fp.ambient_c - 4.0
    expected = 4.0 + gap * (1 - math.exp(-1))      # ≈ 15.4
    assert abs(t - expected) < 1.5
