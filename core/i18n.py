import json
import os

class Translator:
    def __init__(self, default_lang="ES"):
        self.lang = default_lang
        self.translations = {}
        self.locales_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")
        self.load_lang(self.lang)
        
    def load_lang(self, lang_code: str):
        path = os.path.join(self.locales_dir, f"{lang_code.lower()}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
            self.lang = lang_code
            
    def get(self, key: str) -> str:
        return self.translations.get(key, key)
