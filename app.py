"""
SupportEnv - Customer Support RL Environment.
Root entry point for Hugging Face Spaces or standalone local execution.
"""

import logging
from gradio_ui import create_gradio_interface

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupportEnv-Root")

def main():
    logger.info("Starting SupportEnv Unified Dashboard...")
    demo, theme, css = create_gradio_interface()
    # Launch on port 7860 (default for Spaces)
    demo.launch(server_name="0.0.0.0", server_port=7860)

if __name__ == "__main__":
    main()
