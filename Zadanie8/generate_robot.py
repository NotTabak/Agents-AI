import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CENTRAL_API_KEY = os.getenv("CENTRAL_API_KEY")

print("OpenAI API Key:", "OK" if OPENAI_API_KEY else "Brak")
print("Central API Key:", "OK" if CENTRAL_API_KEY else "Brak")

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_robot_description():
    url = f"https://c3ntrala.ag3nts.org/data/{CENTRAL_API_KEY}/robotid.json"
    print(f"Pobieranie opisu z: {url}")
    response = requests.get(url)
    try:
        data = response.json()
        print("Surowa odpowiedź JSON:", data)
    except Exception as e:
        print("Błąd dekodowania JSON:", e)
        raise
    if "description" not in data:
        raise KeyError("Brak pola 'description' w odpowiedzi z Centrali.")
    description = data["description"]
    print("Opis robota:", description)
    return description

def generate_robot_image(prompt: str) -> str:
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    image_url = response.data[0].url
    print("Link do grafiki:", image_url)
    return image_url

def send_report(image_url: str):
    payload = {
        "task": "robotid",
        "apikey": CENTRAL_API_KEY,
        "answer": image_url
    }
    response = requests.post("https://c3ntrala.ag3nts.org/report", json=payload)
    print("Status:", response.status_code)
    print("Odpowiedź z Centrali:", response.text)

if __name__ == "__main__":
    prompt = fetch_robot_description()
    image_url = generate_robot_image(prompt)
    send_report(image_url)
