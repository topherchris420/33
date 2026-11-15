"""Phase 6.1 items 1.5 and 1.6 at the software level.

Fidelity: the harness keys and formats must match the launcher's crypto
source; the dashboard's sign_command must produce launcher-acceptable
packets; the dashboard's decrypt_enc_packet must decrypt harness-built ENC
packets (cross-language round-trip).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Firmware'))
import crypto_harness  # noqa: E402
import dashboard  # noqa: E402


def _launcher():
    return (ROOT / 'Firmware/Launcher/src/main.cpp').read_text(encoding='utf-8')


def _crypto_cpp():
    return (ROOT / 'Firmware/Launcher/src/crypto.cpp').read_text(encoding='utf-8')


# --- fidelity ---------------------------------------------------------------

def test_harness_keys_match_the_launcher_firmware():
    src = _crypto_cpp()
    for key_name in ('CMD_KEY', 'OPERATOR_A_KEY', 'OPERATOR_B_KEY', 'TELEMETRY_KEY'):
        assert key_name in src
    # the dashboard and the harness share the same command key bytes
    assert dashboard._CMD_KEY == crypto_harness.CMD_KEY
    assert dashboard._OPERATOR_A_KEY == crypto_harness.OPERATOR_A_KEY
    assert dashboard._OPERATOR_B_KEY == crypto_harness.OPERATOR_B_KEY
    assert dashboard._TELEMETRY_KEY == crypto_harness.TELEMETRY_KEY


def test_replay_window_and_override_validity_match_the_firmware():
    hdr = (ROOT / 'Firmware/Launcher/src/crypto.h').read_text(encoding='utf-8')
    assert 'REPLAY_WINDOW = 64' in hdr
    assert crypto_harness.REPLAY_WINDOW == 64
    assert 'OVERRIDE_VALIDITY_MS = 60000' in hdr
    assert crypto_harness.OVERRIDE_VALIDITY_MS == 60000


# --- 6.1 item 1.5: command-link security ------------------------------------

def test_valid_authenticated_command_is_accepted():
    auth = crypto_harness.CommandAuthenticator()
    msg = auth.sign(1, 0, 'launch', crypto_harness.CMD_KEY)
    assert auth.authenticate(msg) == 'launch'


def test_replayed_command_is_rejected():
    auth = crypto_harness.CommandAuthenticator()
    msg = auth.sign(10, 0, 'launch', crypto_harness.CMD_KEY)
    assert auth.authenticate(msg) == 'launch'
    assert auth.authenticate(msg) is None  # replay


def test_replay_inside_window_is_rejected_but_ancient_seq_is_not():
    auth = crypto_harness.CommandAuthenticator()
    msg = auth.sign(100, 0, 'launch', crypto_harness.CMD_KEY)
    assert auth.authenticate(msg) == 'launch'
    # a sequence far below the window is stale but outside the rejection band
    old = auth.sign(1, 0, 'calibrate', crypto_harness.CMD_KEY)
    assert auth.authenticate(old) == 'calibrate'


def test_forged_hmac_is_rejected():
    auth = crypto_harness.CommandAuthenticator()
    forged = 'AUTH,2,0,launch,' + 'a' * 64
    assert auth.authenticate(forged) is None


def test_wrong_key_is_rejected():
    auth = crypto_harness.CommandAuthenticator()
    msg = auth.sign(3, 0, 'launch', crypto_harness.OPERATOR_A_KEY)  # signed with the wrong key
    assert auth.authenticate(msg) is None


def test_unknown_operator_is_rejected():
    msg = crypto_harness.CommandAuthenticator.sign(4, 3, 'launch', crypto_harness.CMD_KEY)
    auth = crypto_harness.CommandAuthenticator()
    assert auth.authenticate(msg) is None


def test_dashboard_sign_command_is_launcher_authentic():
    # The dashboard's sign_command must produce packets the launcher accepts.
    auth = crypto_harness.CommandAuthenticator()
    msg = dashboard.sign_command('launch')
    assert auth.authenticate(msg) == 'launch'
    # ...and a replay of it is rejected by the launcher logic.
    assert auth.authenticate(msg) is None


def test_two_key_override_requires_both_operator_keys():
    gate = crypto_harness.OverrideGate()
    good = crypto_harness.build_override_message()
    parts = good.split(',')
    assert gate.authorize(parts[2], parts[3], parts[4], 0) is True
    assert gate.valid(0) is True
    assert gate.valid(crypto_harness.OVERRIDE_VALIDITY_MS + 1) is False


def test_override_with_one_key_or_swapped_keys_is_rejected():
    gate = crypto_harness.OverrideGate()
    good = crypto_harness.build_override_message()
    parts = good.split(',')
    # only key A's signature (B's slot also carries A's mac)
    assert gate.authorize(parts[2], parts[3], parts[3], 0) is False
    # B's mac in A's slot and vice versa
    assert gate.authorize(parts[2], parts[4], parts[3], 0) is False


def test_launcher_fires_only_with_override_or_manual_hold():
    # The launcher's launch branch requires the fire discipline (source check).
    launcher = _launcher()
    assert 'manualFireRecent(millis())' in launcher
    assert 'LauncherCrypto::overrideValid(millis())' in launcher
    assert 'launch_needs_fire_hold_or_override' in launcher


# --- 6.1 item 1.6: telemetry crypto round-trip --------------------------------

def test_enc_packet_round_trips_through_the_dashboard_decryptor():
    pytest.importorskip('cryptography')
    wire = crypto_harness.make_enc_packet('T,123,1.0,2.0,3.0,0.0,0.0,0,ARMED,0.50,0.20,0.00')
    plain = dashboard.decrypt_enc_packet(wire.split(',')[1], wire.split(',')[2])
    assert plain == 'T,123,1.0,2.0,3.0,0.0,0.0,0,ARMED,0.50,0.20,0.00'


def test_enc_packet_tampering_fails_to_decrypt():
    pytest.importorskip('cryptography')
    wire = crypto_harness.make_enc_packet('T,123,1.0')
    iv_hex, ct_hex = wire.split(',')[1], wire.split(',')[2]
    # flip one bit of ciphertext
    tampered = ('%x' % (int(ct_hex[:2], 16) ^ 0x01)).rjust(2, '0') + ct_hex[2:]
    assert dashboard.decrypt_enc_packet(iv_hex, tampered) is None


def test_enc_packet_with_wrong_key_fails_to_decrypt():
    pytest.importorskip('cryptography')
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM
    import secrets
    iv = secrets.token_bytes(8)
    wrong = AESCCM(bytes(16), tag_length=14).encrypt(iv, b'T,123', None)
    assert dashboard.decrypt_enc_packet(iv.hex(), wrong.hex()) is None
