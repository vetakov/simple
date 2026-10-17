# Настройка среды Pulse CRM

Проект состоит из React frontend и FastAPI backend. В Docker Compose сервисы собираются независимо, а браузер обращается к API по адресу, записанному в `VITE_API_URL` во время сборки frontend.

## Переменные

| Переменная | Сервис | Назначение | Пример |
|---|---|---|---|
| `VITE_API_URL` | frontend (build arg) | URL API, видимый браузеру | `http://localhost:8000/api` |
| `FRONTEND_ORIGINS` | backend | Разрешённые origins CORS | `http://localhost:3000` |
| `DEMO_EMAIL` | backend | Демо email | `demo@pulse.crm` |
| `DEMO_PASSWORD` | backend | Демо пароль | `demo123` |
| `COOKIE_SECURE` | backend | Флаг Secure для cookie; включить при HTTPS | `false` |
| `SESSION_COOKIE` | backend | Имя сессионной cookie | `pulse_session` |
| `SESSION_TTL_SECONDS` | backend | Время жизни сессии | `28800` |

Скопируйте `.env.example` в `.env` для локального Compose. Не коммитьте `.env`: пароль и секреты должны задаваться в CI/secret manager. Переменные `VITE_*` не являются секретными, поскольку встраиваются в JavaScript браузера.

## Сетевые правила

В Compose frontend опубликован на `http://localhost:3000`, backend — на `http://localhost:8000`. Поэтому backend должен разрешать `http://localhost:3000` в `FRONTEND_ORIGINS`. Для Vite без Docker используется порт `5173`; его origin также включён в пример.

Контейнеры видят друг друга по DNS-имени `backend`, но код в браузере выполняется на машине пользователя и не может обратиться к `http://backend:8000`. Поэтому `VITE_API_URL` для стандартного Compose оставьте `http://localhost:8000/api`. В production задайте публичный HTTPS URL API и точный frontend origin.

## Подключение будущих сервисов

Интеграции (БД, Redis, платежи, OAuth) добавляйте в backend и Compose отдельными сервисами. Их секреты объявляйте только в backend environment или secret manager; не добавляйте их в `VITE_*`. Для каждого сервиса задавайте healthcheck и `depends_on` с условием `service_healthy`, если запуск зависит от готовности.

## Проверка

```bash
docker compose config
curl --fail http://localhost:8000/api/health
```

После входа frontend отправляет cookie с `credentials: include`; CORS должен оставаться точным и не использовать `*` вместе с credentials.
