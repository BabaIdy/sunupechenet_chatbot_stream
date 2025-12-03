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
        },
        "Kaolack": {
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

    # Prévisions détaillées par jour
    if forecast_data and 'list' in forecast_data:
        context += "\nPREVISIONS DETAILLEES SUR 5 JOURS:\n"
        jours_semaine = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

        # Grouper les prévisions par jour
        previsions_par_jour = {}
        for forecast in forecast_data['list']:
            dt = datetime.fromtimestamp(forecast['dt'])
            date_key = dt.strftime('%Y-%m-%d')
            jour_nom = jours_semaine[dt.weekday()]
            date_formatee = dt.strftime('%d/%m/%Y')

            if date_key not in previsions_par_jour:
                previsions_par_jour[date_key] = {
                    'jour': jour_nom,
                    'date': date_formatee,
                    'previsions': []
                }

            previsions_par_jour[date_key]['previsions'].append({
                'heure': dt.strftime('%Hh'),
                'temp': forecast['main']['temp'],
                'conditions': forecast['weather'][0]['description'],
                'vent': forecast['wind']['speed'],
                'humidite': forecast['main']['humidity']
            })

        # Afficher les prévisions par jour
        for date_key in sorted(previsions_par_jour.keys())[:5]:
            jour_info = previsions_par_jour[date_key]
            context += f"\n{jour_info['jour'].upper()} {jour_info['date']}:\n"

            # Prendre 3-4 moments clés de la journée
            for prev in jour_info['previsions'][:4]:
                context += f"   {prev['heure']}: {prev['temp']}°C, {prev['conditions']}, "
                context += f"vent {prev['vent']} m/s, humidité {prev['humidite']}%\n"

    # Ajouter les données de marée
    tide_data = get_tide_data()
    city_name = weather_data.get('name', 'Dakar')

    # Vérifier si la ville existe dans tide_data, sinon utiliser Dakar par défaut
    if city_name not in tide_data:
        city_name = 'Dakar'

    city_tide = tide_data[city_name]
    context += f"\n\n=== HORAIRES DES MAREES A {city_name.upper()} ===\n"
    context += f"HEURE ACTUELLE: {city_tide.get('current_time', 'N/A')}\n\n"
    context += f"AUJOURD'HUI ({city_tide.get('today_day', 'N/A')} {city_tide.get('today_date', 'N/A')}):\n"
    for tide in city_tide.get('today', []):
        context += f"Maree {tide['type']}: {tide['time']} ({tide['height']})\n"

    context += f"\nDEMAIN ({city_tide.get('tomorrow_day', 'N/A')} {city_tide.get('tomorrow_date', 'N/A')}):\n"
    for tide in city_tide.get('tomorrow', []):
        context += f"Maree {tide['type']}: {tide['time']} ({tide['height']})\n"

    context += f"\n*** IMPORTANT: Compare l'heure actuelle ({city_tide.get('current_time', 'N/A')}) avec les horaires de marée ***\n"
    context += f"*** Ne recommande QUE les créneaux FUTURS (après {city_tide.get('current_time', 'N/A')}) ***\n\n"

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

# ========== NOUVELLE FONCTION: DÉTECTION INTELLIGENTE DES QUESTIONS ==========

def analyze_question_type(question):
    """
    Analyse intelligemment le type de question pour déterminer quelles données utiliser
    Returns: dict avec les flags nécessaires
    """
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

    # Mots-clés météo
    weather_keywords = ['météo', 'meteo', 'temps', 'température', 'temperature', 'vent',
                       'pluie', 'soleil', 'nuage', 'prévision', 'prevision', 'conditions']

    # Mots-clés marée
    tide_keywords = ['marée', 'maree', 'marées', 'marees', 'haute', 'basse', 'flux',
                    'horaire', 'moment', 'quand']

    # Mots-clés pêche (besoin de combiner météo + marée)
    fishing_keywords = ['pêcher', 'pecher', 'pêche', 'peche', 'partir', 'sortie',
                       'aller', 'conseille', 'conseil', 'recommande']

    # Mots-clés statistiques
    stats_keywords = ['statistique', 'statistiques', 'données', 'donnees', 'capture',
                     'débarquement', 'debarquement', 'tendance', 'volume', 'tonnage']

    # Mots-clés espèces
    species_keywords = ['thiof', 'sardinelle', 'capitaine', 'poisson', 'espèce', 'espece',
                       'prix', 'valeur', 'quota']

    # Mots-clés réglementation
    regulation_keywords = ['règle', 'regle', 'réglementation', 'reglementation', 'loi',
                          'interdit', 'autorisé', 'autorise', 'permis', 'licence']

    # Mots-clés plateforme
    platform_keywords = ['sunupechenet', 'pechenet', 'sunu', 'plateforme', 'application', 'app',
                        'fonctionnalité', 'fonctionnalite', 'comment', 'utiliser']

    # Mots-clés comparaison
    comparison_keywords = ['comparer', 'comparaison', 'différence', 'difference',
                          'meilleur', 'vs', 'entre']

    # Détection des besoins
    if any(kw in question_lower for kw in weather_keywords):
        analysis['needs_weather'] = True

    if any(kw in question_lower for kw in tide_keywords):
        analysis['needs_tide'] = True

    if any(kw in question_lower for kw in fishing_keywords):
        analysis['needs_weather'] = True
        analysis['needs_tide'] = True

    if any(kw in question_lower for kw in stats_keywords):
        analysis['needs_statistics'] = True

    if any(kw in question_lower for kw in species_keywords):
        analysis['needs_species'] = True
        analysis['needs_statistics'] = True  # Souvent liées

    if any(kw in question_lower for kw in regulation_keywords):
        analysis['needs_regulations'] = True

    if any(kw in question_lower for kw in platform_keywords):
        analysis['needs_platform_info'] = True

    if any(kw in question_lower for kw in comparison_keywords):
        analysis['needs_comparison'] = True
        analysis['needs_statistics'] = True
        analysis['needs_weather'] = True

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
        'kaolack': 'kaolack'
    }

    for city_key, city_name in cities.items():
        if city_key in question_lower:
            analysis['city'] = city_name
            break

    if not analysis['city']:
        analysis['city'] = "Dakar"  # Par défaut

    return analysis

