#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `isbd` package."""

import pytest
from multiprocessing import Process
import socket
from time import sleep

from click.testing import CliRunner

from iridiumSBD import iridiumSBD as isbd
from iridiumSBD import cli
from iridiumSBD.directip import server


minimal_full_msg = (
    b'\x01'                 # protocol revision
    b'\x00\x22'             # message length after first 3 bytes: 34
    b'\x01'                 # MO header IEI
    b'\x00\x1c'             # MO header length: 28
    b'\x00\x00\x00\x01'     # CDR reference
    b'1234567890abcde'      # IMEI
    b'\x0c'                 # session status
    b'\x00\x01'             # MOMSN
    b'\x00\x00'             # MTMSN
    b'\x00\x00\x00\x00'     # session epoch
    b'\x02'                 # MO payload IEI
    b'\x00\x00'             # empty payload
)


def test_parse_minimal_MO():
    msg = isbd.IridiumSBD(minimal_full_msg)
    
    assert msg.attributes['header']['IMEI'] == '1234567890abcde'
    assert msg.attributes['header']['session_status'] == 12


def test_parse_nopayload_MO():
    msg = isbd.IridiumSBD(minimal_full_msg[:48])


def test_parse_MO_acknowledgment():
    # Acknowledge success
    ack = b'\x01\x00\x04\x05\x00\x01\x01'
    msg = isbd.IridiumSBD(ack)
    assert msg.attributes['confirmation']['IEI'] == b'\x05'
    assert msg.attributes['confirmation']['status'] == 1

    # Acknowledge failure
    ack = b'\x01\x00\x04\x05\x00\x01\x00'
    msg = isbd.IridiumSBD(ack)
    assert msg.attributes['confirmation']['IEI'] == b'\x05'
    assert msg.attributes['confirmation']['status'] == 0


def test_parse_MT_acknowledgment():
    ack = b'\x01\x00\x1cD\x00\x19\x00\x00\x00\x001234567890abcde\xa5\xb5n\x1a\x00\x01'
    msg = isbd.IridiumSBD(ack)
    assert msg.attributes['confirmation']['IEI'] == b'\x44'
    assert msg.attributes['confirmation']['status'] == 1
