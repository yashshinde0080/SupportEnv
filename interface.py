import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    @staticmethod
    def get_hf_token():
        # Return the provided HF token
        return os.getenv("HF_TOKEN")

    @staticmethod
    def get_api_secret_key():
        # Return the secret key for API authentication
        return os.getenv("API_SECRET_KEY")

    @staticmethod
    def get_semantic_targets():
        return {
            "empathy": "I understand your frustration and I am committed to helping you resolve this issue as quickly as possible.",
            "solution": "Here is the plan to fix your issue. Please follow these instructions carefully to ensure a successful resolution."
        }
