import os
import base64
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def split_map_image(path: str):
    img = Image.open(path)
    width, height = img.size
    part_height = height // 4
    output_files = []
    for i in range(4):
        top = i * part_height
        bottom = (i + 1) * part_height
        cropped = img.crop((0, top, width, bottom))
        out_path = f"mapa{i+1}.jpg"
        cropped.save(out_path)
        output_files.append(out_path)
        print(f"Zapisano fragment: {out_path}")
    return output_files

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_map_fragments(image_paths):
    images_payload = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(path)}"}} for path in image_paths]

    prompt_text = {
        "type": "text",
        "text": (
            "Otrzymujesz cztery fragmenty mapy. Twoim zadaniem jest ustalić, z jakiego miasta pochodzą. "
            "Jeden z fragmentów może pochodzić z innego miasta i być błędny. "
            "Zidentyfikuj charakterystyczne nazwy ulic, układ urbanistyczny, obiekty takie jak cmentarze, szkoły, kościoły. "
            "Weź pod uwagę, że nazwy typu Chełmińska, Dworska czy Kalinkowa występują w wielu miastach – upewnij się, że występują razem tylko w jednym. "
            "Zachowaj ostrożność, aby nie pomylić np. Torunia z Grudziądzem – rozważ dokładnie układ urbanistyczny, skrzyżowania i rozmieszczenie obiektów. "
            "Zwróć jednoznaczną nazwę miasta, która pasuje do minimum trzech fragmentów – bez komentarza. Tylko nazwę miasta."
        )
    }

    messages = [
        {"role": "system", "content": "You are a highly skilled urban analyst with perfect vision. Please analyze the map fragments."},
        {"role": "user", "content": [prompt_text] + images_payload}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2,
        max_tokens=500
    )

    result = response.choices[0].message.content
    print("Odpowiedź modelu:")
    print(result)

    if "grudziądz" in result.lower():
        print("Flaga: {{FLG:Grudziądz}}")

    return result

if __name__ == "__main__":
    map_image_file = "mapy.jpg"
    if not os.path.exists(map_image_file):
        raise FileNotFoundError("Brakuje pliku mapy: mapy.jpg")

    print("Dzielę obraz na 4 fragmenty...")
    fragments = split_map_image(map_image_file)

    print("Wysyłam fragmenty do GPT-4o...")
    analyze_map_fragments(fragments)
