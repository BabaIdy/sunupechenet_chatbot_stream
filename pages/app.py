import streamlit as st
import pandas as pd
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import glob
import json
from datetime import datetime
import requests
from llama_index.core import SimpleDirectoryReader
import tempfile
import sounddevice as sd
import soundfile as sf
from gtts import gTTS

# ======= CONFIGURATION PAGE =======
st.set_page_config(
    page_title="SunuPecheNet - Assistant Intelligent",
    layout="wide"
)

# ======= CHARGER VARIABLES D'ENV =======
load_dotenv()

# ======= INITIALISATION SESSION =======
if "messages" not in st.session_state:
    st.session_state.messages = []
if "all_data" not in st.session_state:
    st.session_state.all_data = {}
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False

# ======= FONCTIONS DE LECTURE DE FICHIERS =======
def load_pdf_with_llamaindex(pdf_path):
    try:
        reader = SimpleDirectoryReader(input_files=[pdf_path])
        documents = reader.load_data()
        text = "\n".join([doc.text for doc in documents])
        return text
    except Exception as e:
        st.error(f"Erreur lecture PDF {pdf_path}: {e}")
        return None

def load_csv_with_encoding(file_path):
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            st.error(f"Erreur lecture CSV {file_path}: {e}")
            return None
    st.error(f"Impossible de lire {file_path}")
    return None

@st.cache_data
def load_all_data():
    data_paths = ["data", "../data"]
    data_folder = None
    for path in data_paths:
        if os.path.exists(path):
            data_folder = path
            break
    if not data_folder:
        st.warning("Dossier data introuvable.")
        return {}
    all_data = {}
    # CSV
    for file in glob.glob(os.path.join(data_folder, "*.csv")):
        df = load_csv_with_encoding(file)
        if df is not None:
            all_data[os.path.basename(file)] = {"type":"csv", "content":df}
    # PDF
    for file in glob.glob(os.path.join(data_folder, "*.pdf")):
        text = load_pdf_with_llamaindex(file)
        if text:
            all_data[os.path.basename(file)] = {"type":"pdf","content":text}
    # JSON
    for file in glob.glob(os.path.join(data_folder, "*.json")):
        with open(file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            all_data[os.path.basename(file)] = {"type":"json","content":json_data}
    return all_data

# ======= FONCTIONS AUDIO =======
def record_audio(duration=5, fs=16000):
    st.info(f"Enregistrement {duration}s...")
    recording = sd.rec(int(duration*fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp_file.name, recording, fs)
    return tmp_file.name

def transcribe_audio(file_path):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with open(file_path,"rb") as f:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
    return transcript.text

def speak_text(text, lang="fr"):
    tts = gTTS(text=text, lang=lang)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp_file.name)
    audio_bytes = open(tmp_file.name,"rb").read()
    st.audio(audio_bytes, format="audio/mp3")

# ======= FONCTIONS METEO ET MAREES =======
def get_weather_data(city="Dakar"):
    api_key = os.getenv("OWM_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q":city, "appid":api_key, "units":"metric", "lang":"fr"},
            timeout=10
        )
        return resp.json()
    except:
        return None

def get_forecast_data(city="Dakar"):
    api_key = os.getenv("OWM_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "http://api.openweathermap.org/data/2.5/forecast",
            params={"q":city, "appid":api_key, "units":"metric", "lang":"fr"},
            timeout=10
        )
        return resp.json()
    except:
        return None

def get_tide_data():
    current_time = datetime.now().strftime("%H:%M")
    tide_data = {
        "Dakar": {
            "current_time": current_time,
            "today": [
                {"type": "haute", "time": "05:30", "height": "1.2m"},
                {"type": "basse", "time": "11:45", "height": "0.3m"},
                {"type": "haute", "time": "17:50", "height": "1.3m"},
                {"type": "basse", "time": "23:55", "height": "0.2m"}
            ]
        }
    }
    return tide_data

def format_weather_for_context(weather_data, forecast_data=None):
    if not weather_data:
        return ""
    context = f"Lieu: {weather_data.get('name','N/A')}, Temp: {weather_data['main']['temp']}°C, Conditions: {weather_data['weather'][0]['description']}\n"
    tide_data = get_tide_data()
    city = weather_data.get('name','Dakar')
    if city in tide_data:
        context += f"Maree actuelle: {tide_data[city]['current_time']}\n"
    return context

# ======= CONTEXTE CHAT =======
def create_context_from_data(data_dict):
    context = ""
    for fname, info in data_dict.items():
        context += f"\n=== {fname} ===\n"
        if info["type"]=="csv":
            df = info["content"]
            context += f"Lignes: {len(df)}, Colonnes: {', '.join(df.columns)}\n"
        elif info["type"]=="pdf":
            context += info["content"][:500]+"...\n"
        elif info["type"]=="json":
            context += json.dumps(info["content"], indent=2)[:500]+"...\n"
    return context

def get_chatbot_response(messages, user_question, city="Dakar"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    weather_data = get_weather_data(city)
    forecast_data = get_forecast_data(city)
    weather_context = format_weather_for_context(weather_data, forecast_data)
    local_context = create_context_from_data(st.session_state.all_data)

    system_message = {
        "role":"system",
        "content": f"""
Tu es SunuPecheNet, assistant expert en pêche au Sénégal.
Réponds aux questions de manière claire et précise sur :
- Zones poissonneuses
- Espèces de poissons
- Conditions météo et marées
- Réglementations locales

Contexte météo / marées: {weather_context}
Contexte données locales: {local_context}
"""
    }

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_message]+messages,
            temperature=0.3,
            max_tokens=1500
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Erreur: {e}"

# ======= SIDEBAR =======
with st.sidebar:
    st.title("SunuPecheNet")
    if st.button("Effacer l'historique"):
        st.session_state.messages = []
        st.experimental_rerun()

# ======= CHARGEMENT DONNEES =======
if not st.session_state.data_loaded:
    st.session_state.all_data = load_all_data()
    st.session_state.data_loaded = True

# ======= CHAT TEXTE =======
st.title("SunuPecheNet - Chat intelligent")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Analyse..."):
            response = get_chatbot_response(st.session_state.messages, prompt)
            st.markdown(response)
    st.session_state.messages.append({"role":"assistant","content":response})

# ======= CHAT AUDIO =======
st.divider()
st.subheader("🎤 Posez votre question par la voix")
duration = st.number_input("Durée en secondes", min_value=3, max_value=20, value=5)
if st.button("Enregistrer & poser la question"):
    audio_file = record_audio(duration=duration)
    try:
        question_audio = transcribe_audio(audio_file)
        st.markdown(f"**Vous avez dit :** {question_audio}")
        if question_audio.strip() != "":
            st.session_state.messages.append({"role":"user","content":question_audio})
            with st.chat_message("assistant"):
                with st.spinner("Analyse..."):
                    response = get_chatbot_response(st.session_state.messages, question_audio)
                    st.markdown(response)
                    speak_text(response)
            st.session_state.messages.append({"role":"assistant","content":response})
        else:
            st.warning("La transcription est vide, veuillez réessayer.")
    except Exception as e:
        st.error(f"Erreur transcription audio: {e}")
