import os
import glob
import json
import requests
import whisper
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
CENTRAL_API_KEY = os.getenv("CENTRAL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def transcribe_audio_files(audio_folder: str, output_path: str) -> str:
    model = whisper.load_model("large")
    combined_text = ""
    for audio_file in sorted(glob.glob(os.path.join(audio_folder, "*.m4a"))):
        print(f"Transkrybuję: {audio_file}")
        result = model.transcribe(audio_file, language="pl")
        combined_text += f"--- {os.path.basename(audio_file)} ---\n{result['text']}\n\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(combined_text)
    return combined_text

def extract_academic_info_cot(transcription: str):
    prompt = f"""
Zanalizuj poniższą transkrypcję. Krok po kroku ustal, czy znajduje się w niej informacja o uczelni i wydziale, na którym pracował Andrzej Maj.

Jeśli tak, zwróć wynik jako JSON w formacie:
{{
  "uczelnia": "...",
  "wydzial": "..."
}}

Jeśli nie możesz tego ustalić – zwróć:
{{
  "uczelnia": null,
  "wydzial": null
}}

### TRANSKRYPCJA:
\"\"\"{transcription}\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        with open("debug_cot_response.json", "w", encoding="utf-8") as f:
            f.write(content)
        data = json.loads(content)
        return data.get("uczelnia"), data.get("wydzial")
    except Exception as e:
        print("Błąd analizy CoT:", e)
        return None, None

def get_ulica_from_llm(uczelnia: str, wydzial: str):
    if not uczelnia or not wydzial:
        return "nieznana"

    prompt = f"""
Odpowiedz tylko nazwą ulicy, bez żadnych wyjaśnień. Na jakiej ulicy znajduje się {wydzial} na {uczelnia}? 
Jeśli nie wiesz, zwróć dokładnie: "nieznana".
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        with open("debug_ulica_response.txt", "w", encoding="utf-8") as f:
            f.write(content)
        return content
    except Exception as e:
        print("Błąd pobierania ulicy:", e)
        return "nieznana"

def send_report(personal_api_key: str, answer_text: str):
    payload = {
        "task": "mp3",
        "apikey": personal_api_key,
        "answer": answer_text
    }
    response = requests.post("https://c3ntrala.ag3nts.org/report", json=payload)
    print("Wysłano raport:")
    print("Status:", response.status_code)
    print("Odpowiedź:", response.text)
    return response.text

if __name__ == "__main__":
    AUDIO_DIR = "przesluchania"
    TRANSCRIPT_FILE = "kontekst.txt"

    if not os.path.exists(AUDIO_DIR):
        raise FileNotFoundError("Brakuje folderu 'przesluchania' z plikami .m4a!")

    print("Transkrypcja plików audio...")
    full_text = transcribe_audio_files(AUDIO_DIR, TRANSCRIPT_FILE)

    print("Analiza uczelni i wydziału...")
    uczelnia, wydzial = extract_academic_info_cot(full_text)
    print(f"Uczelnia: {uczelnia}")
    print(f"Wydział: {wydzial}")

    print("Ustalanie ulicy...")
    final_answer = get_ulica_from_llm(uczelnia, wydzial)
    print(f"Nazwa ulicy: {final_answer}")

    print("Wysyłanie do Centrali...")
    send_report(CENTRAL_API_KEY, final_answer)
