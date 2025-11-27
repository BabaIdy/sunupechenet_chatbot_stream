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

# Configuration de la page
st.set_page_config(
    page_title="SunuPecheNet - Assistant Intelligent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Charger les variables d'environnement
load_dotenv()

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
    NOTE: Ces horaires sont approximatifs. Pour des données précises en temps réel,
    il faudrait utiliser une API comme WorldTides ou NOAA.
    """
    from datetime import datetime

    current_hour = datetime.now().hour
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

        context += "\n*** IMPORTANT: Compare l'heure actuelle ({current_time}) avec les horaires de marée ***\n"
        context += "*** Ne recommande QUE les créneaux FUTURS (après {current_time}) ***\n\n"

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
        'météo', 'meteo', 'temps', 'température', 'vent', 'pluie',
        'soleil', 'nuage', 'prévision', 'prevision', 'climat',
        'conditions', 'mer', 'vague', 'houle', 'tempête', 'tempete',
        'orage', 'brouillard', 'visibilité', 'visibilite',
        'marée', 'maree', 'marées', 'marees', 'haute', 'basse', 'flux',
        'pêcher', 'pecher', 'pêche', 'peche', 'quand', 'moment', 'meilleur'
    ]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in weather_keywords)

# ========== FIN FONCTIONS MÉTÉO ==========

# Charger les données CSV
@st.cache_data
def load_csv_data():
    data_folder = os.path.join(os.path.dirname(__file__), '..', 'data')
    csv_files = glob.glob(os.path.join(data_folder, '*.csv'))
    all_data = {}
    for file in csv_files:
        filename = os.path.basename(file)
        try:
            df = pd.read_csv(file)
            all_data[filename] = df
        except Exception as e:
            st.error(f"Erreur lors du chargement de {filename}: {e}")
    return all_data

# Créer le contexte à partir des données
def create_context_from_data(data_dict):
    context = "DONNEES DISPONIBLES POUR REPONDRE AUX QUESTIONS:\n\n"
    context += f"NOTE IMPORTANTE: Date actuelle = {datetime.now().strftime('%d/%m/%Y')}\n"
    context += "Adapte l'utilisation des données selon le contexte temporel de la question!\n\n"

    for filename, df in data_dict.items():
        if filename not in ['users.json', 'conversations.json']:
            context += f"=== {filename} ===\n"
            context += f"Colonnes: {', '.join(df.columns.tolist())}\n"

            # Essayer d'identifier une colonne de date
            date_column = None
            for col in df.columns:
                if 'date' in col.lower() or 'jour' in col.lower():
                    date_column = col
                    break

            if date_column:
                context += f"[COLONNE DATE DETECTEE: {date_column}]\n"
                context += f"Ces données contiennent des informations historiques. Utilise-les intelligemment selon la question.\n"

            context += f"Nombre total d'enregistrements: {len(df)}\n\n"
            if len(df) <= 100:
                context += "DONNEES COMPLETES:\n"
                context += df.to_string(index=False)
            else:
                context += "ECHANTILLON DES DONNEES (50 premieres lignes):\n"
                context += df.head(50).to_string(index=False)
                context += f"\n\n... et {len(df) - 50} autres enregistrements.\n"
            context += "\n\n"
    return context

# Obtenir une réponse du chatbot
def get_chatbot_response(messages, context, user_question):
    """
    Génère une réponse en incluant les données météo si nécessaire
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Récupérer systématiquement les données météo pour les questions de pêche
    weather_context = ""
    fishing_keywords = ['pêcher', 'pecher', 'pêche', 'peche', 'sortie', 'mer', 'conditions', 'marée', 'maree']

    # Si question météo OU question de pêche, récupérer la météo
    if is_weather_question(user_question) or any(kw in user_question.lower() for kw in fishing_keywords):
        # Détecter la ville mentionnée
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

        city = "Dakar"  # Ville par défaut
        question_lower = user_question.lower()
        for city_key, city_name in cities.items():
            if city_key in question_lower:
                city = city_name
                break

        weather_data = get_weather_data(city=city)
        forecast_data = get_forecast_data(city=city)
        weather_context = format_weather_for_context(weather_data, forecast_data)

    # Date actuelle pour le contexte
    current_date = datetime.now().strftime("%d/%m/%Y")
    current_datetime = datetime.now().strftime("%d/%m/%Y à %H:%M")

    system_message = {
        "role": "system",
        "content": f"""Tu es SunuPecheNet, un assistant expert en pêche au Sénégal avec accès à une base de données réelle, aux données météo en temps réel ET aux horaires de marées.

DATE ET HEURE ACTUELLES: {current_datetime}

INSTRUCTIONS CRITIQUES - GESTION INTELLIGENTE DES DATES:

1. NOUS SOMMES LE {current_date} - Adapte tes réponses selon le contexte temporel de la question

2. QUESTIONS SUR LE FUTUR ("demain", "cette semaine", "prochains jours"):
   - Analyse UNIQUEMENT les dates futures (>= {current_date})
   - Utilise les données météo en temps réel
   - Si pas de données futures dans la base CSV, dis-le clairement et base-toi sur la météo actuelle

3. QUESTIONS SUR LE PASSE ("hier", "la semaine dernière", "le 16 novembre"):
   - Réponds avec les données historiques disponibles dans la base
   - Indique clairement qu'il s'agit de données passées
   - Exemple: "Le 16 novembre 2024, il y avait une alerte de surpêche à Dakar..."

4. QUESTIONS SANS CONTEXTE TEMPOREL ("quel jour est risqué cette semaine?"):
   - Par défaut, interprète comme FUTUR (à partir d'aujourd'hui)
   - Si données futures manquantes, explique et propose d'analyser les tendances historiques

5. Tu as DEJA les données météo ET marées en temps réel - UTILISE-LES pour les prévisions
6. HEURE ACTUELLE: Vérifie toujours l'heure actuelle dans les données de marée
7. RECOMMANDATIONS TEMPORELLES:
   - Si l'utilisateur demande "quand aller pêcher" à 22h, ne recommande PAS 15h (c'est passé!)
   - Compare TOUJOURS l'heure actuelle avec les horaires de marée
   - Ne propose QUE des créneaux FUTURS (après l'heure actuelle)
   - Si tous les créneaux d'aujourd'hui sont passés, propose DEMAIN
   - EXEMPLE: Si on est à 22h et haute mer était à 17h50 -> propose les horaires de DEMAIN (06h15)
8. REPONDS DIRECTEMENT selon le contexte temporel détecté

8. Analyse météo:
   - Vent favorable si < 15 m/s (sinon dangereux)
   - Visibilité bonne si > 5 km
   - Température eau idéale: 20-25°C

9. FILTRAGE INTELLIGENT DES DONNEES CSV:
   - Détecte le contexte temporel de la question (passé/présent/futur)
   - Pour questions FUTURES: ne montre que dates >= {current_date}
   - Pour questions PASSEES: montre les données historiques concernées
   - Pour analyses de tendances: utilise toutes les données disponibles
   - EXEMPLE 1: "Quel jour risqué cette semaine?" -> Analyse du {current_date} à +7 jours
   - EXEMPLE 2: "Que s'est-il passé le 16 novembre?" -> Montre les données du 16/11/2024
   - EXEMPLE 3: "Quelles sont les tendances de surpêche?" -> Analyse toutes les données historiques

10. REGLES DES MAREES (TRES IMPORTANT - EXPLIQUE TOUJOURS):
   MEILLEURS MOMENTS pour pêcher:
      - 2h AVANT marée haute (marée montante = eau qui monte = nourriture + oxygène = poissons en chasse)
      - 1h APRES marée haute (début descente = encore actifs)
      - Pendant toute la MAREE MONTANTE (flux = mouvement = poissons actifs)
   PIRES MOMENTS (NE PAS pêcher):
      - Marée haute STATIONNAIRE (étale = eau immobile = poissons se reposent)
      - Marée basse STATIONNAIRE (étale = pas de mouvement = poissons inactifs)
      - Quand l'eau ne bouge pas = pas de nourriture en mouvement = poissons dorment

   TOUJOURS EXPLIQUER:
      - Pourquoi ce moment est bon/mauvais
      - Le mouvement de l'eau (montante/descendante/stationnaire)
      - Le comportement des poissons à ce moment
      - Calculer les créneaux précis (ex: si haute mer à 18h35, alors pêcher 16h35-18h35)

11. Donne un verdict CLAIR avec CRENEAUX HORAIRES précis
12. Pour les espèces, prix, captures: consulte les données CSV selon le contexte temporel

IMPORTANT - GESTION CONTEXTUELLE DES DATES ET HEURES:
- Aujourd'hui = {current_date}
- Heure actuelle = {current_datetime}
- VERIFIE TOUJOURS l'heure actuelle avant de recommander un créneau de pêche
- Ne recommande JAMAIS un créneau passé (ex: si on est à 22h, ne dis pas "pêche à 15h")
- Si question "quand aller pêcher" et on est tard le soir -> propose les créneaux de DEMAIN
- Détecte les mots-clés temporels: "demain", "hier", "cette semaine", "la semaine dernière", dates spécifiques
- Questions par défaut sur "cette semaine" ou "prochains jours" = FUTUR (du {current_date} au {(datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y")})
- Questions avec dates passées explicites = réponds avec données historiques
- Sois CLAIR sur le contexte temporel dans ta réponse: "D'après les données du 16 novembre 2024..." ou "Pour les prochains jours..."
- EXEMPLE CRITIQUE: Si on est le 26/11 à 22h et tu vois marée haute à 17h50 aujourd'hui -> c'est PASSE, propose 06h15 DEMAIN

{weather_context}

{context}

RAPPEL IMPORTANT:
- Tu DOIS TOUJOURS expliquer POURQUOI un moment est bon ou mauvais
- Mentionne le mouvement de l'eau (montante/descendante/stationnaire)
- Explique le comportement des poissons selon la marée
- Donne des créneaux horaires PRECIS calculés à partir des horaires de marée

Tu as DEJA toutes les données (météo + marées) - réponds IMMEDIATEMENT sans demander d'infos supplémentaires!"""
    }

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[system_message] + messages,
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erreur lors de la génération de la réponse: {e}"

# Initialiser l'état de session
if "messages" not in st.session_state:
    st.session_state.messages = []

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.csv_data = {}
    st.session_state.context = ""

# ========== SIDEBAR ==========
with st.sidebar:
    # Logo dans la sidebar
    logo_path = Path("pages/image/logo_sunupechenet.png")
    if not logo_path.exists():
        logo_path = Path("image/logo_sunupechenet.png")
    if not logo_path.exists():
        logo_path = Path("logo_sunupechenet.png")

    if logo_path.exists():
        st.image(str(logo_path), width=100)

    # Infos plateforme
    st.write("### SunuPecheNet")
    st.write("*Assistant intelligent pour la pêche*")
    st.divider()

    # Statut API
    api_key = os.getenv("OPENAI_API_KEY")
    owm_key = os.getenv("OWM_API_KEY")

    if api_key:
        st.success("IA activée")
    else:
        st.error("Clé OpenAI manquante")

    if owm_key:
        st.success("Météo activée")
    else:
        st.error("Clé OpenWeatherMap manquante")

    st.divider()

    # Actions
    st.write("### Actions")

    if st.button("Effacer l'historique"):
        st.session_state.messages = []
        st.success("Historique effacé")
        st.rerun()

# ========== CHARGEMENT DES DONNÉES ==========
if not st.session_state.data_loaded:
    with st.spinner("Chargement de la base de données..."):
        csv_data = load_csv_data()
        st.session_state.csv_data = csv_data
        if st.session_state.csv_data:
            st.session_state.context = create_context_from_data(st.session_state.csv_data)
            st.session_state.data_loaded = True
        else:
            st.warning("Aucune donnée CSV trouvée")

# ========== CHAT PRINCIPAL ==========
st.title("SUNU PECHENET")
st.subheader("Posez vos questions sur la pêche et la météo")

# Afficher l'historique
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input utilisateur
if prompt := st.chat_input("Posez votre question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyse en cours..."):
            response = get_chatbot_response(
                st.session_state.messages,
                st.session_state.context,
                prompt
            )
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})