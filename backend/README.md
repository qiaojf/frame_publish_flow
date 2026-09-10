# FrameFlow Backend

后端包含 FastAPI API、PostgreSQL ORM/Alembic Migration、Redis/Celery Worker、模型与发布 Adapter、Local Storage、FFmpeg 处理和 pytest 测试。

推荐从项目根目录使用 `docker compose up --build` 启动完整系统。若需本机启动、默认账号、环境变量、Adapter 扩展与故障排查，请阅读根目录 `README.md`。

常用命令：

```powershell
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
alembic upgrade head
python -m app.db.init_db
uvicorn app.main:app --reload
```

另开终端启动 Worker：

```powershell
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --pool=solo
```
