# HEX PROTOCOL

License key administration platform: a dark, modern admin dashboard, a
Python FastAPI backend, PostgreSQL storage, and an encrypted verification
API for a separate Java/Android client. This repo does **not** contain
any Android app code or UI — only the server side and a `CryptoManager.java`
helper meant to be dropped into your existing Android project.

---

## 1. What's included

```
app/
  main.py              FastAPI app, startup wiring, admin auto-seed
  database.py          SQLAlchemy engine/session, init_db()
  config.py            Env-var driven settings
  schemas.py           Pydantic request/response models
  dependencies.py      Auth dependency, client-IP helper
  models/              License, Device, Log, Admin (SQLAlchemy)
  routes/
    auth_api.py         POST /api/v1/auth/verify  (Java client, encrypted)
    admin_pages.py       Server-rendered dashboard pages
    admin_auth_routes.py Admin login/logout
    admin_api.py          JSON API consumed by the dashboard's JS
  services/
    license_service.py   Key generation & duration logic
    device_service.py     Verify + auto-register + device-mismatch logic
  security/
    crypto_manager.py     AES-256-GCM encrypt/decrypt (Python side)
    admin_auth.py          bcrypt password hashing + signed session cookie
  admin/
    templates/            Jinja2 templates (dashboard, keys, generate, devices, logs, settings, login)
    static/                CSS + vanilla JS for the dashboard

java_client/
  CryptoManager.java    AES-256-GCM encrypt/decrypt, wire-compatible with crypto_manager.py

requirements.txt
railway.json
Procfile
.env.example
```

---

## 2. How the license system works

- **License keys** look like `HEX-XXXX-XXXX-XXXX` and are generated from
  the **Generate Keys** page with a duration: 1 Hour, Custom Hours, 1 Day,
  Custom Days, 7 Days, 30 Days, or Lifetime.
- **Expiry** starts counting from the moment a key is *generated* (not
  first used). If you'd rather have expiry start on first activation,
  see the comment in `services/license_service.create_licenses`.
- **Device binding**: the first successful `/api/v1/auth/verify` call for
  a given key automatically registers the `installation_id` sent by your
  Android app. Every later call must use that same `installation_id`, or
  the API returns `DEVICE_MISMATCH`. An admin can reset the binding from
  the License Keys or Registered Devices pages, freeing the key to bind
  to a new device.
- **Statuses**: `ACTIVE`, `INACTIVE` (deactivated by admin), `BANNED`,
  and `EXPIRED` (derived automatically once `expires_at` has passed).

---

## 3. Zero-config startup

Nothing is required to get the app running:

- **Database**: if `DATABASE_URL` isn't set, the app falls back to a
  local SQLite file and prints a warning to the logs. Attach a Railway
  PostgreSQL plugin for anything beyond a quick test - Railway injects
  `DATABASE_URL` automatically.
- **`SECRET_KEY` / `PAYLOAD_ENCRYPTION_KEY`**: if not set as env vars,
  the app generates them on first boot and saves them in the database
  (`app_secrets` table). They stay stable across restarts and redeploys
  without you setting anything - but if you ever need to move to a new
  database (or want a specific key to hardcode in an offline Android
  build), you can still set them as env vars and they'll take priority.
- **Admin login**: if `ADMIN_USERNAME`/`ADMIN_PASSWORD` aren't set, the
  app creates an account with username `admin` and a random password,
  and prints that password to the Railway deploy logs **once**, on
  first boot only. Check **Deployments → View Logs** right after your
  first deploy and copy it down - then change it from the Settings
  page once you're logged in.

You can still set any of these explicitly (see `.env.example`) if you'd
rather control them yourself.

---

## 4. The encrypted API

### Endpoint

```
POST /api/v1/auth/verify
Content-Type: application/json
```

### Request (encryption enabled — the default)

```json
{ "payload": "<base64url AES-256-GCM blob>" }
```

Where the blob, once decrypted, is JSON:

```json
{
  "license_key": "HEX-AB12-CD34-EF56",
  "installation_id": "a1b2c3d4-...",
  "app_version": "1.0.0"
}
```

### Response (same envelope shape)

```json
{ "payload": "<base64url AES-256-GCM blob>" }
```

Decrypted:

```json
{
  "status": "SUCCESS",
  "message": "License verified.",
  "expires_at": "2026-10-03T12:00:00"
}
```

`status` is one of: `SUCCESS`, `INVALID_KEY`, `EXPIRED`,
`DEVICE_MISMATCH`, `BANNED`, `SERVER_ERROR`.

### Encryption details

- AES-256-GCM, standard library (`cryptography` on the Python side,
  `javax.crypto` on the Java side) — no custom cryptography.
- A fresh random 12-byte nonce is generated for every single encryption
  call.
- Wire format: `base64url( nonce[12] || ciphertext || tag[16] )`, no
  padding.
- The shared secret is normalized to exactly 32 bytes via SHA-256 on
  both sides, so `PAYLOAD_ENCRYPTION_KEY` can be any reasonably long
  random string.
- The authentication tag is verified on every decrypt; a failed/tampered
  payload raises an error and the endpoint responds generically without
  leaking why.

### ⚠️ Key management — read before shipping to production

