import os
import google.generativeai as genai

key = os.environ.get("GEMINI_KEY") or input("Paste Gemini API key (visible): ")
genai.configure(api_key=key)
for m in genai.list_models():
    print(m.name)