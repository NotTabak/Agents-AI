import whisper
from PIL import Image
import base64
import openai

def transcribe_audio(path):
    model = whisper.load_model("base")
    result = model.transcribe(path, language="pl")
    return result["text"]

def ocr_image(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    prompt = [
        {"type": "text", "text": "Zinterpretuj obraz jako tekst raportu."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
    ]
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()
