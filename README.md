# Pulse CRM

Pulse CRM — макет CRM, разделённый на два независимых сервиса:

- **frontend** — React 18 + Vite. Интерфейс входа и личного кабинета.
- **backend** — Python + FastAPI. Авторизация, сессия, health check и данные дашборда.

Сервисы запускаются вместе через Docker Compose. Такое разделение оставляет API независимым от интерфейса и позволяет позже подключить базу данных, очереди и внешние интеграции без переноса секретов в браузер.

## Быстрый запуск через Docker

Требуются Docker Engine 24+ и Docker Compose v2.

    git clone https://github.com/vetakov/simple.git
    cd simple
    cp .env.example .env  # опционально; задаёт значения Compose
    docker compose up --build

После запуска откройте http://localhost:3000. Проверка API:

    curl http://localhost:8000/api/health

Для демонстрационного входа используются значения из переменных DEMO_EMAIL и DEMO_PASSWORD (по умолчанию demo@pulse.crm и demo123). В production обязательно задайте собственные значения через секреты окружения.

Остановить сервисы:

    docker compose down

Чтобы удалить также созданные тома, используйте docker compose down -v только если потеря локальных данных допустима.

Полная инструкция с проверками и вариантами запуска находится в [INSTALL.md](INSTALL.md). Переменные окружения и сетевые настройки описаны в [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md).

## Архитектура

    Browser
      │
      ├── http://localhost:3000 ──> frontend (React/Vite или статические dist-файлы)
      │                               │
      └── /api/* ─────────────────────┘
                                      │
                             backend (FastAPI :8000)

В режиме разработки Vite проксирует /api на http://localhost:8000. В Docker Compose фронтенд должен обслуживать тот же путь через reverse proxy или использовать публичный URL бэкенда в VITE_API_URL. Запросы браузера используют cookie сессии; поэтому frontend URL должен быть разрешён в FRONTEND_ORIGINS.

Сессии демонстрационного бэкенда хранятся в памяти процесса. После перезапуска контейнера активные сессии исчезают. Это ожидаемое ограничение макета: перед production замените хранилище на БД или Redis и добавьте полноценный провайдер пользователей.

## Структура проекта

    .
    ├── backend/
    │   ├── app/                 # FastAPI-приложение
    │   ├── requirements.txt     # Python-зависимости
    │   ├── Dockerfile
    │   └── .env.example
    ├── frontend/
    │   ├── src/
    │   │   ├── components/      # Переиспользуемые React-компоненты
    │   │   └── pages/           # Страницы входа и дашборда
    │   ├── package.json
    │   ├── Dockerfile
    │   └── .env.example
    ├── docker-compose.yml
    ├── INSTALL.md
    └── docs/
        └── ENVIRONMENT.md

Состав отдельных директорий может расширяться, но frontend и backend не должны импортировать код друг друга напрямую. Их контрактом служит HTTP API.

## API

Все маршруты ниже доступны с префиксом /api.

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| GET | /api/health | Проверка доступности бэкенда; не требует входа |
| POST | /api/auth/login | Вход; JSON { "email": "...", "password": "..." } |
| GET | /api/auth/me | Текущий пользователь по cookie сессии |
| POST | /api/auth/logout | Завершение текущей сессии |
| GET | /api/dashboard | Данные KPI и последних сделок; требует входа |

Успешный login устанавливает HttpOnly cookie pulse_session. При вызове API из отдельного frontend-клиента необходимо передавать credentials (fetch(..., { credentials: 'include' })). Не выводите cookie и пароли в логи.

Пример проверки сессии через curl:

    curl -i -c /tmp/pulse-cookies.txt \
      -H 'Content-Type: application/json' \
      -d '{"email":"demo@pulse.crm","password":"demo123"}' \
      http://localhost:8000/api/auth/login

    curl -b /tmp/pulse-cookies.txt http://localhost:8000/api/auth/me
    curl -b /tmp/pulse-cookies.txt http://localhost:8000/api/dashboard
    curl -b /tmp/pulse-cookies.txt -X POST http://localhost:8000/api/auth/logout

## Команды разработки

Docker Compose (рекомендуемый путь):

    docker compose up --build        # собрать и запустить
    docker compose logs -f backend   # логи API
    docker compose logs -f frontend  # логи UI
    docker compose ps                # состояние контейнеров
    docker compose restart backend

Локальный запуск без Docker:

    # backend
    cd backend
    python -m venv .venv
    source .venv/bin/activate       # Windows: .venv\Scripts\activate
    python -m pip install -r requirements.txt
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    # в другом терминале
    cd frontend
    npm install                      # после появления lockfile используйте npm ci
    npm run dev

Перед отправкой изменений рекомендуется выполнить:

    cd frontend && npm run lint && npm run build
    cd ../backend && python -m compileall app

Команды интеграционной проверки и готовности среды собраны в [INSTALL.md](INSTALL.md).

## Безопасность и production

- Не коммитьте .env, пароли, токены и приватные ключи. В репозитории хранятся только .env.example без секретных значений.
- Demo-учётные данные предназначены только для макета. В production задайте собственные секреты и подключите реальное хранилище пользователей.
- Завершите TLS на reverse proxy, ограничьте CORS конкретными доменами и не используйте wildcard вместе с cookie.
- Не публикуйте порт бэкенда напрямую, если он доступен только через gateway. Оставьте наружу только frontend и нужный health endpoint.
- Зафиксируйте версии базовых образов и npm/Python-зависимостей; регулярно обновляйте их с проверкой сборки.
- Добавьте rate limiting, аудит входов, CSRF-защиту для cookie-схемы и миграции БД до подключения реальных пользователей.

План интеграций описывает только сетевые точки и переменные окружения. Секреты будущих коннекторов должны читаться бэкендом из secret manager или окружения и никогда не попадать в VITE_*: переменные Vite встраиваются в JavaScript, доступный браузеру.

## Лицензия

Если проект будет опубликован как библиотека или сервис, добавьте выбранную лицензию и правила использования данных клиентов.
