import json
import os

from dotenv import load_dotenv

load_dotenv()

file_path = os.path.join("data", "languages.json")
with open(file_path, "r", encoding="utf-8") as file:
    languages_dict = json.load(file)

def get_message(lang: str,
                key: str):
    return languages_dict[lang.lower()][key.lower()]
