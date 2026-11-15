#ifndef LAUNCHER_CRYPTO_H
#define LAUNCHER_CRYPTO_H

/*
 * Phase 5 combat command-and-control security (docs/MILITARY/C2_CRYPTO.md).
 *
 * Provides, on the launcher ESP32 (mbedtls):
 * - HMAC-SHA256 command authentication with a monotonic sequence number and a
 *   replay-rejection window (blocks captured-command replay);
 * - AES-128-CCM authenticated encryption for the telemetry downlink;
 * - the wartime two-key OVERRIDE mode: a weapons command is accepted only
 *   when BOTH operator keys (two digital arms, or a physical arm plus one
 *   digital key) have signed it.
 *
 * Keys are provisioned constants; they MUST be changed before fielding
 * (the defaults exist only for bench bring-up and are documented).
 * Compile-verified only; not bench-tested (Phase 6.1).
 */

#include <Arduino.h>
#include <stdint.h>
#include <string.h>
#include "mbedtls/md.h"
#include "mbedtls/ccm.h"

class LauncherCrypto {
public:
    static constexpr size_t HMAC_LEN = 32;      // SHA-256 bytes
    static constexpr size_t KEY_LEN = 16;       // AES-128 / HMAC key
    static constexpr uint32_t REPLAY_WINDOW = 64;

    // Provisioned keys. CHANGE BEFORE FIELDING: these defaults are for
    // bench bring-up only and are recorded in docs/MILITARY/C2_CRYPTO.md.
    static const uint8_t CMD_KEY[KEY_LEN];      // weapons-command signing key
    static const uint8_t OPERATOR_A_KEY[KEY_LEN]; // digital arm #1
    static const uint8_t OPERATOR_B_KEY[KEY_LEN]; // digital arm #2
    static const uint8_t TELEMETRY_KEY[KEY_LEN];  // AES-CCM downlink key

    static void hmac(const uint8_t *key, size_t key_len,
                    const char *data, size_t data_len,
                    uint8_t out[HMAC_LEN]) {
        mbedtls_md_context_t ctx;
        mbedtls_md_init(&ctx);
        mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
        mbedtls_md_hmac_starts(&ctx, key, key_len);
        mbedtls_md_hmac_update(&ctx, (const uint8_t *)data, data_len);
        mbedtls_md_hmac_finish(&ctx, out);
        mbedtls_md_free(&ctx);
    }

    static bool hmacEqual(const uint8_t a[HMAC_LEN], const uint8_t b[HMAC_LEN]) {
        // constant-time compare
        uint8_t diff = 0;
        for (size_t i = 0; i < HMAC_LEN; i++) diff |= a[i] ^ b[i];
        return diff == 0;
    }

    // ---- command authentication with replay window ------------------------
    // Authenticated command wire format:
    //   AUTH,<seq>,<operator>,<payload>,<hmac_hex>
    // operator: 0 = command key, 1 = operator A, 2 = operator B
    // hmac covers "<seq>,<operator>,<payload>".
    static bool authenticate(const String &msg, uint32_t &out_seq, String &out_payload) {
        int c1 = msg.indexOf(',');
        int c2 = msg.indexOf(',', c1 + 1);
        int c3 = msg.indexOf(',', c2 + 1);
        int c4 = msg.lastIndexOf(',');
        if (c1 < 0 || c2 <= c1 || c3 <= c2 || c4 <= c3) return false;
        String seq_s = msg.substring(c1 + 1, c2);
        String op_s = msg.substring(c2 + 1, c3);
        String payload = msg.substring(c3 + 1, c4);
        String mac_hex = msg.substring(c4 + 1);
        uint32_t seq = (uint32_t)strtoul(seq_s.c_str(), nullptr, 10);
        int op = op_s.toInt();

        const uint8_t *key = nullptr;
        if (op == 0) key = CMD_KEY;
        else if (op == 1) key = OPERATOR_A_KEY;
        else if (op == 2) key = OPERATOR_B_KEY;
        else return false;

        String signed_part = seq_s + "," + op_s + "," + payload;
        uint8_t mac[HMAC_LEN];
        hmac(key, KEY_LEN, signed_part.c_str(), signed_part.length(), mac);

        uint8_t given[HMAC_LEN];
        if (mac_hex.length() != 2 * HMAC_LEN) return false;
        for (size_t i = 0; i < HMAC_LEN; i++) {
            String byte_hex = mac_hex.substring(2 * i, 2 * i + 2);
            given[i] = (uint8_t)strtoul(byte_hex.c_str(), nullptr, 16);
        }
        if (!hmacEqual(mac, given)) return false;

        // replay window: reject sequences at or below the last accepted one,
        // and old sequences inside the sliding window.
        if (seq <= lastSeq) {
            if (lastSeq - seq < REPLAY_WINDOW) return false;
        }
        if (seq > lastSeq) lastSeq = seq;
        out_seq = seq;
        out_payload = payload;
        return true;
    }

