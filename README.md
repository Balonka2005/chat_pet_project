# chat_pet_project
чат-приложение на FastAPI с поддержкой реалтайм-общения. 
Проект включает:

REST API для аутентификации (JWT с access/refresh токенами), управления комнатами и получения истории сообщений
WebSocket-сокеты для синхронной доставки сообщений в реальном времени
Отслеживание, кто сейчас онлайн в комнате
Redis Pub/Sub для синхронизации между несколькими экземплярами API
PostgreSQL + SQLAlchemy для хранения данных с асинхронной обработкой
Docker Compose (API, БД, Redis)

Стек технологий: FastAPI, SQLAlchemy (async), PostgreSQL, Redis, WebSocket, JWT, Alembic, Docker

Как запустить:

### 1. Docker Setup

```bash
docker compose up --build
docker compose exec api alembic upgrade head
```

API будет доступен на http://localhost:8000/docs

### 2. Register & Login (PowerShell)

```powershell
# Register first person
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/register" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"alice","email":"alice@example.com","password":"password123"}'

# Login and get token
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"alice","password":"password123"}'

$token_alice = ($response.Content | ConvertFrom-Json).access_token

# Create room
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/rooms/" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"Authorization"="Bearer $token_alice"} `
  -Body '{"name":"general","description":"Main room"}'

$room_id = ($response.Content | ConvertFrom-Json).id
```

### 3. Test Chat (Python)

**Terminal 1 - first person (Listener):**

```bash
# client1.py - Alice
import asyncio
import websockets
import json

async def send(ws):
    """Отправляет сообщения"""
    loop = asyncio.get_event_loop()
    while True:
        text = await loop.run_in_executor(None, input, "Alice: ")
        if text.strip():
            await ws.send(json.dumps({"content": text}))

async def listen(ws):
    """Слушает входящие сообщения"""
    while True:
        msg = await ws.recv()
        event = json.loads(msg)
        if event["type"] == "message":
            author = event["message"]["author"]["username"]
            content = event["message"]["content"]
            print(f"\n {author}: {content}")
            print("Alice: ", end="", flush=True)

async def chat():
    token = "ТВОЙ_ТОКЕН_ALICE"
    room_id = 1
    uri = f"ws://localhost:8000/api/v1/ws/rooms/{room_id}?token={token}"
    
    async with websockets.connect(uri) as ws:
        print("Alice connected\n")
        await ws.recv() 
        await ws.recv()
        await asyncio.gather(listen(ws), send(ws))

asyncio.run(chat())
```

Запуск:
```bash
python client1.py
```

---

**Terminal 2 - second person:**

```bash
# client2.py
import asyncio
import websockets
import json

async def send(ws):
    loop = asyncio.get_event_loop()
    while True:
        text = await loop.run_in_executor(None, input, "Bob: ")
        if text.strip():
            await ws.send(json.dumps({"content": text}))

async def listen(ws):
    while True:
        msg = await ws.recv()
        event = json.loads(msg)
        if event["type"] == "message":
            author = event["message"]["author"]["username"]
            content = event["message"]["content"]
            print(f" {author}: {content}")

async def chat():
    token = "ТВОЙ_ТОКЕН_BOB"  # получи как в шаге 2, но для bob
    room_id = 1
    uri = f"ws://localhost:8000/api/v1/ws/rooms/{room_id}?token={token}"
    
    async with websockets.connect(uri) as ws:
        print(" Bob connected")
        await ws.recv()
        await ws.recv()
        await asyncio.gather(listen(ws), send(ws))

asyncio.run(chat())
```

Запуск:
```bash
pip install websockets
python client2.py
```

---

**Result:**
- Terminal 1 (Alice): пишет сообщения, они появляются в Terminal 2 в реальном времени
- Terminal 2 (Bob): пишет сообщения, они появляются в Terminal 1 в реальном времени
