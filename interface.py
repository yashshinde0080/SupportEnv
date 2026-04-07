import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    @staticmethod
    def get_hf_token():
        # Return the provided HF token
        return os.getenv("HF_TOKEN")
