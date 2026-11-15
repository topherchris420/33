"""Phase 6.1 command-link security harness (items 1.5 and 1.6, software level).

A Python port of the launcher's security implementation
(Firmware/Launcher/src/crypto.h / crypto.cpp) with the same keys, the same
AUTH wire format, the same two-key OVERRIDE, and the same AES-128-CCM
telemetry framing. Like the PN-law cross-check that caught a sign error in
Phase 3, this exists so the C++ implementation is checked by an independent
implementation rather than trusted.

Fidelity to the firmware is enforced by tests/test_crypto_harness.py.

Items covered (all still PENDING on hardware):
  1.5 command-link security: authenticated commands accepted; replayed,
      forged, and wrong-operator commands rejected; two-key OVERRIDE
      requires both operator keys.
  1.6 telemetry crypto round-trip: ENC packets decrypt with the same
      dashboard code path (Firmware/dashboard.py decrypt_enc_packet).
"""

import hmac as hmac_mod
import hashlib
import secrets
import time

# --- bench keys, identical to Firmware/Launcher/src/crypto.cpp --------------
CMD_KEY = bytes([0x33, 0x21, 0x0a, 0x1c, 0x2f, 0x3b, 0x4e, 0x5d,
                 0x69, 0x77, 0x83, 0x9a, 0xa5, 0xb2, 0xc4, 0xd6])
OPERATOR_A_KEY = bytes([0xd1, 0x12, 0xa0, 0xc3, 0x1b, 0xf2, 0x34, 0x45,
                       0x5c, 0x6d, 0x7e, 0x8f, 0x90, 0x01, 0x12, 0x23])
OPERATOR_B_KEY = bytes([0x23, 0x32, 0x21, 0x10, 0x0f, 0x9e, 0x87, 0x76,
                       0x65, 0x54, 0x43, 0x32, 0x21, 0x10, 0x0f, 0x00])
TELEMETRY_KEY = bytes([0xab, 0xcd, 0xef, 0x01, 0x23, 0x45, 0x67, 0x89,
                      0x9a, 0xbc, 0xde, 0xf0, 0x11, 0x22, 0x33, 0x44])

REPLAY_WINDOW = 64
OVERRIDE_VALIDITY_MS = 60000
HMAC_LEN = 32


class CommandAuthenticator:
    """Mirrors LauncherCrypto::authenticate: AUTH,<seq>,<op>,<payload>,<mac>."""

    OPERATORS = {0: CMD_KEY, 1: OPERATOR_A_KEY, 2: OPERATOR_B_KEY}

    def __init__(self):
        self.last_seq = 0

    @staticmethod
    def sign(seq, operator, payload, key):
        signed = f"{seq},{operator},{payload}"
        mac = hmac_mod.new(key, signed.encode('utf-8'), hashlib.sha256).hexdigest()
        return f"AUTH,{seq},{operator},{payload},{mac}"

    def authenticate(self, msg):
        try:
            parts = msg.split(',')
            if parts[0] != 'AUTH' or len(parts) < 5:
                return None
            seq = int(parts[1])
            operator = int(parts[2])
            payload = ','.join(parts[3:-1])
            mac_hex = parts[-1]
        except (ValueError, IndexError):
            return None
        if operator not in self.OPERATORS:
            return None
        if len(mac_hex) != 2 * HMAC_LEN:
            return None
        signed = f"{seq},{operator},{payload}"
        expect = hmac_mod.new(self.OPERATORS[operator], signed.encode('utf-8'),
                               hashlib.sha256).hexdigest()
        if not hmac_mod.compare_digest(expect, mac_hex):
            return None
        if seq <= self.last_seq and self.last_seq - seq < REPLAY_WINDOW:
            return None
        if seq > self.last_seq:
            self.last_seq = seq
        return payload


class OverrideGate:
    """Mirrors LauncherCrypto::authorizeOverride: both keys must sign."""

    def __init__(self):
        self.valid_until_ms = 0

    @staticmethod
    def sign_enabler(nonce_hex, key):
        signed = f"OVERRIDE,enabler,{nonce_hex}"
        return hmac_mod.new(key, signed.encode('utf-8'), hashlib.sha256).hexdigest()

    def authorize(self, nonce_hex, mac_a_hex, mac_b_hex, now_ms):
        signed = f"OVERRIDE,enabler,{nonce_hex}"
        for key, mac in ((OPERATOR_A_KEY, mac_a_hex), (OPERATOR_B_KEY, mac_b_hex)):
            expect = hmac_mod.new(key, signed.encode('utf-8'), hashlib.sha256).hexdigest()
            if len(mac) != 2 * HMAC_LEN or not hmac_mod.compare_digest(expect, mac):
                return False
        self.valid_until_ms = now_ms + OVERRIDE_VALIDITY_MS
        return True

    def valid(self, now_ms):
        return self.valid_until_ms != 0 and now_ms < self.valid_until_ms


def build_override_message(nonce_hex=None):
    """Build a valid two-key OVERRIDE message (for tests and bench drives)."""
    nonce = nonce_hex or secrets.token_hex(8)
    mac_a = OverrideGate.sign_enabler(nonce, OPERATOR_A_KEY)
    mac_b = OverrideGate.sign_enabler(nonce, OPERATOR_B_KEY)
    return f"OVERRIDE,enabler,{nonce},{mac_a},{mac_b}"


def make_enc_packet(plaintext, counter=None):
    """Build an ENC,<iv>,<ct> telemetry packet exactly as the launcher does
    (AES-128-CCM, 14-byte tag, iv = 4-byte counter + 4-byte clock) using the
    same key. Returns the wire string."""
    from cryptography.hazmat.primitives.ciphers.aead import AESCCM
    if counter is None:
        counter = secrets.randbits(32)
    iv = counter.to_bytes(4, 'big') + int(time.time() * 1000 % 2**32).to_bytes(4, 'big')
    aead = AESCCM(TELEMETRY_KEY, tag_length=14)
    ct = aead.encrypt(iv, plaintext.encode('utf-8'), None)
    return f"ENC,{iv.hex()},{ct.hex()}"


if __name__ == '__main__':
    import json
    auth = CommandAuthenticator()
    results = {}
    # valid command
    msg = auth.sign(1, 0, 'launch', CMD_KEY)
    results['valid_command'] = auth.authenticate(msg)
    # replay
    results['replay_rejected'] = auth.authenticate(msg) is None
    # forged hmac
    forged = 'AUTH,2,0,launch,' + '0' * 64
    results['forged_rejected'] = auth.authenticate(forged) is None
    # wrong operator
    msg3 = CommandAuthenticator.sign(3, 3, 'launch', CMD_KEY)
    results['unknown_operator_rejected'] = auth.authenticate(msg3) is None
    # two-key override
    gate = OverrideGate()
    good = build_override_message()
    parts = good.split(',')
    results['override_both_keys'] = gate.authorize(parts[2], parts[3], parts[4], 0)
    results['override_one_key_only'] = not gate.authorize(
        parts[2], parts[3], parts[3], 0)
    print(json.dumps(results, indent=2))
