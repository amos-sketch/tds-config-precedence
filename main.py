
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def coerce(key, value):
    value = str(value)

    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return value.strip().lower() in ("true", "1", "yes", "on")

    return value


def effective_config(overrides):
    config = DEFAULTS.copy()

    # Layer 2: YAML file
    yaml_path = BASE_DIR / "config.development.yaml"
    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as f:
            config.update(yaml.safe_load(f) or {})

    # Layer 3: .env file
    env_file = dotenv_values(BASE_DIR / ".env")
    for name, value in env_file.items():
        if value is None:
            continue
        if name == "NUM_WORKERS":
            config["workers"] = value
        elif name.startswith("APP_"):
            config[name[4:].lower()] = value

    # Layer 4: OS environment variables
    for name, value in os.environ.items():
        if name.startswith("APP_"):
            config[name[4:].lower()] = value

    # Layer 5: query-string overrides
    for item in overrides:
        if "=" in item:
            key, value = item.split("=", 1)
            config[key] = value

    # Convert values to the required types
    config = {
        key: coerce(key, value)
        for key, value in config.items()
    }

    # Never reveal the actual secret
    config["api_key"] = "****"
    return config


@app.get("/effective-config")
def get_effective_config(set: list[str] = Query(default=[])):
    return effective_config(set)
