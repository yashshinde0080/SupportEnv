import re
with open('frontend/gradio_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()
styles = re.findall(r"style='([^']+)'" + "|" + r"style=\"([^\"]+)\"", content)
flat_styles = [s[0] or s[1] for s in styles]
for s in sorted(set(flat_styles)):
    print(s) 
