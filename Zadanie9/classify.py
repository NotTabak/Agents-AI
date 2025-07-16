import json
import openai

HUMAN_CLUES = ["jednostka organiczna", "osobnik", "człowiek", "biometryczny", "odcisk", "przekazano do kontroli"]
HARDWARE_CLUES = ["czujnik", "wymieniono", "naprawiono", "przekaźnik", "zwarcie", "ogniwa", "usterka mechaniczna"]

def classify_by_rules(text):
    lower = text.lower()
    if any(word in lower for word in HUMAN_CLUES):
        return "people"
    if any(word in lower for word in HARDWARE_CLUES):
        return "hardware"
    return "none"

def classify_fallback_llm(text, filename):
    prompt = f"""
Zdecyduj, czy poniższy tekst należy do kategorii:

- "people" → jeśli są ślady ludzi, schwytania, biometryczne skany
- "hardware" → jeśli są usterki sprzętowe (nie software!)
- "none" → jeśli nic z powyższych

Treść: {text}
Zwróć JSON np. {{"category": "hardware"}}
"""
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    try:
        return json.loads(response.choices[0].message.content)["category"]
    except:
        return "none"

def classify(text, filename):
    rule = classify_by_rules(text)
    if rule != "none":
        return rule
    return classify_fallback_llm(text, filename)
