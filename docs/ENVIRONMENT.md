# Настройка окружения Pulse CRM

Проект состоит из React frontend, FastAPI backend и PostgreSQL. Docker Compose подключает контейнеры к общей сети: backend обращается к базе по DNS-имени `postgres`, а браузер — к опубликованному API. Frontend не получает доступ к PostgreSQL.

## Сервисы и сеть

| Сервис | Внутренний адрес | Публикация по умолчанию | Назначение |
| --- | --- | --- | --- |
| `frontend` | `http://frontend:80` | `http://localhost:3000` | React-приложение и Nginx |
| `backend` | `http://backend:8000` | `http://localhost:8000` | FastAPI API |
| `postgres` | `postgres:5432` | `localhost:5432` | PostgreSQL; наружный порт нужен только для локальной диагностики |

`backend` зависит от health check `postgres`. Не подставляйте `backend` или `postgres` в `VITE_API_URL`: это имена Docker-сети, а JavaScript выполняется в браузере на машине пользователя. Для стандартного Compose используйте `http://localhost:8000/api`; для production — публичный HTTPS URL gateway.

## Переменные Compose и backend

Скопируйте корневой пример:

```bash
cp .env.example .env
```

| Переменная | Где используется | Назначение | Пример |
| --- | --- | --- | --- |
| `POSTGRES_DB` | `postgres`, Compose | Имя создаваемой базы | `pulse_crm` |
| `POSTGRES_USER` | `postgres`, Compose | Пользователь PostgreSQL | `pulse` |
| `POSTGRES_PASSWORD` | `postgres`, Compose | Пароль PostgreSQL | `pulse_dev_password` |
| `DATABASE_URL` | `backend` | SQLAlchemy URL с драйвером psycopg | `postgresql+psycopg://pulse:pulse_dev_password@postgres:5432/pulse_crm` |
| `DEMO_EMAIL` | `backend` | Email демонстрационного пользователя | `demo@pulse.crm` |
| `DEMO_PASSWORD` | `backend` | Пароль демонстрационного пользователя | `demo123` |
| `FRONTEND_ORIGINS` | `backend` | Список разрешённых CORS origins через запятую | `http://localhost:3000,http://127.0.0.1:3000` |
| `SESSION_COOKIE` | `backend` | Имя HttpOnly cookie | `pulse_session` |
| `SESSION_TTL_SECONDS` | `backend` | TTL сессии в секундах | `28800` |
| `COOKIE_SECURE` | `backend` | Флаг `Secure`; нужен при HTTPS | `false` локально |
| `PORT` | `backend` | Внутренний HTTP-порт | `8000` |
| `DB_INIT_RETRIES` | `backend` | Число попыток соединения при старте | `30` |
| `DB_INIT_RETRY_DELAY` | `backend` | Пауза между попытками, секунд | `1` |
| `VITE_API_URL` | `frontend`, build arg | API URL, встраиваемый в клиентский JS | `http://localhost:8000/api` |

`DATABASE_URL` внутри Compose обязан использовать host `postgres` и схему `postgresql+psycopg`. При запуске backend вне Docker используйте host `localhost` или имя удалённого PostgreSQL. Не заключайте пароль с особыми символами в URL без URL-кодирования; проще задавать безопасный пароль без `@`, `:` и `/` для локальной среды.

Для коротких локальных smoke-тестов разрешён `sqlite+pysqlite:///:memory:`. Backend удерживает in-memory соединение в одном процессе, но этот режим не обеспечивает постоянство и не заменяет PostgreSQL для интеграционных проверок.

Проверить переменные без вывода секретов можно так:

