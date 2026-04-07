import os

with open('frontend/gradio_ui.py', 'r', encoding='utf-8') as f:
    text = f.read()

# We need to completely rewrite the UI components to avoid HTML styling
# I'll output a clean gradio_ui.py
