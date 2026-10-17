# Pulse CRM

Pulse CRM — макет CRM, разделённый на независимые React и Python-сервисы. Данные пользователей и организаций хранятся в PostgreSQL, который запускается отдельным контейнером Docker Compose.

## Возможности

- React 18 + Vite: форма входа и личный кабинет;
- FastAPI: HTTP API, cookie-сессии и данные дашборда;
- PostgreSQL 16: пользователи, организации, связи пользователей с организациями и сессии;
- связь `User ↔ Organization` — многие ко многим через таблицу `user_organizations`;
- автоматическое создание таблиц и идемпотентное заполнение демонстрационных данных при старте backend;
- отдельные Docker-образы для frontend и backend и постоянный Docker volume для PostgreSQL.

Интерфейс не подключается к базе напрямую. Браузер обращается к backend API, а только backend использует `DATABASE_URL`.

## Быстрый запуск через Docker

Требуются Docker Engine 24+ и Docker Compose v2.

```bash
git clone https://github.com/vetakov/simple.git
cd simple
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Ожидаемые адреса:

- UI: <http://localhost:3000>
- API: <http://localhost:8000>
- API health: <http://localhost:8000/api/health>
- Swagger: <http://localhost:8000/docs>
- PostgreSQL с хоста: `localhost:5432` (для отладки; приложению следует использовать имя сервиса `postgres`).

При первом запуске Compose создаёт `postgres_data`, ждёт health check PostgreSQL, затем backend создаёт таблицы и добавляет демонстрационного пользователя с двумя организациями. Логин берётся из `DEMO_EMAIL` и `DEMO_PASSWORD` (по умолчанию `demo@pulse.crm` / `demo123`).

Остановить сервисы можно без удаления данных:

```bash
docker compose down
```

Для полного сброса локальной базы (удалятся все данные PostgreSQL) используйте только когда это допустимо:

```bash
docker compose down -v
docker compose up --build -d
```

Полная процедура установки и smoke-проверки приведена в [INSTALL.md](INSTALL.md), а описание переменных — в [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md).

## Архитектура

```text
Browser
  │
  └── http://localhost:3000 ──> frontend (React/Nginx)
                                  │ HTTP + HttpOnly cookie
                                  ▼
                         backend (FastAPI :8000)
                                  │ DATABASE_URL
                                  ▼
                         postgres (PostgreSQL :5432)
```

В Compose frontend получает `VITE_API_URL=http://localhost:8000/api` во время сборки. Из браузера имя `backend` недоступно, поэтому клиентский URL должен указывать на опубликованный адрес API. Сам backend подключается к базе по имени Compose-сервиса `postgres`, например `postgresql+psycopg://pulse:pulse_dev_password@postgres:5432/pulse_crm`.

## Данные и связь пользователь–организация

Backend использует SQLAlchemy-модели:

- `users` — учётные записи (email, имя, роль и хеш пароля);
- `organizations` — организации CRM;
- `user_organizations` — таблица связи с составным уникальным ключом `user_id + organization_id`;
- `auth_sessions` — серверные сессии, на которые указывает HttpOnly cookie.

Один пользователь может состоять в нескольких организациях, и одна организация может иметь нескольких пользователей. В ответах `/api/auth/login` и `/api/auth/me` поле `user.organizations` содержит доступные пользователю организации. Данные каждой организации включают стабильный `id`, отображаемое `name` и `slug` (если они присутствуют в версии API). Доступ к дашборду проверяет cookie-сессию.

Маршрут `GET /api/organizations` возвращает организации текущего пользователя. Отдельные операции CRUD организаций пока не являются частью макета. При добавлении CRUD проверяйте membership пользователя на backend, а не доверяйте выбранному `organization_id` из браузера.

При старте backend таблицы создаются через SQLAlchemy `create_all`, а seed выполняется повторно безопасно: существующий email и существующие связи не дублируются. Это удобно для разработки. Для production используйте версионируемые миграции (например, Alembic) перед изменением схемы; `create_all` не заменяет миграции.

## Структура проекта

```text
.
├── backend/
│   ├── app/                 # FastAPI и SQLAlchemy-модели
│   ├── requirements.txt     # Python-зависимости, включая psycopg и SQLAlchemy
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/                 # React-компоненты и страницы
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml       # frontend + backend + postgres
├── .env.example             # значения Compose по умолчанию
├── INSTALL.md
└── docs/ENVIRONMENT.md
```

## API

Все прикладные маршруты имеют префикс `/api`.

