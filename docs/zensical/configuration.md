# Configure your instance

camply reads environment variables. For checkout workflows, copy `docs/examples/.env.example` to `.env` and edit it, then run `UV_ENV_FILE=.env task standalone:run` to load it. For an installed package, export the variables in your shell or use `uv run --no-project --env-file .env camply serve`. Docker Compose reads `.env` automatically for its configured overrides. See the [complete configuration reference](https://github.com/juftin/camply-web/blob/main/docs/operations/CONFIGURATION.md) for all settings and runtime-specific behavior.

## Authentication

Choose `CAMPLY_AUTH_MODE` explicitly when sharing an instance:

| Mode      | Behavior                                                                                             |
| --------- | ---------------------------------------------------------------------------------------------------- |
| `none`    | Default: automatically signs in as a shared administrator. Suitable for your private local instance. |
| `session` | In-app username/password login, with signed session cookies.                                         |
| `auth0`   | Auth0 login using your configured application.                                                       |

For session login, set these values in your environment or `.env`, replacing the examples with your own credentials and a random secret of at least 32 characters:

```dotenv
CAMPLY_AUTH_MODE=session
CAMPLY_LOGIN_USERNAME=your-username
CAMPLY_LOGIN_PASSWORD=replace-with-your-password
CAMPLY_SESSION_SECRET=replace-with-a-random-secret-at-least-32-characters
```

For local HTTP, also set `CAMPLY_SESSION_COOKIE_SECURE=false` and include the exact frontend origin in `CAMPLY_CORS_ORIGINS`, for example `'["http://127.0.0.1:8000"]'` for standalone. Keep secure cookies enabled for HTTPS. Compose provides development session defaults; replace them when sharing the instance.

For Auth0, set `CAMPLY_AUTH0_DOMAIN`, `CAMPLY_AUTH0_AUDIENCE`, and `CAMPLY_AUTH0_CLIENT_ID`, and configure callback/logout URLs for your frontend origin. Follow the [authentication reference](https://github.com/juftin/camply-web/blob/main/docs/operations/CONFIGURATION.md#-authentication-toggleable) for details.

## Notifications

Set `PUSHOVER_APP_TOKEN` to your Pushover application's token, then configure a Pushover user key in each user's account settings. In distributed deployments, the worker needs the application token.

`CAMPLY_NOTIFICATION_MODE=summary` is the default: new openings are summarized with a link to scan results. `direct` sends individual booking-link alerts. Set `CAMPLY_APP_URL` to your reachable frontend URL; standalone defaults to its listener, while Compose's development default is `http://localhost:5173` and should be changed to your actual frontend address.

## Storage and polling

| Setting                     | Purpose                                                                             |
| --------------------------- | ----------------------------------------------------------------------------------- |
| `CAMPLY_DB_HOST`            | Absolute SQLite file path in standalone mode; database hostname in PostgreSQL mode. |
| `CAMPLY_HEARTBEAT_INTERVAL` | Scheduler heartbeat in seconds; default `300`.                                      |
| `CAMPLY_TARGET_COOLDOWN`    | Minimum target polling cooldown in seconds; default `55`.                           |
| `CAMPLY_APP_URL`            | Public frontend URL used in notification links.                                     |

Standalone manages SQLite and local background checks. Distributed mode uses PostgreSQL and Celery/Valkey; the Compose file wires these services together. See [runtime selection](https://github.com/juftin/camply-web/blob/main/docs/operations/CONFIGURATION.md#runtime-selection) before customizing deployment roles.
