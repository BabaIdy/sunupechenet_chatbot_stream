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

        # Combiner tout le texte des documents
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
    """
    Récupère les données météo actuelles depuis OpenWeatherMap
    """
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
    """
    Récupère les prévisions météo sur plusieurs jours
    """
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
    """
    Récupère les données de marée pour les principales villes de pêche du Sénégal
    """
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
        "Saint-Louis": {
            "current_time": current_time,
            "today": [
                {"type": "haute", "time": "05:15", "height": "1.4m"},
                {"type": "basse", "time": "11:30", "height": "0.2m"},
                {"type": "haute", "time": "17:35", "height": "1.5m"},
                {"type": "basse", "time": "23:40", "height": "0.1m"}
            ],
            "tomorrow": [
                {"type": "haute", "time": "06:00", "height": "1.5m"},
                {"type": "basse", "time": "12:15", "height": "0.1m"},
                {"type": "haute", "time": "18:20", "height": "1.6m"}
            ]
        },
        "Mbour": {
            "current_time": current_time,
            "today": [
                {"type": "haute", "time": "05:45", "height": "1.1m"},
                {"type": "basse", "time": "12:00", "height": "0.4m"},
                {"type": "haute", "time": "18:05", "height": "1.2m"}
            ],
            "tomorrow": [
                {"type": "haute", "time": "06:30", "height": "1.2m"},
                {"type": "basse", "time": "12:45", "height": "0.3m"},
                {"type": "haute", "time": "18:50", "height": "1.3m"}
            ]
        },
        "Kayar": {
            "current_time": current_time,
            "today": [
                {"type": "haute", "time": "05:20", "height": "1.3m"},
                {"type": "basse", "time": "11:35", "height": "0.3m"},
                {"type": "haute", "time": "17:40", "height": "1.4m"},
                {"type": "basse", "time": "23:45", "height": "0.2m"}
            ],
            "tomorrow": [
                {"type": "haute", "time": "06:05", "height": "1.4m"},
                {"type": "basse", "time": "12:20", "height": "0.2m"},
                {"type": "haute", "time": "18:25", "height": "1.5m"}
            ]
        },
        "Joal-Fadiouth": {
            "current_time": current_time,
            "today": [
                {"type": "haute", "time": "05:50", "height": "1.1m"},
                {"type": "basse", "time": "12:05", "height": "0.4m"},
                {"type": "haute", "time": "18:10", "height": "1.2m"}
            ],
            "tomorrow": [
                {"type": "haute", "time": "06:35", "height": "1.2m"},
                {"type": "basse", "time": "12:50", "height": "0.3m"},
                {"type": "haute", "time": "18:55", "height": "1.3m"}
            ]
        }
    }
    return tide_data
    return tide_data

def format_weather_for_context(weather_data, forecast_data=None):
    """
    Formate les données météo pour le contexte du chatbot
    """
    if not weather_data:
        return ""

    context = "\n=== DONNEES METEO EN TEMPS REEL (OpenWeatherMap) ===\n\n"

    # Météo actuelle
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

    # Ajouter les données de marée
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

        context += f"\n*** IMPORTANT: Compare l'heure actuelle ({current_time}) avec les horaires de marée ***\n"
        context += f"*** Ne recommande QUE les créneaux FUTURS (après {current_time}) ***\n\n"

        context += "\nREGLES D'OR DE LA PECHE AUX MAREES:\n"
        context += "MEILLEURS MOMENTS (poissons tres actifs):\n"
        context += "   - 2h AVANT maree haute (maree montante)\n"
        context += "   - 2h APRES debut maree haute (debut de descente)\n"
        context += "   - Pendant la MAREE MONTANTE (flux)\n"
        context += "\nMOMENTS MOYENS:\n"
        context += "   - Debut de maree descendante\n"
        context += "   - 1h apres maree basse\n"
        context += "\nA EVITER (poissons inactifs):\n"
        context += "   - Maree haute STATIONNAIRE (etale haute mer)\n"
        context += "   - Maree basse STATIONNAIRE (etale basse mer)\n"
        context += "   - Ces moments l'eau ne bouge pas = poissons dorment\n"

    context += "\n" + "="*60 + "\n"
    return context

def is_weather_question(question):
    """
    Détecte si la question concerne la météo ou les marées
    """
    weather_keywords = [
        'météo', 'meteo', 'temps', 'température', 'temperature', 'vent', 'pluie',
        'soleil', 'nuage', 'prévision', 'prevision', 'climat',
        'conditions', 'mer', 'vague', 'houle', 'tempête', 'tempete',
        'orage', 'brouillard', 'visibilité', 'visibilite',
        'marée', 'maree', 'marées', 'marees', 'haute', 'basse', 'flux',
        'pêcher', 'pecher', 'pêche', 'peche', 'quand', 'moment', 'meilleur',
        'partir', 'sortie', 'aller', 'conseille', 'conseil', 'recommande'
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in weather_keywords)

