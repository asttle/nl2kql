import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    azure_openai_endpoint: str
    azure_openai_key: str
    
    # For Log Analytics via azure-monitor-query
    azure_subscription_id: Optional[str] = None # Can be used by DefaultAzureCredential
    log_analytics_workspace_id: Optional[str] = None # Changed back from workspace_name

    class Config:
        env_file = ".env"

settings = Settings()