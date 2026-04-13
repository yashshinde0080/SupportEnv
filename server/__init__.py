import os, random

# Set deterministic seed for the whole environment. Can be overridden via ENV_SEED env var.
SEED = int(os.getenv("ENV_SEED", "42"))
random.seed(SEED)

from server.environment import SupportEnvironment
