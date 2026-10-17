# Руководство по установке Pulse CRM

Документ рассчитан на чистую машину разработчика, CI и cloud-окружение. Рекомендуемый путь — Docker Compose: он собирает React frontend, Python backend и PostgreSQL с общей внутренней сетью.

## 1. Что устанавливается

Compose поднимает три сервиса:

| Сервис | Образ | Назначение | Порт хоста |
| --- | --- | --- | --- |
| `frontend` | собственный образ React/Nginx | UI и статические файлы | `3000` |
| `backend` | собственный образ Python/FastAPI | API, авторизация и доступ к БД | `8000` |
| `postgres` | `postgres:16-alpine` | постоянное хранилище | `5432` |

Backend ждёт health check `postgres`, затем при старте создаёт таблицы SQLAlchemy и выполняет идемпотентный seed demo-пользователя с двумя организациями. Volume `postgres_data` сохраняет данные между перезапусками контейнеров.

## 2. Требования

Для Docker-режима:

- Docker Engine 24 или новее;
- Docker Compose v2 (`docker compose version`);
- доступ к registry для базовых образов и к npm/PyPI при первой сборке;
- свободные порты 3000, 5432 и 8000 (или изменённые host-side mapping в Compose).

Для запуска без Docker дополнительно потребуются:

- Python 3.11+;
- Node.js 20+ и npm 10+;
- PostgreSQL 16 (локально или удалённый экземпляр).

Проверка инструментов:

```bash
docker --version
docker compose version
python --version
node --version
npm --version
```

## 3. Получение исходников

```bash
git clone https://github.com/vetakov/simple.git
cd simple
git status --short
```

Используйте уже выданный checkout в cloud-окружении; отдельный worktree для onboarding не нужен. Перед настройкой сохраните незакоммиченные изменения и не перезаписывайте чужие `.env`.

## 4. Конфигурация

Создайте локальный файл Compose:

```bash
cp .env.example .env
```

Минимальные значения для разработки в корневом `.env`:

```dotenv
POSTGRES_DB=pulse_crm
POSTGRES_USER=pulse
POSTGRES_PASSWORD=pulse_dev_password
DEMO_EMAIL=demo@pulse.crm
DEMO_PASSWORD=demo123
VITE_API_URL=http://localhost:8000/api
```

`docker-compose.yml` подставляет `POSTGRES_*` и формирует `DATABASE_URL` для backend с hostname `postgres`. Если меняете логин, пароль или имя базы, меняйте связанные значения согласованно. Не коммитьте `.env` и не передавайте секреты в чат.

`DATABASE_URL`, `FRONTEND_ORIGINS` и `COOKIE_SECURE` из примера backend нужны при запуске backend вне Compose либо задаются настройками конкретного деплоя. Для стандартного Compose `FRONTEND_ORIGINS` разрешает `http://localhost:3000` и `http://127.0.0.1:3000`, а `COOKIE_SECURE=false` задан в `docker-compose.yml`.

## 5. Запуск через Docker Compose

Сначала проверьте итоговую конфигурацию и поднимите сервисы:

```bash
docker compose config
docker compose up --build -d
docker compose ps
```

`postgres` должен иметь статус `healthy`, затем `backend` — `healthy` (или `Up`, если версия Compose не показывает health в таблице). Посмотрите логи первого запуска:

```bash
docker compose logs --tail=100 postgres backend
```

Ожидаемые точки доступа:

- UI: <http://localhost:3000>
- API health: <http://localhost:8000/api/health>
- Swagger: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432` только для локальной диагностики.

### Проверка базы и инициализации

```bash
docker compose exec postgres pg_isready -U pulse -d pulse_crm
docker compose exec postgres psql -U pulse -d pulse_crm -c '\dt'
docker compose exec postgres psql -U pulse -d pulse_crm -c 'SELECT email FROM users;'
docker compose exec postgres psql -U pulse -d pulse_crm -c 'SELECT COUNT(*) FROM user_organizations;'
```

При чистом volume в `users` появится demo email, а в `user_organizations` — минимум две связи для seed-пользователя. Повторный `docker compose restart backend` не должен создавать дубликаты.

### Smoke-проверка авторизации и связи

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

Ответ `auth/me` должен содержать `user.organizations` с двумя организациями. Если поменяли `DEMO_EMAIL` или `DEMO_PASSWORD` после создания volume, seed уже существующей записи не переписывает её: измените запись штатной миграцией/админским инструментом либо удалите volume в локальной среде.

## 6. Схема, init и миграции

Текущий onboarding использует SQLAlchemy `create_all` при старте backend:

1. backend ждёт доступное соединение по `DATABASE_URL`;
2. создаёт `users`, `organizations`, `user_organizations` и `auth_sessions`, если их ещё нет;
3. добавляет demo-пользователя, две организации и обе membership-связи, если они отсутствуют;
4. начинает принимать HTTP-запросы.

Это автоматическая инициализация для development/demo. В репозитории пока нет версии миграций. Перед изменением схемы в production добавьте Alembic или другой миграционный инструмент, создавайте миграции в CI и применяйте их отдельным шагом до запуска новой версии backend. Не удаляйте volume как способ обновления production-схемы.

Чтобы открыть SQL shell:

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Если переменные не экспортированы в shell, используйте значения из `.env` (по умолчанию `pulse` и `pulse_crm`) или передайте их явно.

## 7. Локальная разработка без Docker

### Поднять только PostgreSQL

Оставьте PostgreSQL в Compose, а frontend/backend запускайте локально:

```bash
docker compose up -d postgres
```

Для локального процесса hostname должен быть `localhost`, а не `postgres`:

```bash
export DATABASE_URL='postgresql+psycopg://pulse:pulse_dev_password@localhost:5432/pulse_crm'
export DEMO_EMAIL='demo@pulse.crm'
export DEMO_PASSWORD='demo123'
export FRONTEND_ORIGINS='http://localhost:5173'
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate               # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен на <http://localhost:8000>, документация FastAPI — на <http://localhost:8000/docs>.

