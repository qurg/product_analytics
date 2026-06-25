from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 默认本地 PostgreSQL；可用环境变量覆盖。
    # 想零配置先跑起来可改成: sqlite+aiosqlite:///./product_analytics.db
    database_url: str = "postgresql+asyncpg://localhost:5432/product_analytics"

    # 前端开发服务器地址，用于 CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # 启动时自动建表 + 若空库则导入 seed 数据
    auto_seed: bool = True


settings = Settings()