    // ---- two-key OVERRIDE -------------------------------------------------
    // OVERRIDE,enabler,<hmacA_hex>,<hmacB_hex> signed by BOTH operator keys
    // over the string "OVERRIDE,enabler,<nonce>". Both must verify; the
    // authorization is valid for OVERRIDE_VALIDITY_MS.
    static constexpr unsigned long OVERRIDE_VALIDITY_MS = 60000;
    static unsigned long overrideUntilMs;
    static bool overrideValid(unsigned long now_ms) {
        return overrideUntilMs != 0 && now_ms < overrideUntilMs;
    }
    static void clearOverride() { overrideUntilMs = 0; }

    static bool authorizeOverride(const String &nonce_hex,
                                  const String &mac_a_hex, const String &mac_b_hex,
                                  unsigned long now_ms) {
        String signed_part = "OVERRIDE,enabler," + nonce_hex;
        uint8_t mac[HMAC_LEN], given[HMAC_LEN];
        hmac(OPERATOR_A_KEY, KEY_LEN, signed_part.c_str(), signed_part.length(), mac);
        if (mac_a_hex.length() != 2 * HMAC_LEN) return false;
        for (size_t i = 0; i < HMAC_LEN; i++) {
            given[i] = (uint8_t)strtoul(mac_a_hex.substring(2 * i, 2 * i + 2).c_str(), nullptr, 16);
        }
        if (!hmacEqual(mac, given)) return false;
        hmac(OPERATOR_B_KEY, KEY_LEN, signed_part.c_str(), signed_part.length(), mac);
        if (mac_b_hex.length() != 2 * HMAC_LEN) return false;
        for (size_t i = 0; i < HMAC_LEN; i++) {
            given[i] = (uint8_t)strtoul(mac_b_hex.substring(2 * i, 2 * i + 2).c_str(), nullptr, 16);
        }
        if (!hmacEqual(mac, given)) return false;
        overrideUntilMs = now_ms + OVERRIDE_VALIDITY_MS;
        return true;
    }

    // ---- AES-128-CCM telemetry downlink -----------------------------------
    // out must have room for len + 14 (tag). Returns ciphertext length incl.
    // tag, or 0 on failure.
    static size_t encryptTelemetry(const uint8_t *in, size_t len,
                                   uint8_t *iv, size_t iv_len,
                                   uint8_t *out, size_t out_cap) {
        if (len + 14 > out_cap) return 0;
        mbedtls_ccm_context ccm;
        mbedtls_ccm_init(&ccm);
        int ok = mbedtls_ccm_setkey(&ccm, MBEDTLS_CIPHER_ID_AES,
                                   TELEMETRY_KEY, 128);
        if (ok != 0) { mbedtls_ccm_free(&ccm); return 0; }
        ok = mbedtls_ccm_encrypt_and_tag(&ccm, len, iv, iv_len,
                                         nullptr, 0, in, out, out + len, 14);
        mbedtls_ccm_free(&ccm);
        return (ok == 0) ? len + 14 : 0;
    }

private:
    static uint32_t lastSeq;
};

#endif // LAUNCHER_CRYPTO_H
