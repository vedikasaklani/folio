# Folio

Collaborative notes workspace with page version history (Django + DRF, React later).

## Building

### Run it
```
docker compose up -d                 # Postgres on localhost:5434 (credentials from .env: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
python manage.py migrate
python manage.py createsuperuser     # or register via POST /api/auth/register/
python manage.py runserver
```

### Two logins, on purpose

| URL | Gives you | Used by |
|---|---|---|
| `POST /api/auth/login/` | a **token** string | React app, curl, Postman. The client must send `Authorization: Token <key>` on every request. |
| `/browser-login/` | a **session cookie** | Only the browsable API in a browser tab. |

A browser tab can't attach an `Authorization` header when you navigate to a URL, so a token alone never
authenticates you there. A session cookie is sent automatically. The app itself uses tokens; sessions
exist purely so you can click around `/api/` while developing.