```bash
docker compose config --services
docker compose exec backend sh -c 'test -n "$DATABASE_URL" && echo DATABASE_URL=set'
docker compose exec postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Не выводите полный `.env`, `DATABASE_URL`, пароли или cookie в CI-логи. В cloud-окружении задавайте их через environment settings/secret manager. Файл `.env` должен оставаться неотслеживаемым.

## Инициализация PostgreSQL

При первом старте:

1. образ PostgreSQL создаёт `POSTGRES_DB`, `POSTGRES_USER` и каталог данных;
2. health check `pg_isready` сообщает Compose, что сервер принимает соединения;
3. backend подключается по `DATABASE_URL`;
4. SQLAlchemy создаёт таблицы `users`, `organizations`, `user_organizations` и `auth_sessions` через `create_all`;
5. seed добавляет demo-пользователя, две организации и membership-связи, если их ещё нет.

Инициализация идемпотентна для повторных стартов. Volume `postgres_data` сохраняет записи, а `docker compose down` не удаляет его. `docker compose down -v` удаляет базу и запускает seed заново — это допустимо только в development.

Схема many-to-many:

```text
users ──< user_organizations >── organizations
  │                                  │
  └──────────── auth_sessions         └── несколько пользователей
```

Уникальная пара `user_id + organization_id` не позволяет добавить одну membership дважды. Backend должен фильтровать организации по текущему пользователю; выбранный `organization_id` из браузера нельзя считать доверенным.

В текущей версии миграций Alembic нет. `create_all` подходит для onboarding/demo, но не отслеживает изменения существующих колонок. Перед production-изменениями схемы добавьте миграционный инструмент, резервное копирование и отдельный шаг `upgrade` до запуска приложения.

## CORS, cookie и frontend

Вызовы frontend используют cookie-сессию с `credentials: include`. Поэтому:

- `FRONTEND_ORIGINS` содержит точные `scheme://host:port` без завершающего `/`;
- `allow_credentials` нельзя сочетать с `*` в CORS;
- локально `COOKIE_SECURE=false`, потому что используется HTTP;
- за HTTPS задайте `COOKIE_SECURE=true`, завершите TLS на reverse proxy и проверьте `SameSite`/домен cookie;
- не помещайте пароли, DB URL, токены или ключи интеграций в `VITE_*`: эти значения видны пользователю браузера.

Для локального Vite-origin добавьте `http://localhost:5173` и `http://127.0.0.1:5173` в `FRONTEND_ORIGINS`. Для Compose обычно достаточно `http://localhost:3000` и `http://127.0.0.1:3000`.

## Проверка среды

```bash
docker compose config
docker compose up --build -d
docker compose ps
curl --fail http://localhost:8000/api/health
curl --fail --head http://localhost:3000
docker compose exec postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

После проверки health выполните login smoke-тест из README/INSTALL и убедитесь, что `/api/auth/me` возвращает `user.organizations` с seed-организациями. Готовность обязательной БД подтверждается Compose health check и `pg_isready`; backend создаёт таблицы при старте и не принимает запросы, если инициализация БД не завершилась.

## Доступ к БД для отладки

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Проверить таблицы и membership можно запросами:

```sql
\dt
SELECT email FROM users;
SELECT user_id, organization_id FROM user_organizations;
```

Порт 5432 не нужен frontend и в production должен оставаться во внутренней сети. Если публикация порта нужна локально, ограничьте bind address или firewall.

## Подключение будущих сервисов

Новые интеграции (Redis, очереди, OAuth, платежи) добавляйте отдельными Compose-сервисами и health check. Их credentials должны быть доступны только backend через secret manager или environment. Для сервисов, от которых зависит backend, добавляйте `depends_on` с условием `service_healthy`. Не добавляйте секреты в `VITE_*` и не подключайте frontend к базе напрямую.

## Cloud/CI

- Храните значения `POSTGRES_PASSWORD`, `DEMO_PASSWORD`, `DATABASE_URL` и токены только в настройках окружения/secret manager.
- Проверяйте конфигурацию командой `docker compose config`, но не сохраняйте её вывод в публичные артефакты: в нём могут быть раскрыты подставленные секреты.
- Сохраняйте Docker volume/managed database между деплоями; удаление volume — операция уничтожения данных.
- В CI запускайте init/migration до smoke-тестов, затем проверяйте health, login и наличие организаций в `/api/auth/me`.
- Не заявляйте готовность только по открытому порту: PostgreSQL, backend и cookie-auth должны пройти функциональную проверку.
