# Configuration

camply reads settings from environment variables. Export them in your shell, pass an `.env` file to `uvx`:

```bash
uvx --env-file .env --from "camply-web[server]" camply serve
```

Docker Compose reads `.env` automatically; start from `docs/examples/.env.example` in the repository. For every available variable and default, see the [Environment Variables reference](../operations/CONFIGURATION.md).

## Authentication

Choose `CAMPLY_AUTH_MODE` before sharing your instance:

| Mode      | Behavior                                                                                         |
| --------- | ------------------------------------------------------------------------------------------------ |
| `none`    | Default. Signs every visitor in as a shared administrator. Use only on a private local instance. |
| `session` | In-app username/password login using signed session cookies.                                     |
| `auth0`   | Multi-user login via your Auth0 tenant, with optional `CAMPLY_INVITE_ONLY=true`.                 |

For `session` login, set your own credentials and a signing secret of at least 32 characters:

```dotenv
CAMPLY_AUTH_MODE=session
CAMPLY_LOGIN_USERNAME=your-username
CAMPLY_LOGIN_PASSWORD=replace-with-your-password
CAMPLY_SESSION_SECRET=replace-with-a-random-secret-at-least-32-characters
```

If you host `session` login over plain HTTP (not behind HTTPS), set `CAMPLY_SESSION_COOKIE_SECURE=false` and add your exact frontend origin to `CAMPLY_CORS_ORIGINS` (for example, `'["http://127.0.0.1:8000"]'` in standalone mode). Keep secure cookies enabled behind HTTPS.

For `auth0` login, set `CAMPLY_AUTH0_DOMAIN`, `CAMPLY_AUTH0_AUDIENCE`, and `CAMPLY_AUTH0_CLIENT_ID`, and allow your frontend origin in Auth0's callback and logout URLs.

## Notifications

Users choose either **Pushover** or **ntfy** in their account settings.

| Variable                       | Purpose                                                                                | Default                                                    |
| ------------------------------ | -------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `PUSHOVER_APP_TOKEN`           | Pushover application token (needed by API and worker)                                  | Unset                                                      |
| `CAMPLY_NTFY_SUBSCRIPTION_URL` | Public ntfy server shown to users                                                      | `https://ntfy.sh`                                          |
| `CAMPLY_NTFY_PUBLISH_URL`      | Optional private server URL used only when publishing alerts                           | Uses `CAMPLY_NTFY_SUBSCRIPTION_URL`                        |
| `CAMPLY_NOTIFICATION_MODE`     | `summary` (one alert per scan with results link) or `direct` (one alert per site link) | `summary`                                                  |
| `CAMPLY_APP_URL`               | Public frontend base URL used in summary alert links                                   | Standalone: listener URL; Compose: `http://localhost:5173` |

Always set `CAMPLY_APP_URL` to an address your phone or browser can actually open (such as `https://camply.example.com`).

## Storage and polling

| Variable                    | Purpose                                                                           | Default                                                        |
| --------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `CAMPLY_DB_HOST`            | Absolute SQLite file path (standalone) or database hostname (PostgreSQL)          | `~/.local/share/camply/camply.db` (standalone)                 |
| `CAMPLY_ENCRYPTION_KEY`     | Fernet key(s) for encrypting stored user notification secrets (comma-separated)   | Auto-generated `<db>.key` for SQLite; required for PostgreSQL  |
| `CAMPLY_HEARTBEAT_INTERVAL` | Seconds between scheduler discovery heartbeats                                    | `300`                                                          |
| `CAMPLY_TARGET_COOLDOWN`    | Minimum seconds before re-checking the same campground target                     | `55`                                                           |