# ========== CHARGEMENT DES DONNÉES ==========

@st.cache_data
def load_all_data():
    """
    Charge tous les fichiers CSV, PDF et JSON du dossier data
    """
    # Essayer différents chemins pour le dossier data
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

    # Charger les CSV
    csv_files = glob.glob(os.path.join(data_folder, '*.csv'))
    for file in csv_files:
        filename = os.path.basename(file)
        try:
            df = load_csv_with_encoding(file)
            if df is not None:
                all_data[filename] = {'type': 'csv', 'content': df}
        except Exception as e:
            st.error(f"Erreur CSV {filename}: {e}")

    # Charger les PDF avec llama-index
    pdf_files = glob.glob(os.path.join(data_folder, '*.pdf'))
    for file in pdf_files:
        filename = os.path.basename(file)
        try:
            text = load_pdf_with_llamaindex(file)
            if text:
                all_data[filename] = {'type': 'pdf', 'content': text}
        except Exception as e:
            st.error(f"Erreur PDF {filename}: {e}")

    # Charger les JSON
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

def create_context_from_data(data_dict):
    """
    Crée le contexte pour le chatbot à partir des CSV, PDF et JSON (optimisé)
    """
    context = "DONNEES DISPONIBLES POUR REPONDRE AUX QUESTIONS:\n\n"
    context += f"NOTE IMPORTANTE: Date actuelle = {datetime.now().strftime('%d/%m/%Y')}\n\n"

    for filename, data_info in data_dict.items():
        context += f"=== {filename} ===\n"

        if data_info['type'] == 'csv':
            df = data_info['content']
            context += f"Type: CSV\n"
            context += f"Colonnes: {', '.join(df.columns.tolist())}\n"
            context += f"Lignes: {len(df)}\n"

            # Limiter à 20 lignes maximum
            if len(df) > 0:
                context += "\nECHANTILLON (20 premières lignes):\n"
                context += df.head(20).to_string(index=False)
            context += "\n"

        elif data_info['type'] == 'pdf':
            text = data_info['content']
            context += f"Type: PDF\n"

            # Limiter à 2000 caractères
            if len(text) > 2000:
                context += "EXTRAIT:\n" + text[:2000] + "...\n"
            else:
                context += "CONTENU:\n" + text + "\n"

        elif data_info['type'] == 'json':
            json_content = data_info['content']
            context += f"Type: JSON\n"
            json_str = json.dumps(json_content, indent=2, ensure_ascii=False)

            # Limiter à 1000 caractères
            if len(json_str) > 1000:
                context += "EXTRAIT:\n" + json_str[:1000] + "...\n"
            else:
                context += "CONTENU:\n" + json_str + "\n"

        context += "\n"

    return context

# ========== CHATBOT ==========

def get_chatbot_response(messages, context, user_question):
    """
    Génère une réponse en incluant les données météo si nécessaire
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Récupérer données météo pour questions de pêche
    weather_context = ""
    fishing_keywords = ['pêcher', 'pecher', 'pêche', 'peche', 'sortie', 'mer', 'conditions', 'marée', 'maree']

    if is_weather_question(user_question) or any(kw in user_question.lower() for kw in fishing_keywords):
        cities = {
            'dakar': 'Dakar',
            'saint-louis': 'Saint-Louis',
            'saint louis': 'Saint-Louis',
            'thiès': 'Thiès',
            'thies': 'Thiès',
            'mbour': 'Mbour',
            'joal': 'Joal-Fadiouth',
            'ziguinchor': 'Ziguinchor',
            'kayar': 'Kayar'
        }

        city = "Dakar"
        question_lower = user_question.lower()
        for city_key, city_name in cities.items():
            if city_key in question_lower:
                city = city_name
                break

        weather_data = get_weather_data(city=city)
        forecast_data = get_forecast_data(city=city)
        weather_context = format_weather_for_context(weather_data, forecast_data)

    current_date = datetime.now().strftime("%d/%m/%Y")
    current_datetime = datetime.now().strftime("%d/%m/%Y à %H:%M")

    system_message = {
        "role": "system",
        "content": f"""Tu es SunuPecheNet, un assistant expert en pêche au Sénégal. Tu es INTELLIGENT et tes réponses sont PERTINENTES, JUSTIFIÉES et BASÉES SUR DES DONNÉES RÉELLES.

