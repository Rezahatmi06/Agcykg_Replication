import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("API Key tidak ditemukan di file .env!")
else:
    print("Sedang memeriksa hak akses API Key...")
    genai.configure(api_key=api_key)
    try:
        print("--- Daftar Model yang Bisa Diakses API Key Ini ---")
        models_found = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
                models_found = True
        
        if not models_found:
            print("Tidak ada model Gemini yang terbuka untuk API Key ini.")
        print("--------------------------------------------------")
    except Exception as e:
        print(f"Peringatan! Error Koneksi/API Key: {e}")