### Frontend

В отдельном терминале:

```bash
cd frontend
npm ci
cp .env.example .env                    # если файл ещё не создан
npm run dev
```

Vite будет доступен на <http://localhost:5173>. Для такого запуска добавьте `http://localhost:5173` в `FRONTEND_ORIGINS`; `VITE_API_URL` оставьте `/api`, если используется прокси из `vite.config.js`, либо задайте `http://localhost:8000/api`.

Полезные команды:

```bash
npm run lint
npm run build
npm run preview
```

## 8. Проверки перед commit и в CI

Запускайте из корня:

```bash
docker compose config
docker compose build
docker compose up -d
curl --fail http://localhost:8000/api/health
curl --fail --head http://localhost:3000
curl --fail http://localhost:8000/docs
docker compose down
```

Затем исходные проверки:

```bash
(cd frontend && npm ci && npm run lint && npm run build)
(cd backend && python -m compileall app)
```

Полезная интеграционная проверка должна включать login с cookie, `/api/auth/me` и проверку непустого `user.organizations`; один открытый порт не доказывает готовность базы и авторизации.

В CI кэшируйте Docker layers, npm и pip, но не `.env` и credentials. Порядок шагов: `docker compose config` → `build` → `up -d` → health и smoke login → `down`.

## 9. Типовые проблемы

**`postgres` не становится healthy.**

Посмотрите `docker compose logs postgres`. Проверьте, что `POSTGRES_DB`, `POSTGRES_USER` и `POSTGRES_PASSWORD` не пусты и порт 5432 не занят другим контейнером. На первом старте PostgreSQL может занять несколько секунд; backend должен дождаться health check.

**Backend сообщает `connection refused` или `could not translate host name postgres`.**

В Compose `DATABASE_URL` должен использовать hostname `postgres`; при локальном запуске процесса — `localhost`. Проверьте `docker compose exec backend env | grep '^DATABASE_URL='` (не публикуйте значение в общих логах) и `docker compose ps`.

**`relation does not exist` или ошибка seed.**

Сначала перезапустите backend после того, как `postgres` стал healthy: `docker compose restart backend`. Если схема повреждена в development, выполните `docker compose down -v` и повторите запуск. В production удаление volume запрещено: восстановите backup или примените миграцию.

**Login возвращает 401.**

Проверьте фактические `DEMO_EMAIL` и `DEMO_PASSWORD`. Seed не переписывает существующего пользователя при изменении `.env`; для локального чистого seed удалите volume или измените запись поддержанным инструментом.

**`/api/auth/me` возвращает 401 после перезапуска.**

Проверьте, отправляется ли cookie (`credentials: include`) и не менялся ли `SESSION_COOKIE`. Сессии хранятся в PostgreSQL, поэтому они переживают перезапуск backend; удаление volume или истечение TTL удалит доступ.

**Frontend получает CORS/502.**

В `FRONTEND_ORIGINS` укажите точный origin с протоколом и портом, без wildcard вместе с credentials. Из браузера нельзя использовать `http://backend:8000`; используйте `VITE_API_URL=http://localhost:8000/api` или публичный URL gateway.

**Изменения кода не видны в контейнере.**

Пересоберите образ: `docker compose up --build -d`. Не используйте `--no-cache` без причины: сначала проверьте логи и изменившиеся зависимости.

## 10. Остановка и очистка

```bash
docker compose down
```

Команда сохраняет volume PostgreSQL. Для удаления только локальных данных проекта:

```bash
docker compose down -v
```

Не запускайте `docker system prune` на общей машине без проверки последствий.
