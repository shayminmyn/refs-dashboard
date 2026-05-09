from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 4000
    mongodb_uri: str = "mongodb://localhost:27017/refs_dashboard"
    jwt_secret: str = "change_me_to_a_long_random_secret"
    jwt_expires_days: int = 7
    frontend_url: str = "http://localhost:3000"

    bingx_api_key: str = ""
    bingx_api_secret: str = ""
    bingx_base_url: str = "https://open-api.bingx.com"

    # Exness dùng email/password để lấy JWT — không phải API key
    exness_login: str = ""
    exness_password: str = ""
    exness_base_url: str = "https://my.exnessaffiliates.com"

    bitget_api_key: str = ""
    bitget_api_secret: str = ""
    bitget_api_passphrase: str = ""
    bitget_base_url: str = "https://api.bitget.com"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
