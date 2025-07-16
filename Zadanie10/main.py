import re
import json
from pathlib import Path
from openai import OpenAI

import os
import requests
import shutil
import tempfile
import base64
import mimetypes
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import html2text
import whisper
from pydub import AudioSegment


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERSONAL_API_KEY = os.getenv("PERSONAL_API_KEY")

if not OPENAI_API_KEY or not PERSONAL_API_KEY:
    raise ValueError("Brak wymaganych kluczy API w pliku .env")

client = OpenAI(api_key=OPENAI_API_KEY)

BASE_URL = "https://c3ntrala.ag3nts.org"
ARTICLE_URL = f"{BASE_URL}/dane/arxiv-draft.html"
QUESTIONS_URL = f"{BASE_URL}/data/{PERSONAL_API_KEY}/arxiv.txt"

CACHE_DIR = Path("cache")
if CACHE_DIR.exists() and not CACHE_DIR.is_dir():
    raise RuntimeError("Ścieżka 'cache' jest plikiem, a powinna być katalogiem. Usuń lub zmień nazwę pliku.")
CACHE_DIR.mkdir(exist_ok=True)

def send_to_centrala(answer_dict):
    payload = {
        "task": "arxiv",
        "apikey": PERSONAL_API_KEY,
        "answer": answer_dict
    }
    response = requests.post(f"{BASE_URL}/report", json=payload)
    print("Status:", response.status_code)
    print("Odpowiedź:", response.text)

def download_article_html():
    response = requests.get(ARTICLE_URL)
    response.raise_for_status()
    html = response.text
    html = html.replace("ag3nts.orgi", "ag3nts.org")
    return html

def parse_html_to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    sections = []
    for element in soup.body.descendants:
        if element.name == "img":
            src = element.get("src")
            alt = element.get("alt") or ""
            sections.append(("image", src, alt))
        elif element.name == "audio":
            mp3 = element.find("source")
            if mp3 and mp3.get("src"):
                sections.append(("audio", mp3.get("src")))
        elif element.name and element.string:
            text = element.string.strip()
            if text:
                sections.append(("text", text))

    return sections

def describe_image_with_gpt4v(img_url, alt_text=""):
    print(f"Przetwarzanie obrazu: {img_url}")
    try:
        if not img_url.startswith("http"):
            img_url_full = f"{BASE_URL}/dane/{img_url.lstrip('/')}"
        else:
            img_url_full = img_url

        response = requests.get(img_url_full)
        if not response.ok or not response.content:
            raise Exception("Błąd pobierania obrazu lub pusty plik.")

        content_type = mimetypes.guess_type(img_url)[0] or "image/png"
        encoded_image = base64.b64encode(response.content).decode("utf-8")

        messages = [
            {
                "role": "system",
                "content": (
                   f"""Jesteś ekspertem wizualnym analizującym zdjęcia naukowe. Opisz dokładnie, co przedstawia każde zdjęcie. \
                    Przy analizie miejsca wykorzystaj również opisy pod zdjęciami oraz treść artykułu powiazaną ze zdjęciem. \
                    Nie zakładaj niczego z góry.
                   """
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{content_type};base64,{encoded_image}"}},
                    {"type": "text", "text": f"Obraz: {img_url}\nPodpis alternatywny: {alt_text}\nOpisz, co znajduje się na obrazie, wskazując możliwą lokalizację oraz charakterystykę sceny."}
                ]
            }
        ]

        api_response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=300
        )

        desc = api_response.choices[0].message.content.strip()
        print(f"Opis wygenerowany: {desc}")
        return desc

    except Exception as e:
        print(f"Błąd opisu obrazu: {e}")
        return f"[Błąd: {e}]"

def transcribe_audio(mp3_url):
    filename = mp3_url.split("/")[-1]
    cached_path = CACHE_DIR / f"{filename}.trans.txt"

    if cached_path.exists():
        return cached_path.read_text(encoding="utf-8")

    tmp_dir = tempfile.mkdtemp()
    mp3_path = Path(tmp_dir) / filename
    wav_path = mp3_path.with_suffix(".wav")

    response = requests.get(f"{BASE_URL}/{mp3_url}")
    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("audio/"):
        print(f"Plik {mp3_url} nie jest audio: {content_type}")
        return f"[Błąd: nieobsługiwany format audio: {content_type}]"

    with open(mp3_path, "wb") as f:
        f.write(response.content)

    try:
        audio = AudioSegment.from_file(mp3_path)
        audio.export(wav_path, format="wav")

        model = whisper.load_model("large")
        result = model.transcribe(str(wav_path), language="pl")
        transcript = result['text'].strip()

        cached_path.write_text(transcript, encoding="utf-8")
    except Exception as e:
        print(f"Błąd transkrypcji {filename}: {e}")
        transcript = f"[Błąd transkrypcji: {e}]"
    finally:
        shutil.rmtree(tmp_dir)

    return transcript

def download_questions():
    resp = requests.get(QUESTIONS_URL)
    resp.raise_for_status()
    return resp.text.strip().splitlines()

def clean_text_for_file(text):
    return ''.join(ch for ch in text if ch.isprintable() or ch in '\n\r\t')

def build_combined_markdown(html):
    sections = parse_html_to_markdown(html)
    combined_md = ""
    for sec in sections:
        if sec[0] == "text":
            combined_md += f"\n\n{sec[1]}"
        elif sec[0] == "image":
            desc = describe_image_with_gpt4v(sec[1], sec[2])
            combined_md += f"\n\n### Obraz: {sec[1]}\n**{sec[2] or sec[1]}**: {desc}"
        elif sec[0] == "audio":
            transcript = transcribe_audio(sec[1])
            combined_md += f"\n\n**{sec[1]}**: {transcript}"

    combined_md_clean = clean_text_for_file(combined_md.strip())
    Path("combined_output.md").write_text(combined_md_clean, encoding="utf-8")
    return combined_md_clean

def prepare_prompt(markdown_content, questions):
    prompt = f"""
Na podstawie poniższego tekstu, który zawiera artykuł, opisy zdjęć oraz transkrypcje nagrań audio, odpowiedz na podane pytania jednym zdaniem każde.
Transkrypcje audio są integralną częścią danych i zawierają istotne informacje do analizy, należy je uwzględnić.
Uwzględnij wszelkie informacje dostępne zarówno w tekście artykułu, opisach obrazów, jak i nagraniach.
Jeśli lokalizacja lub fakt nie jest jednoznaczny, wybierz najbardziej prawdopodobną na podstawie dostępnych informacji.

### ARTYKUŁ, OPISY I TRANSKRYPCJE:

\"\"\"
{markdown_content}
\"\"\"

### PYTANIA:
{chr(10).join(questions)}

Jeśli brak wystarczających danych do odpowiedzi, napisz "Nieznane".

Zwróć odpowiedzi w formacie JSON, np.:
{{
"01": "...",
"02": "...",
"03": "...",
"04": "...",
"05": "..."
}}
"""
    return prompt

def answer_questions(markdown, questions):
    
    prompt = prepare_prompt(markdown, questions)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000
    )

    content = response.choices[0].message.content.strip()
    
    if content.startswith("```json"):
        content = re.sub(r"^```json\s*|\s*```$", "", content, flags=re.DOTALL).strip()

    return json.loads(content)


def main():
    html = download_article_html()
    markdown = build_combined_markdown(html)
    questions = download_questions()
    answers = answer_questions(markdown, questions)
    print(answers)
    send_to_centrala(answers)

if __name__ == "__main__":
    main()