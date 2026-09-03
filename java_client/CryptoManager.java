package com.hexprotocol.client;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;

/**
 * CryptoManager.java
 *
 * AES-256-GCM application-layer payload encryption, compatible with the
 * companion Python implementation in app/security/crypto_manager.py.
 *
 * Wire format (base64url, no padding, single string):
 *   [ 12-byte nonce ][ ciphertext ][ 16-byte GCM auth tag ]
 *
 * IMPORTANT - key management:
 * Do NOT hardcode PAYLOAD_ENCRYPTION_KEY as a string constant in this
 * class or anywhere in the shipped APK. A key baked into the APK can be
 * extracted by decompiling the app, which defeats the purpose of
 * encrypting the payload. Instead:
 *
 *   1. Preferred: have the server issue a short-lived, per-device
 *      session key after an initial authenticated handshake (e.g. over
 *      TLS, tied to a signed device attestation), store it only in
 *      memory / Android Keystore, and rotate it periodically.
 *   2. At minimum: pull the key from a secure remote config service at
 *      runtime rather than embedding it in source, and rely on HTTPS/TLS
 *      as the primary transport protection (this app-layer encryption is
 *      defense-in-depth, not a replacement for TLS).
 *
 * This class only implements the cipher operations - it deliberately
 * takes the key as a parameter rather than owning a hardcoded secret.
 */
public final class CryptoManager {

    private static final int NONCE_SIZE = 12;   // bytes
    private static final int TAG_SIZE_BITS = 128; // 16-byte GCM tag
    private static final String CIPHER_ALGO = "AES/GCM/NoPadding";
    private static final String KEY_ALGO = "AES";

    private final byte[] aesKey; // 32 bytes, derived from the raw secret

    /**
     * @param rawKey the shared secret string (e.g. the session key issued
     *               by the server). Normalized to 32 bytes via SHA-256 to
     *               match the Python side's key derivation exactly.
     */
    public CryptoManager(String rawKey) {
        this.aesKey = deriveKey(rawKey);
    }

    private static byte[] deriveKey(String rawKey) {
        try {
            MessageDigest sha256 = MessageDigest.getInstance("SHA-256");
            return sha256.digest(rawKey.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new RuntimeException("Failed to derive AES key", e);
        }
    }

    /**
     * Encrypts a plaintext string and returns a base64url (no padding)
     * string containing nonce || ciphertext || tag.
     */
    public String encrypt(String plainData) {
        try {
            byte[] nonce = new byte[NONCE_SIZE];
            new SecureRandom().nextBytes(nonce);

            Cipher cipher = Cipher.getInstance(CIPHER_ALGO);
            SecretKeySpec keySpec = new SecretKeySpec(aesKey, KEY_ALGO);
            GCMParameterSpec spec = new GCMParameterSpec(TAG_SIZE_BITS, nonce);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, spec);

            byte[] cipherTextAndTag = cipher.doFinal(plainData.getBytes(StandardCharsets.UTF_8));

            ByteBuffer buffer = ByteBuffer.allocate(nonce.length + cipherTextAndTag.length);
            buffer.put(nonce);
            buffer.put(cipherTextAndTag);

            return base64UrlEncodeNoPadding(buffer.array());
        } catch (Exception e) {
            throw new RuntimeException("Encryption failed", e);
        }
    }

    /**
     * Reverses encrypt(). Throws RuntimeException (wrapping the
     * underlying cause) if the payload is malformed or the
     * authentication tag fails to verify - treat any exception here as
     * "reject this response/request", never fall back to using
     * unauthenticated data.
     */
    public String decrypt(String encryptedData) {
        try {
            byte[] blob = base64UrlDecode(encryptedData);
            if (blob.length < NONCE_SIZE + 16) {
                throw new IllegalArgumentException("Payload too short to contain nonce + tag");
            }

            byte[] nonce = Arrays.copyOfRange(blob, 0, NONCE_SIZE);
            byte[] cipherTextAndTag = Arrays.copyOfRange(blob, NONCE_SIZE, blob.length);

            Cipher cipher = Cipher.getInstance(CIPHER_ALGO);
            SecretKeySpec keySpec = new SecretKeySpec(aesKey, KEY_ALGO);
            GCMParameterSpec spec = new GCMParameterSpec(TAG_SIZE_BITS, nonce);
            cipher.init(Cipher.DECRYPT_MODE, keySpec, spec);

            byte[] plainBytes = cipher.doFinal(cipherTextAndTag);
            return new String(plainBytes, StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new RuntimeException("Decryption failed - payload may be corrupted, tampered with, or encrypted with a different key", e);
        }
    }

    private static String base64UrlEncodeNoPadding(byte[] data) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(data);
    }

    private static byte[] base64UrlDecode(String data) {
        return Base64.getUrlDecoder().decode(data);
    }

    // --------------------------------------------------------------
    // Example usage (remove or adapt in your real application code):
    //
    //   CryptoManager crypto = new CryptoManager(sessionKey);
    //   String payload = "{\"license_key\":\"HEX-XXXX-XXXX-XXXX\",\"installation_id\":\"...\",\"app_version\":\"1.0.0\"}";
    //   String encrypted = crypto.encrypt(payload);
    //   // send `encrypted` as the request body to POST /api/v1/auth/verify
    //   // ... receive `encryptedResponse` from the server ...
    //   String decrypted = crypto.decrypt(encryptedResponse);
    //   // parse `decrypted` as JSON and handle SUCCESS / INVALID_KEY / etc.
    // --------------------------------------------------------------
}
