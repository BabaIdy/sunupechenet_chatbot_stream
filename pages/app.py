
import streamlit as st
import pandas as pd
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import glob
import json
from datetime import datetime, timedelta
import requests
from llama_index.core import SimpleDirectoryReader

# Configuration de la page
st.set_page_config(
    page_title="SunuPecheNet - Assistant Intelligent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Charger les variables d'environnement
load_dotenv()

# ========== FONCTIONS DE LECTURE DE FICHIERS ==========

def load_pdf_with_llamaindex(pdf_path):
    """
    Charge et extrait le texte d'un PDF avec llama-index
    """
    try:
        reader = SimpleDirectoryReader(input_files=[pdf_path])
        documents = reader.load_data()
        text = "\n".join([doc.text for doc in documents])
        return text
    except Exception as e:
        st.error(f"Erreur lors de la lecture du PDF {pdf_path}: {e}")
        return None

def load_csv_with_encoding(file_path):
    """
    Charge un CSV en essayant différents encodages
    """
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']

    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            st.error(f"Erreur lors du chargement de {file_path}: {e}")
            return None

    st.error(f"Impossible de lire {file_path} avec les encodages testés")
    return None

# ========== FONCTIONS OPENWEATHERMAP ==========

def get_weather_data(city="Dakar", lat=None, lon=None):
    api_key = os.getenv("OWM_API_KEY")
    if not api_key:
        return None

    base_url = "http://api.openweathermap.org/data/2.5/weather"

    params = {
        "appid": api_key,
        "units": "metric",
        "lang": "fr"
    }

    if lat and lon:
        params["lat"] = lat
        params["lon"] = lon
    else:
        params["q"] = city

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur API météo: {e}")
        return None

def get_forecast_data(city="Dakar", lat=None, lon=None, days=5):
    api_key = os.getenv("OWM_API_KEY")
    if not api_key:
        return None

    base_url = "http://api.openweathermap.org/data/2.5/forecast"

    params = {
        "appid": api_key,
        "units": "metric",
        "lang": "fr"
    }

    if lat and lon:
        params["lat"] = lat
        params["lon"] = lon
    else:
        params["q"] = city

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur API prévisions: {e}")
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
            ],
            "tomorrow": [
                {"type": "haute", "time": "06:15", "height": "1.3m"},
                {"type": "basse", "time": "12:30", "height": "0.2m"},
                {"type": "haute", "time": "18:35", "height": "1.4m"}
            ]
        },
        # … autres villes inchangées …
    }
    return tide_data

def format_weather_for_context(weather_data, forecast_data=None):
    if not weather_data:
        return ""

    context = "\n=== DONNEES METEO EN TEMPS REEL (OpenWeatherMap) ===\n\n"
    context += f"Lieu: {weather_data.get('name', 'N/A')}\n"
    context += f"Temperature: {weather_data['main']['temp']}°C (Ressenti: {weather_data['main']['feels_like']}°C)\n"
    context += f"Conditions: {weather_data['weather'][0]['description']}\n"
    context += f"Vent: {weather_data['wind']['speed']} m/s, Direction: {weather_data['wind'].get('deg', 'N/A')}°\n"
    context += f"Humidite: {weather_data['main']['humidity']}%\n"
    context += f"Pression: {weather_data['main']['pressure']} hPa\n"
    if 'visibility' in weather_data:
        context += f"Visibilite: {weather_data['visibility']/1000} km\n"
    if 'clouds' in weather_data:
        context += f"Couverture nuageuse: {weather_data['clouds']['all']}%\n"

    # Prévisions
    if forecast_data and 'list' in forecast_data:
        context += "\nPREVISIONS SUR 5 JOURS:\n"
        for i, forecast in enumerate(forecast_data['list'][:8]):
            dt = datetime.fromtimestamp(forecast['dt'])
            context += f"\n{dt.strftime('%d/%m a %Hh')}:\n"
            context += f"   - Temperature: {forecast['main']['temp']}°C\n"
            context += f"   - Conditions: {forecast['weather'][0]['description']}\n"
            context += f"   - Vent: {forecast['wind']['speed']} m/s\n"
            context += f"   - Humidite: {forecast['main']['humidity']}%\n"

    # Marées
    tide_data = get_tide_data()
    city_name = weather_data.get('name', 'Dakar')
    current_time = tide_data.get(city_name, {}).get('current_time', datetime.now().strftime("%H:%M"))

    if city_name in tide_data:
        context += f"\n\n=== HORAIRES DES MAREES A {city_name.upper()} ===\n"
        context += f"HEURE ACTUELLE: {current_time}\n\n"
        context += "AUJOURD'HUI:\n"
        for tide in tide_data[city_name]['today']:
            context += f"Maree {tide['type']}: {tide['time']} ({tide['height']})\n"
        context += "\nDEMAIN:\n"
        for tide in tide_data[city_name]['tomorrow']:
            context += f"Maree {tide['type']}: {tide['time']} ({tide['height']})\n"

    context += "\n" + "="*60 + "\n"
    return context

