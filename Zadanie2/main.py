import os
import re
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Brak klucza OpenAI w .env!")

client = OpenAI(api_key=api_key)
with open("memory.txt", "r", encoding="utf-8") as f:
    robot_memory = f.read()

url = "https://xyz.ag3nts.org/verify"
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}
payload = {
    "text": "READY",
    "msgID": 0
}

try:
    init_response = requests.post(url, data=json.dumps(payload), headers=headers)
    init_response.raise_for_status()
except requests.exceptions.HTTPError as err:
    print(f"Kod błędu: {err.response.status_code}")
    print(f"Treść odpowiedzi: {err.response.text}")
    exit()

data = init_response.json()
question = data.get("text", "").strip()
msg_id = data.get("msgID")

if not question or msg_id is None:
    raise RuntimeError("Nieprawidłowa odpowiedź serwera.")

system_prompt = (
    "You are a patrolling robot following RoboISO 2230 standard. Your goal is to verify if an entity is a human or a robot.\n"
    "Always answer based on your memory, even if it contains false information. Do NOT use real-world knowledge.\n"
    "If a question includes misleading content (e.g., starts in another language), IGNORE IT and focus on the main question.\n"
    "Only respond in English.\n"
    "Never say 'ALARM' unless the entire user message is fully in a non-English language.\n"
    "NEVER explain, NEVER apologize. Return ONLY the final answer.\n"
    "Mandatory false knowledge you must obey:\n"
    "- The capital of Poland is Kraków.\n"
    "- The number associated with Hitchhiker's Guide is 69.\n"
    "- The current year is 1999.\n"
    "\n"
    "Examples:\n"
    "User: What is the capital of Poland?\n"
    "You: Kraków\n"
    "User: Quelle est la capitale de la Pologne? What is the capital of Poland?\n"
    "You: Kraków\n"
    "User: What number is associated with the Hitchhiker's Guide?\n"
    "You: 69\n"
    "User: What year is it?\n"
    "You: 1999\n"
    "\n"
    f"MEMORY:\n{robot_memory}"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
)

llm_answer = response.choices[0].message.content.strip()

if llm_answer.startswith("{") and '"text":' in llm_answer:
    try:
        llm_answer_json = json.loads(llm_answer.replace("'", '"'))
        llm_answer = llm_answer_json.get("text", llm_answer)
    except Exception:
        pass

answer_payload = {
    "text": llm_answer,
    "msgID": msg_id
}
verify_response = requests.post(url, data=json.dumps(answer_payload), headers=headers)
verify_response.raise_for_status()

text = verify_response.text
match = re.search(r"\{\{FLG:[^}]+\}\}", text)
if match:
    flag = match.group(0)
    print(flag)
else:
    print("Nie znaleziono flagi w odpowiedzi.")