| Метод | Маршрут | Авторизация | Назначение |
| --- | --- | --- | --- |
| GET | `/api/health` | нет | Проверка доступности backend; готовность PostgreSQL дополнительно проверяется Compose health check |
| POST | `/api/auth/login` | нет | Вход; JSON `{ "email": "...", "password": "..." }`, устанавливает HttpOnly cookie |
| GET | `/api/auth/me` | cookie | Текущий пользователь и его организации |
| POST | `/api/auth/logout` | cookie | Удаляет серверную сессию и cookie |
| GET | `/api/dashboard` | cookie | KPI, сделки и активность для текущего пользователя |
| GET | `/api/organizations` | cookie | Список организаций текущего пользователя (CRUD пока не реализован) |

При вызове API из отдельного frontend-клиента передавайте cookie: `fetch(url, { credentials: "include" })`. Не выводите cookie, пароли и `DATABASE_URL` в логи.

Пример smoke-проверки:

```bash
curl --fail http://localhost:8000/api/health
curl -i -c /tmp/pulse-cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@pulse.crm","password":"demo123"}' \
  http://localhost:8000/api/auth/login
curl --fail -b /tmp/pulse-cookies.txt http://localhost:8000/api/auth/me
curl --fail -b /tmp/pulse-cookies.txt http://localhost:8000/api/dashboard
curl -b /tmp/pulse-cookies.txt -X POST http://localhost:8000/api/auth/logout
```

## Переменные окружения

Корневой `.env` используется Compose для `POSTGRES_*`, demo-реквизитов и `VITE_API_URL`. Compose сам формирует `DATABASE_URL` для backend из параметров PostgreSQL. Остальные backend-параметры (`FRONTEND_ORIGINS`, cookie и retry) задаются в `docker-compose.yml`, `backend/.env.example` или через настройки деплоя:

| Переменная | Назначение | Значение по умолчанию |
| --- | --- | --- |
| `POSTGRES_DB` | Имя базы | `pulse_crm` |
| `POSTGRES_USER` | Пользователь PostgreSQL | `pulse` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | `pulse_dev_password` |
| `DATABASE_URL` | URL backend к базе; внутри Compose использует host `postgres` | `postgresql+psycopg://pulse:pulse_dev_password@postgres:5432/pulse_crm` |
| `DEMO_EMAIL` | Email seed-пользователя | `demo@pulse.crm` |
| `DEMO_PASSWORD` | Пароль seed-пользователя | `demo123` |
| `FRONTEND_ORIGINS` | Разрешённые CORS origins | `http://localhost:3000,http://127.0.0.1:3000` |
| `VITE_API_URL` | URL API, встраиваемый в frontend при build | `http://localhost:8000/api` |
| `COOKIE_SECURE` | Флаг Secure для cookie | `false` локально, `true` за HTTPS |
| `DB_INIT_RETRIES` | Число попыток подключения при старте backend | `30` |
| `DB_INIT_RETRY_DELAY` | Пауза между попытками инициализации, секунд | `1` |

Секреты не коммитьте. `VITE_*` не являются секретными: Vite встраивает их в JavaScript, доступный браузеру. В production задавайте пароль базы и пароль пользователя через secret manager, ограничивайте CORS конкретными HTTPS-origin и не публикуйте порт PostgreSQL наружу.

## Команды разработки

```bash
# из корня репозитория
docker compose config
docker compose up --build -d
docker compose ps
docker compose logs -f backend
docker compose logs -f postgres
docker compose exec postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose down
```

Проверки исходников без Docker:

```bash
(cd frontend && npm ci && npm run lint && npm run build)
(cd backend && python -m compileall app)
```

Для локального backend без контейнера нужен запущенный PostgreSQL и `DATABASE_URL` с host `localhost`, например `postgresql+psycopg://pulse:pulse_dev_password@localhost:5432/pulse_crm`; подробности — в [INSTALL.md](INSTALL.md).

## Безопасность и production

- Demo-учётные данные предназначены только для разработки; смените их до публикации.
- Используйте TLS на reverse proxy, `COOKIE_SECURE=true`, точный `FRONTEND_ORIGINS` и rate limiting для login.
- Порт `5432` оставляйте доступным только локально/в приватной сети; обычно в production наружу публикуется только frontend или gateway.
- Добавьте Alembic-миграции, резервное копирование и мониторинг PostgreSQL до изменения схемы.
- Хешируйте пароли и храните секреты в secret manager; не передавайте секреты в frontend или `VITE_*`.
- Для нескольких backend-реплик используйте общую PostgreSQL-сессию (текущие `auth_sessions` уже хранятся в БД) и настройте пул подключений.

## Лицензия

Если проект будет опубликован как библиотека или сервис, добавьте выбранную лицензию и правила использования данных клиентов.
