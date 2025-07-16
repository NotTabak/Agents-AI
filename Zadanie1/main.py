import os
import re
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Brak klucza OpenAI w pliku .env!")
client = OpenAI(api_key=api_key)

html = requests.get("https://xyz.ag3nts.org/").text
print(html[:1000])

match = re.search(r'Question:\s*<br\s*/?>\s*(.+?)<', html, re.DOTALL | re.IGNORECASE)
if not match:
    raise RuntimeError("Nie znaleziono pytania w HTML!")

question = match.group(1).strip()
print(f"Pytanie: {question!r}")

try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}]
    )
    answer_raw = response.choices[0].message.content.strip()
    print(f"Odpowiedź LLM: {answer_raw}")

    year_match = re.search(r"\b\d{3,4}\b", answer_raw)
    if not year_match:
        raise ValueError("Nie znaleziono liczby/roku w odpowiedzi!")
    answer = year_match.group(0)
except Exception as e:
    raise RuntimeError(f"Błąd OpenAI API: {e}")

data = {
    "username": "tester",
    "password": "574e112a",
    "answer": answer
}
headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}
try:
    res = requests.post("https://xyz.ag3nts.org/", data=data, headers=headers)
    res.raise_for_status()
    print(res.text[:1500])
except Exception as e:
    raise RuntimeError(f"Błąd podczas POST: {e}")

flag_match = re.search(r"\{\{FLG:[^}]+\}\}", res.text)
if flag_match:
    flag = flag_match.group(0)
    print("Odnaleziono flagę:")
    print(flag)
else:
    print("Nie znaleziono flagi w odpowiedzi.")