# ========== DÉTECTION INTELLIGENTE DES QUESTIONS ==========

def analyze_question_type(question):
    question_lower = question.lower()
    analysis = {
        'needs_weather': False,
        'needs_tide': False,
        'needs_statistics': False,
        'needs_species': False,
        'needs_regulations': False,
        'needs_platform_info': False,
        'needs_comparison': False,
        'city': None
    }
    # … mots-clés inchangés …
    # … logique inchangée …

    # Détection de la ville
    cities = {
        'dakar': 'Dakar',
        'saint-louis': 'Saint-Louis',
        'saint louis': 'Saint-Louis',
        'thiès': 'Thiès',
        'thies': 'Thiès',
        'mbour': 'Mbour',
        'joal': 'Joal-Fadiouth',
        'ziguinchor': 'Ziguinchor',
        'kayar': 'Kayar',
        'kaolack': 'Kaolack'
    }

    for city_key, city_name in cities.items():
        if city_key in question_lower:
            analysis['city'] = city_name
            break

    if not analysis['city']:
        analysis['city'] = "Dakar"

    return analysis

# ========== CHARGEMENT DES DONNÉES ==========

@st.cache_data
def load_all_data():
    """
    Charge tous les fichiers CSV, PDF et JSON du dossier data
    """
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'data'),
        os.path.join(os.path.dirname(__file__), 'data'),
        'data',
        '../data'
    ]

    data_folder = None
    for path in possible_paths:
        if os.path.exists(path):
            data_folder = path
            break

    if not data_folder:
        return {}

    all_data = {}

    # Charger CSV
    csv_files = glob.glob(os.path.join(data_folder, '*.csv'))
    for file in csv_files:
        filename = os.path.basename(file)
        try:
            df = load_csv_with_encoding(file)
            if df is not None:
                all_data[filename] = {'type': 'csv', 'content': df}
        except Exception as e:
            st.error(f"Erreur CSV {filename}: {e}")

    # Charger PDF
    pdf_files = glob.glob(os.path.join(data_folder, '*.pdf'))
    for file in pdf_files:
        filename = os.path.basename(file)
        try:
            text = load_pdf_with_llamaindex(file)
            if text:
                all_data[filename] = {'type': 'pdf', 'content': text}
        except Exception as e:
            st.error(f"Erreur PDF {filename}: {e}")

    # Charger JSON
    json_files = glob.glob(os.path.join(data_folder, '*.json'))
    for file in json_files:
        filename = os.path.basename(file)
        try:
            with open(file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                all_data[filename] = {'type': 'json', 'content': json_data}
        except Exception as e:
            st.error(f"Erreur JSON {filename}: {e}")

    return all_data

# ========== RESTE DU CODE ==========

# … le reste de ton code (create_context_from_data, get_chatbot_response, sidebar, chat…) reste identique …

def create_context_from_data(data_dict, include_stats=False, include_species=False, include_regulations=False):
    """
    Crée un contexte INTELLIGENT selon les besoins détectés
    """
    context = "DONNEES DISPONIBLES:\n\n"
    context += f"Date actuelle: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

    for filename, data_info in data_dict.items():
        # Filtrage intelligent
        if not include_stats and 'statistique' in filename.lower():
            continue
        if not include_species and 'espece' in filename.lower():
            continue
        if not include_regulations and ('reglement' in filename.lower() or 'loi' in filename.lower()):
            continue

        context += f"=== {filename} ===\n"

        if data_info['type'] == 'csv':
            df = data_info['content']
            context += f"Type: CSV\n"
            context += f"Colonnes: {', '.join(df.columns.tolist())}\n"
            context += f"Lignes: {len(df)}\n"

            if len(df) > 0:
                context += "\nECHANTILLON (20 premières lignes):\n"
                context += df.head(20).to_string(index=False)
            context += "\n"

        elif data_info['type'] == 'pdf':
            text = data_info['content']
            context += f"Type: PDF\n"
            if len(text) > 2000:
                context += "EXTRAIT:\n" + text[:2000] + "...\n"
            else:
                context += "CONTENU:\n" + text + "\n"

        elif data_info['type'] == 'json':
            json_content = data_info['content']
            context += f"Type: JSON\n"
            json_str = json.dumps(json_content, indent=2, ensure_ascii=False)
            if len(json_str) > 1000:
                context += "EXTRAIT:\n" + json_str[:1000] + "...\n"
            else:
                context += "CONTENU:\n" + json_str + "\n"

        context += "\n"

    return context

# ========== CHATBOT AMÉLIORÉ ==========

def get_chatbot_response(messages, base_context, user_question):
    """
    Génère une réponse INTELLIGENTE en combinant les bonnes sources
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Analyse intelligente de la question
    analysis = analyze_question_type(user_question)

    # Construction du contexte selon les besoins
    final_context = ""

    # 1. Ajouter météo si nécessaire
    if analysis['needs_weather'] or analysis['needs_tide']:
        weather_data = get_weather_data(city=analysis['city'])
        forecast_data = get_forecast_data(city=analysis['city'])
        weather_context = format_weather_for_context(weather_data, forecast_data)
        final_context += weather_context

    # 2. Ajouter données locales filtrées
    filtered_context = create_context_from_data(
        st.session_state.all_data,
        include_stats=analysis['needs_statistics'],
        include_species=analysis['needs_species'],
        include_regulations=analysis['needs_regulations']
    )
    final_context += filtered_context

    current_datetime = datetime.now().strftime("%d/%m/%Y à %H:%M")

    system_message = {
        "role": "system",
        "content": f"""Tu es SunuPecheNet, assistant expert en pêche au Sénégal.

DATE ET HEURE: {current_datetime}

=== INSTRUCTIONS INTELLIGENCE AUGMENTÉE ===

Tu disposes de DEUX sources de données complémentaires:
1. DONNÉES EN TEMPS RÉEL (météo, marées) - priorité pour conditions actuelles
2. DONNÉES HISTORIQUES/STATISTIQUES (CSV, PDF, JSON) - priorité pour analyses

RÈGLES DE COMBINAISON INTELLIGENTE:

1. QUESTIONS MIXTES (ex: "Quelles sont les statistiques de pêche et les conditions météo?"):
   → Utilise LES DEUX sources
   → Structure: d'abord météo/marées, puis statistiques
   → Fais des LIENS: "Avec ces conditions + ces statistiques historiques, je recommande..."

2. COMPARAISONS (ex: "Quelle ville est meilleure pour pêcher demain?"):
   → Récupère météo de PLUSIEURS villes
   → Compare avec statistiques de capture par région
   → Donne un classement justifié

3. PRÉVISIONS ENRICHIES (ex: "Conseils pour pêcher le thiof demain"):
   → Météo + marées pour timing
   → Statistiques espèce (prix, quotas, zones)
   → Conseil complet et personnalisé

4. QUESTIONS STATISTIQUES SEULES (ex: "Évolution des captures 2019"):
   → Utilise UNIQUEMENT les CSV/PDF/JSON
   → Pas besoin de météo

5. TON STYLE:
   - Professionnel mais accessible
   - Justifie avec des DONNÉES CHIFFRÉES
   - Structure claire: Météo → Marées → Stats → Conseil final
   - Si données manquantes, dis-le clairement

{final_context}

IMPORTANT: Les données ci-dessus sont RÉELLES. Utilise-les intelligemment!"""
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[system_message] + messages,
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur: {e}"

# ========== INITIALISATION ==========

if "messages" not in st.session_state:
    st.session_state.messages = []

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.all_data = {}

# ========== SIDEBAR ==========

with st.sidebar:
    logo_paths = [
        Path("pages/image/logo_sunupechenet.png"),
        Path("image/logo_sunupechenet.png"),
        Path("logo_sunupechenet.png")
    ]

    for logo_path in logo_paths:
        if logo_path.exists():
            st.image(str(logo_path), width=100)
            break

    st.write("### SunuPecheNet")
    st.write("Assistant intelligent")
    st.divider()

    if st.button("Effacer l'historique"):
        st.session_state.messages = []
        st.rerun()

# ========== CHARGEMENT DONNÉES ==========

if not st.session_state.data_loaded:
    all_data = load_all_data()
    st.session_state.all_data = all_data
    if all_data:
        st.session_state.data_loaded = True

# ========== CHAT ==========

st.title("SunuPecheNet")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if len(st.session_state.messages) == 0:
    welcome_message = "Bienvenue dans le chatbot de SunuPecheNet !"
    with st.chat_message("assistant"):
        st.markdown(welcome_message)
    st.session_state.messages.append({"role": "assistant", "content": welcome_message})

if prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(" Analyse intelligente..."):
            response = get_chatbot_response(
                st.session_state.messages,
                "",  # Le contexte est maintenant géré dans la fonction
                prompt
            )
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})