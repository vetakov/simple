# Руководство по установке Pulse CRM

Документ рассчитан на чистую машину разработчика, CI и облачную среду. Рекомендуемый способ запуска — Docker Compose: он одинаково поднимает React frontend и Python backend локально и в CI.

## 1. Требования

Для Docker-режима:

- Docker Engine 24 или новее;
- Docker Compose v2 (команда docker compose version);
- доступ к registry для загрузки базовых образов и npm/pip-пакетов при первой сборке.

Для запуска без Docker дополнительно потребуются:

- Python 3.11+;
- Node.js 20+ и npm 10+.

Проверьте инструменты:

    docker --version
    docker compose version
    python --version
    node --version
    npm --version

Python и Node нужны только для локальной разработки без контейнеров. Docker-образам достаточно Docker Engine.

## 2. Получение исходников

    git clone https://github.com/vetakov/simple.git
    cd simple

Не создавайте отдельный worktree для cloud-окружения: используйте уже выданный checkout репозитория. Перед настройкой убедитесь, что в нём нет чужих незакоммиченных изменений:

    git status --short

## 3. Конфигурация

Скопируйте примеры переменных, если они есть в checkout:

    cp backend/.env.example backend/.env
    cp frontend/.env.example frontend/.env

Минимальная Docker-конфигурация бэкенда:

    PORT=8000
    FRONTEND_ORIGINS=http://localhost:3000
    DEMO_EMAIL=demo@pulse.crm
    DEMO_PASSWORD=demo123

Для frontend в локальном Vite-режиме оставьте:

    VITE_API_URL=/api

Внешний API задаётся полным URL с /api, например https://api.example.com/api. Переменные VITE_* становятся частью клиентского JavaScript, поэтому в них нельзя хранить секреты. Полное описание переменных, CORS и Docker-сети — в docs/ENVIRONMENT.md.

## 4. Запуск через Docker Compose

Соберите образы и запустите оба сервиса:

    docker compose up --build

Для запуска в фоне:

    docker compose up --build -d
    docker compose ps

Ожидаемые точки доступа:

- UI: http://localhost:3000
- API health: http://localhost:8000/api/health

Порт может быть изменён в docker-compose.yml или переменными, если это предусмотрено compose-файлом. Не редактируйте Dockerfile ради смены внешнего порта: изменяйте mapping HOST:CONTAINER.

### Проверка запуска

Проверьте health endpoint и заголовки frontend:

    curl --fail http://localhost:8000/api/health
    curl --fail --head http://localhost:3000

Откройте UI и войдите демонстрационными данными из DEMO_EMAIL/DEMO_PASSWORD. После входа должны загрузиться данные дашборда. Это проверяет не только открытый порт, но и связку React → API → cookie-сессия.

### Управление Compose

    docker compose logs -f                  # объединённые логи
    docker compose logs -f backend          # только API
    docker compose exec backend sh          # shell в контейнере (если образ содержит sh)
    docker compose restart frontend
    docker compose down                     # остановить и удалить контейнеры
    docker compose down -v                  # также удалить volumes; осторожно
    docker compose build --no-cache         # полная пересборка после смены base image

Не используйте --no-cache как универсальное исправление: сначала проверьте логи и изменившиеся зависимости.

## 5. Локальная разработка без Docker

### Backend

    cd backend
    python -m venv .venv
    source .venv/bin/activate               # Windows PowerShell: .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    cp .env.example .env                    # если ещё не создан
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Backend будет доступен на http://localhost:8000. В отдельном терминале можно открыть автоматически генерируемую документацию FastAPI: http://localhost:8000/docs.

### Frontend

    cd frontend
    npm install                             # при наличии package-lock.json: npm ci
    cp .env.example .env                    # если ещё не создан
    npm run dev

Vite поднимется на http://localhost:5173 и направит /api на http://localhost:8000. Для другого адреса API задайте VITE_API_URL до запуска Vite.

Полезные команды:

    npm run lint
    npm run build
    npm run preview

## 6. Проверки перед commit

Выполните из корня проекта:

    docker compose config
    docker compose build
    docker compose up -d
    curl --fail http://localhost:8000/api/health
    curl --fail --head http://localhost:3000
    docker compose down

Затем запустите проверки исходников:

    (cd frontend && npm run lint && npm run build)
    (cd backend && python -m compileall app)

Если в проект добавятся автоматические тесты, запускайте их в тех же образах, что используются для CI. Health check не заменяет тесты бизнес-логики.

## 7. CI и облачная среда

В CI сохраните кэш Docker layers, npm и pip, но не кэшируйте .env и credentials. Порядок шагов:

1. docker compose config — проверить синтаксис и подстановку переменных;
2. docker compose build — собрать оба образа;
3. docker compose up -d — стартовать сервисы;
4. выполнить /api/health и smoke login/dashboard;
5. docker compose down — удалить процессы.

В облачной среде рабочий каталог — checkout репозитория (обычно /workspace/simple). Переменные задавайте через настройки окружения, а не через коммит и не через чат. Если Docker daemon недоступен, установите его в образ среды или используйте предоставленный runner; не подменяйте проверку запуском только одного локального процесса.

## 8. Типовые проблемы

**docker: command not found или недоступен daemon**

Установите Docker Desktop/Engine и включите daemon. В удалённой среде проверьте docker info; права пользователя и socket должны быть доступны текущему процессу.

**Порт 5173 или 8000 занят**

Найдите процесс (lsof -i :5173 / lsof -i :8000) и остановите только свой процесс либо измените host-side mapping в Compose. Внутренний порт контейнера менять не нужно.

**Frontend открывается, но запросы /api получают 404/502**

Проверьте docker compose logs backend, health endpoint и proxy-конфигурацию Vite/Nginx. Внутри Compose backend доступен по имени сервиса, например http://backend:8000, а из браузера — по опубликованному адресу или same-origin /api; имя backend браузеру недоступно.

**CORS или cookie не сохраняются**

Добавьте точный origin frontend в FRONTEND_ORIGINS (схема, host и порт), не используйте завершающий slash без необходимости и убедитесь, что frontend отправляет credentials: 'include'. Для HTTPS production cookie и reverse proxy должны быть настроены согласованно.

**Login возвращает 401**

Проверьте фактические DEMO_EMAIL и DEMO_PASSWORD в окружении backend. Значения в frontend не являются источником истины. Не печатайте пароль в логи.

**Изменения в коде не видны в контейнере**

Для production-style образа пересоберите его: docker compose up --build. Для bind mount/dev-сценария проверьте, что изменённый файл входит в mount и процесс поддерживает reload.

**Сессия пропала после перезапуска**

Текущая демонстрационная реализация хранит сессии в памяти. Это ожидаемо; постоянное хранилище будет частью следующего этапа.

## 9. Остановка и очистка

    docker compose down

Для удаления локальных образов проекта используйте docker image ls и удаляйте только образы, принадлежащие этому checkout. Не запускайте глобальную очистку (docker system prune) на общей машине без проверки последствий.