# ========== CHARGEMENT DES DONNÉES ==========

@st.cache_data
def load_all_data():
    """
    Charge tous les fichiers CSV, PDF et JSON du dossier data
    """
    # CORRECTION: __file__ au lieu de _file_
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

    # Charger les PDF
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

    # Date et heure actuelles avec jour de la semaine
    now = datetime.now()
    current_datetime = now.strftime("%d/%m/%Y à %H:%M")
    jours_semaine = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    jour_actuel = jours_semaine[now.weekday()]

    # Calculer les 7 prochains jours avec leurs dates
    prochains_jours = ""
    for i in range(7):
        future_date = now + timedelta(days=i)
        jour_nom = jours_semaine[future_date.weekday()]
        if i == 0:
            prochains_jours += f"- AUJOURD'HUI ({jour_nom}) : {future_date.strftime('%d/%m/%Y')}\n"
        elif i == 1:
            prochains_jours += f"- DEMAIN ({jour_nom}) : {future_date.strftime('%d/%m/%Y')}\n"
        else:
            prochains_jours += f"- {jour_nom.upper()} : {future_date.strftime('%d/%m/%Y')}\n"

    system_message = {
        "role": "system",
        "content": f"""Tu es SunuPecheNet, assistant expert en pêche au Sénégal.

DATE ET HEURE ACTUELLES: {jour_actuel} {current_datetime}

CALENDRIER DES 7 PROCHAINS JOURS:
{prochains_jours}

=== INSTRUCTIONS CRITIQUES SUR LES DATES ===

COMPRENDRE LES JOURS:
- Quand l'utilisateur dit "jeudi", "vendredi", "samedi", etc., tu DOIS:
  1. Regarder le calendrier ci-dessus
  2. Identifier la DATE EXACTE correspondante
  3. Utiliser les prévisions météo disponibles pour CETTE DATE précise

EXEMPLES:
- Si aujourd'hui = mercredi 03/12/2025:
  * "jeudi" = 04/12/2025 (demain)
  * "vendredi" = 05/12/2025 (dans 2 jours)
  * "samedi" = 06/12/2025 (dans 3 jours)
  * "dimanche" = 07/12/2025 (dans 4 jours)

- Si l'utilisateur demande "la météo de samedi":
  1. Tu identifies: samedi = 06/12/2025
  2. Tu cherches dans les PRÉVISIONS MÉTÉO les données pour le 06/12
  3. Tu réponds: "Pour samedi 6 décembre 2025, voici les prévisions..."

ERREUR À ÉVITER:
❌ "Je n'ai pas accès aux prévisions pour ce jour"
✅ "Pour samedi 6 décembre 2025, selon les prévisions: [données météo]"

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

5. QUESTIONS SUR DES JOURS FUTURS (ex: "Météo pour vendredi", "Peut-on pêcher samedi?"):
   → TOUJOURS convertir le jour en date exacte via le calendrier
   → Chercher les prévisions pour CETTE DATE dans les données fournies
   → Répondre avec la date complète: "Pour vendredi 5 décembre 2025..."

6. TON STYLE:
   - Professionnel mais accessible
   - Justifie avec des DONNÉES CHIFFRÉES
   - Structure claire: Date exacte → Météo → Marées → Conseil final
   - TOUJOURS préciser la date complète quand tu parles d'un jour futur
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
        with st.spinner("🔍 Analyse intelligente en cours..."):
            try:
                response = get_chatbot_response(
                    st.session_state.messages,
                    "",  # Le contexte est maintenant géré dans la fonction
                    prompt
                )
                st.markdown(response)
            except Exception as e:
                error_message = f"❌ Une erreur s'est produite : {str(e)}\n\nVeuillez réessayer ou reformuler votre question."
                st.error(error_message)
                response = error_message

    st.session_state.messages.append({"role": "assistant", "content": response})