DATE ET HEURE ACTUELLES: {current_datetime}

=== RÈGLES CRITIQUES D'INTELLIGENCE ===

1. UTILISE TOUJOURS LES DONNÉES RÉELLES:
   - Tu as accès aux données météo EN TEMPS RÉEL d'OpenWeatherMap
   - Tu as accès aux horaires de marée PRÉCIS
   - Tu as accès aux fichiers CSV/PDF/JSON avec des données réelles
   - NE DIS JAMAIS "je n'ai pas accès" si les données sont dans le contexte
   - ANALYSE les données et JUSTIFIE tes réponses

2. TEMPÉRATURE ET MÉTÉO:
   - Les données météo sont DANS LE CONTEXTE ci-dessous
   - Lis la section "=== DONNEES METEO EN TEMPS REEL ==="
   - Donne la température EXACTE mentionnée
   - Exemple: Si tu vois "Temperature: 28°C", dis "La température actuelle est de 28°C"

3. HORAIRES DE MARÉE PAR VILLE:
   - KAYAR: Marées disponibles (cherche "KAYAR" dans le contexte)
   - DAKAR: Marées disponibles
   - MBOUR: Marées disponibles
   - SAINT-LOUIS: Marées disponibles
   - JOAL: Marées disponibles
   - KAOLACK: Ville INTÉRIEURE (pas de marée, utilise Dakar comme référence la plus proche)

4. CONSEILS INTELLIGENTS ET JUSTIFIÉS:
   Quand on te demande "qu'elle conseille" ou "quand partir":

   a) ANALYSE LA MÉTÉO:
      - Vent: Si < 10 m/s = "Excellent, mer calme"
             Si 10-15 m/s = "Acceptable, attention aux vagues"
             Si > 15 m/s = "DANGEREUX, restez à terre"
      - Température: Mentionne-la toujours
      - Visibilité: Si < 5 km = "Visibilité réduite, soyez prudent"

   b) ANALYSE LES MARÉES:
      - Calcule les créneaux OPTIMAUX (2h avant marée haute)
      - Vérifie l'HEURE ACTUELLE
      - Si créneaux passés → propose DEMAIN
      - JUSTIFIE: "La marée montante apporte nourriture et oxygène, les poissons sont actifs"

   c) DONNE UN CONSEIL COMPLET:
      Format idéal:
      "D'après les conditions actuelles:
      - Météo: [température], vent [vitesse] → [évaluation]
      - Marée haute à [heure]
      - Meilleur créneau: [heure début]-[heure fin]
      - Pourquoi: [justification basée sur marée et météo]"

5. QUESTIONS SUR LA PLATEFORME:
   - Utilise les informations des fichiers PDF
   - Sois précis sur les 6 fonctionnalités de SunuPecheNet

6. VILLES SPÉCIFIQUES:
   - Si l'utilisateur mentionne SA ville (ex: "je suis de Kayar"), utilise les données de CETTE ville
   - Adapte TOUS les conseils à sa localisation
   - Mentionne la ville dans ta réponse

7. TON ET STYLE:
   - Professionnel mais accessible
   - Justifie TOUJOURS tes recommandations
   - Pas d'emojis
   - Concis mais complet

{weather_context}

{context}

IMPORTANT: Les données météo et marées sont ci-dessus. LIS-LES et UTILISE-LES dans tes réponses!"""
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modèle plus récent avec 128k tokens
            messages=[system_message] + messages,
            temperature=0.3,
            max_tokens=1000
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
    st.session_state.context = ""

# ========== SIDEBAR ==========

with st.sidebar:
    # Logo
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
    st.write("*Assistant intelligent*")
    st.divider()

    # Action unique
    if st.button("Effacer l'historique"):
        st.session_state.messages = []
        st.rerun()

# ========== CHARGEMENT DONNÉES (silencieux) ==========

if not st.session_state.data_loaded:
    all_data = load_all_data()
    st.session_state.all_data = all_data
    if all_data:
        st.session_state.context = create_context_from_data(all_data)
        st.session_state.data_loaded = True

# ========== CHAT ==========

st.title("SunuPecheNet")

# Historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Message de bienvenue initial (une seule fois)
if len(st.session_state.messages) == 0:
    welcome_message = "Bienvenue dans le chatbot de SunuPecheNet !"
    with st.chat_message("assistant"):
        st.markdown(welcome_message)
    st.session_state.messages.append({"role": "assistant", "content": welcome_message})

# Input
if prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(" Analyse..."):
            response = get_chatbot_response(
                st.session_state.messages,
                st.session_state.context,
                prompt
            )
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})