**Do not hardcode `PAYLOAD_ENCRYPTION_KEY` as a string literal inside
your shipped Android APK.** A key embedded in app code can be recovered
by decompiling the APK, which defeats the purpose of the extra
encryption layer. Two reasonable options, in order of preference:

1. **Short-lived session keys (recommended for real production use):**
   add a lightweight handshake/login step where the server issues a
   per-device, time-limited session key over TLS after some form of
   device attestation, store it only in memory or Android Keystore, and
   rotate it. This repo ships the verify endpoint and crypto primitives;
   wiring up a session-issuance endpoint is a natural next step once you
   decide how you want to attest devices.
2. **Minimum viable approach:** fetch the key from a remote config
   service at app start rather than compiling it into the APK, and treat
   HTTPS/TLS as your primary protection — the AES-256-GCM layer here is
   defense-in-depth on top of TLS, not a replacement for it.

**HTTPS is mandatory** in any case — Railway terminates TLS for you
automatically on the generated `*.up.railway.app` domain or any custom
domain you attach.

---

## 5. Java client usage

```java
CryptoManager crypto = new CryptoManager(sessionKey); // see key management note above

String json = "{\"license_key\":\"HEX-AB12-CD34-EF56\","
            + "\"installation_id\":\"" + installationId + "\","
            + "\"app_version\":\"1.0.0\"}";

String encryptedPayload = crypto.encrypt(json);

// POST { "payload": encryptedPayload } to https://your-app.up.railway.app/api/v1/auth/verify

String decryptedResponse = crypto.decrypt(responseBody.getString("payload"));
// parse decryptedResponse as JSON, branch on "status"
```

`CryptoManager.java` lives in `java_client/` — copy it into your Android
project's source tree (e.g. `app/src/main/java/.../CryptoManager.java`)
and adjust the package name to match your app.

---

## 6. Local development

```bash
python -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum set SECRET_KEY, PAYLOAD_ENCRYPTION_KEY,
# ADMIN_USERNAME, ADMIN_PASSWORD. Without DATABASE_URL set, the app
# falls back to a local SQLite file for convenience.

uvicorn app.main:app --reload
```

Visit `http://localhost:8000/admin/login`. On first boot, if the
`admins` table is empty, the app seeds a single admin account from
`ADMIN_USERNAME` / `ADMIN_PASSWORD`.

---

## 7. Deploying: GitHub → Railway

1. **Push this project to a GitHub repository.**
2. **Create a new Railway project** → "Deploy from GitHub repo" → select
   the repo.
3. **Add a PostgreSQL plugin** to the project (Railway → "+ New" →
   "Database" → "PostgreSQL"). Railway automatically injects
   `DATABASE_URL` into your service's environment — you don't need to
   set it by hand.
4. **That's it — no environment variables are required.** See section 3
   above. If you want to control the admin login or the encryption key
   yourself instead of letting the app generate them, set them now:
   `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`, `PAYLOAD_ENCRYPTION_KEY`.
5. **Deploy.** Railway detects `railway.json` / `Procfile` and runs:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. **Open the deploy logs** (Railway → Deployments → View Logs) and look
   for a block like:
   ```
   ============================================================
   No ADMIN_USERNAME/ADMIN_PASSWORD set - generated one for you:
     username: admin
     password: aB3xQ...
   Save this now - it will not be shown again. Change it from
   the Settings page after your first login.
   ============================================================
   ```
   That only appears once, on the very first successful boot. If you
   don't see it, an admin account already exists (or you set
   `ADMIN_USERNAME`/`ADMIN_PASSWORD` yourself).
7. Visit `https://<your-app>.up.railway.app/admin/login` and log in with
   those credentials.
8. **Point your Android app** at
   `https://<your-app>.up.railway.app/api/v1/auth/verify`.

### Post-deploy checklist

- [ ] Log into `/admin/login` with the credentials from the deploy logs,
      then change the password from **Settings** right away.
- [ ] Confirm a PostgreSQL plugin is attached (check the logs for
      "Database connection successful" rather than a SQLite warning) -
      otherwise your keys/devices/logs won't survive the next deploy.
- [ ] Confirm `ENCRYPTION_ENABLED=true` in production.
- [ ] Generate a batch of license keys from **Generate Keys** and test
      one end-to-end with `CryptoManager.java`.
- [ ] Review the key-management note in section 4 before you finalize
      how the Android app obtains `PAYLOAD_ENCRYPTION_KEY` — you can
      read the auto-generated value back out via a one-off admin/DB
      query if you need to hardcode it for testing, but see the warning
      there about doing that in a real shipped APK.

---

## 8. Database schema

| Table      | Columns |
|------------|---------|
| `licenses` | id, license_key, status, note, duration_label, created_at, activated_at, expires_at |
| `devices`  | id, license_id, installation_id, app_version, registered_at, last_login |
| `logs`     | id, license_id, installation_id, source_ip, status, created_at |
| `admins`   | id, username, password_hash, created_at |

Tables are created automatically via SQLAlchemy `Base.metadata.create_all()`
on startup. For a larger project you'd typically move to Alembic
migrations instead — the models are already structured to make that
straightforward to add later.
