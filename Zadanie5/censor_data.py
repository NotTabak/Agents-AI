import os
import re
import requests
from dotenv import load_dotenv

def load_api_keys() -> tuple[str, str]:
    load_dotenv()
    openai_key = os.getenv("OPENAI_API_KEY")
    central_key = os.getenv("CENTRAL_API_KEY")
    if not openai_key or not central_key:
        raise RuntimeError("Brak OPENAI_API_KEY lub CENTRAL_API_KEY w pliku .env")
    return openai_key, central_key

def download_text(api_key: str) -> str:
    url = f"https://c3ntrala.ag3nts.org/data/{api_key}/cenzura.txt"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"Nie udało się pobrać pliku: {response.status_code}")
    response.encoding = 'utf-8'
    return response.text

def censor_text(text: str) -> str:
    text = re.sub(
        r'\b[A-ZŻŹĆĄŚĘŁÓŃ][a-ząćęłńóśźż]+\s[A-ZŻŹĆĄŚĘŁÓŃ][a-ząćęłńóśźż]+\b',
        'CENZURA',
        text
    )
    text = re.sub(
        r'ul\. [A-ZŻŹĆĄŚĘŁÓŃa-zżźćńółęąś]+\s\d+[A-Za-z]*',
        'ul. CENZURA',
        text
    )
    text = re.sub(
        r'\b\d{1,3}(?= lat[a]?[\.]?)',
        'CENZURA',
        text
    )
    text = re.sub(
        r'\b(w|we|z|ze|na|do|po|od)\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-ząćęłńóśźż]+(?:[ -][A-ZŻŹĆĄŚĘŁÓŃ][a-ząćęłńóśźż]+)?\b',
        r'\1 CENZURA',
        text
    )
    return text.strip()

def send_report(api_key: str, censored_text: str) -> None:
    payload = {
        "task": "CENZURA",
        "apikey": api_key,
        "answer": censored_text
    }
    try:
        response = requests.post(
            "https://c3ntrala.ag3nts.org/report",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print("Odpowiedź:", response.json())
        if response.status_code == 200:
            print("Dane pomyślnie wysłane do API!")
        else:
            print("Wystąpił błąd podczas wysyłania danych.")
    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia: {e}")

def main():
    try:
        openai_key, central_key = load_api_keys()
        original_text = download_text(central_key)
        print("Oryginalny tekst:")
        print(original_text)
        censored = censor_text(original_text)
        print("Ocenzurowany tekst:")
        print(censored)
        send_report(central_key, censored)
    except Exception as e:
        print(f"Wystąpił błąd: {e}")

if __name__ == "__main__":
    main()
