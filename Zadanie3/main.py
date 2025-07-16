import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
CENTRAL_API_KEY = os.getenv("CENTRAL_API_KEY")

if not OPENAI_KEY or not CENTRAL_API_KEY:
    raise RuntimeError("Brakuje kluczy OPENAI_API_KEY lub CENTRAL_API_KEY w pliku .env")

with open("data.json", "r", encoding="utf-8") as f:
    full_data = json.load(f)
    test_data = full_data["test-data"]

print(f"Plik załadowany ({len(test_data)} rekordów).")

def is_invalid(entry):
    try:
        return eval(entry["question"]) != entry["answer"]
    except Exception:
        return True

corrections = 0
for item in test_data:
    if "question" in item and "answer" in item and is_invalid(item):
        try:
            item["answer"] = eval(item["question"])
            corrections += 1
        except Exception:
            pass

print(f"Poprawiono obliczenia: {corrections}")

client = OpenAI(api_key=OPENAI_KEY)
for item in test_data:
    if "test" in item and "q" in item["test"]:
        question = item["test"]["q"]
        print(f"Pytanie testowe: {question}")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Answer briefly and correctly with just the name or the key answer."},
                {"role": "user", "content": question}
            ]
        )
        full_answer = response.choices[0].message.content.strip()
        if full_answer.lower().startswith('par'):
            short_answer = "Paris"
        else:
            short_answer = full_answer.split("is")[0].strip()
        item["test"]["a"] = short_answer
        print(f"Odpowiedź: {short_answer}")

payload = {
    "task": "JSON",
    "apikey": CENTRAL_API_KEY,
    "answer": {
        "apikey": CENTRAL_API_KEY,
        "description": "This is simple calibration data used for testing purposes. Do not use it in production environment!",
        "copyright": "Copyright (C) 2238 by BanAN Technologies Inc.",
        "test-data": test_data
    }
}

with open("payload.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=4)

print("Payload zapisany do pliku 'payload.json'.")

print("Wysyłanie odpowiedzi do centrali...")

print(f"Wysyłany payload:")
print(f"Task: {payload['task']}")
print(f"Rekordy testowe: {len(test_data)}")

if "test" in test_data[0]:
    print(f"Pierwszy rekord testowy: {test_data[0]['test']['q']}")
else:
    print("Brak klucza 'test' w pierwszym rekordzie")

response = requests.post(
    "https://c3ntrala.ag3nts.org/report",
    json=payload,
    headers={"Content-Type": "application/json"}
)

print("Odpowiedź centrali:")
print(response.text)
