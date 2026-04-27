# -*- coding: utf-8 -*-

"""Top-level package for Iridium Short Burst Data."""

__author__ = """Guilherme Castelão"""
__email__ = 'guilherme@castelao.net'
__version__ = '0.1.0'

from .iridiumSBD import (
    IridiumSBD,
    dump,
    is_inbound,
    is_outbound,
    is_truncated,
    message_type,
    valid_isbd,
)

__all__ = [
    'IridiumSBD',
    'dump',
    'is_inbound',
    'is_outbound',
    'is_truncated',
    'message_type',
    'valid_isbd',
]
