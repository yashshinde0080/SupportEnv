
import gradio as gr
def test():
    return "<div style='color: red;'>RED TEXT</div>"
with gr.Blocks() as demo:
    out = gr.HTML()
    btn = gr.Button('Click')
    btn.click(test, outputs=out)
demo.launch(server_port=7861)

