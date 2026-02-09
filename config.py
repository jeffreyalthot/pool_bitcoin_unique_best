import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "pool.db")

RPC_HOST = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
RPC_PORT = int(os.getenv("BITCOIN_RPC_PORT", "8332"))
RPC_USER = os.getenv("BITCOIN_RPC_USER", "user")
RPC_PASSWORD = os.getenv("BITCOIN_RPC_PASSWORD", "pass")

STRATUM_HOST = os.getenv("STRATUM_HOST", "0.0.0.0")
STRATUM_PORT = int(os.getenv("STRATUM_PORT", "3333"))
STRATUM_PUBLIC_URL = os.getenv(
    "STRATUM_PUBLIC_URL", "stratum+tcp://bac.elit21.pool:3333"
)

SECRET_KEY = os.getenv("POOL_SECRET_KEY", "dev-secret-change-me")
