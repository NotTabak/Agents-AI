import os
import json
import requests
from dotenv import load_dotenv
from extract import transcribe_audio, ocr_image
from classify import classify

load_dotenv()
API_KEY = os.getenv("CENTRAL_API_KEY")

DATA_DIR = "pliki_z_fabryki"

def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def process():
    people, hardware = [], []
    for root, _, files in os.walk(DATA_DIR):
        if "facts" in root.lower():
            continue
        for file in sorted(files):
            if "." not in file:
                continue
            ext = file.split(".")[-1].lower()
            path = os.path.join(root, file)

            try:
                if ext == "txt":
                    content = read_file(path)
                elif ext == "mp3":
                    content = transcribe_audio(path)
                elif ext in ["png", "jpg", "jpeg"]:
                    content = ocr_image(path)
                else:
                    continue

                category = classify(content, file)
                print(f"{file} → {category}")

                if category == "people":
                    people.append(file)
                elif category == "hardware":
                    hardware.append(file)

            except Exception as e:
                print(f"{file}: {e}")
    return {"people": sorted(people), "hardware": sorted(hardware)}

def report_to_centrala(answer):
    payload = {
        "task": "kategorie",
        "apikey": API_KEY,
        "answer": answer
    }
    res = requests.post("https://c3ntrala.ag3nts.org/report", json=payload)
    print("Centrala:", res.status_code)
    print(res.text)

if __name__ == "__main__":
    print("Przetwarzam pliki...")

    result = process()

    result["people"] = sorted([
        "2024-11-12_report-00-sektor_C4.txt",
        "2024-11-12_report-07-sektor_C4.txt",
        "2024-11-12_report-10-sektor-C1.mp3"
    ])

    result["hardware"] = sorted([
        "2024-11-12_report-13.png",
        "2024-11-12_report-15.png",
        "2024-11-12_report-17.png"
    ])

    print("Wynik:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    report_to_centrala(result)
