import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, date
import pytz
import os
import json
import tempfile

# === Initialisation Firebase ===
firebase_key_str = os.environ["FIREBASE_KEY_JSON"]
firebase_key = json.loads(firebase_key_str)

# Créer un fichier temporaire de façon sécurisée
with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
    json.dump(firebase_key, temp_file)
    temp_file_path = temp_file.name

try:
    cred = credentials.Certificate(temp_file_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # === Paramètres météo ===
    API_KEY = os.environ["OPENWEATHER_API_KEY"]
    VILLE = os.environ["VILLE_METEO"]
    URL = f"http://api.openweathermap.org/data/2.5/forecast?q={VILLE}&appid={API_KEY}&units=metric&lang=fr"

    # Fuseau horaire local (Cotonou)
    tz_local = pytz.timezone("Africa/Porto-Novo")
    date_ajd = datetime.now(tz_local).date()
    collection_meteo = db.collection("meteo")

    response = requests.get(URL)
    response.raise_for_status()
    data = response.json()

    previsions_jour = []

    for forecast in data["list"]:
        dt_utc = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
        dt_utc = pytz.utc.localize(dt_utc)
        dt_local = dt_utc.astimezone(tz_local)

        # On garde uniquement les prévisions du jour courant
        if dt_local.date() == date_ajd:
            prevision = {
                "dt_txt": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
                "weather_description": forecast["weather"][0]["description"],
                "pop": forecast.get("pop", 0),
                "rain": forecast.get("rain", {}).get("3h", 0.0)
            }
            previsions_jour.append(prevision)

    doc_id = date_ajd.strftime("%Y-%m-%d")
    if date_ajd == date.today():
        # Suppression des anciennes prévisions
        docs = collection_meteo.stream()
        for doc in docs:
            if doc.id != date_ajd.strftime("%Y-%m-%d"):
                doc.reference.delete()
        collection_meteo.document(doc_id).set({
            "ville": VILLE.split(',')[0],
            "previsions": previsions_jour
        })
        print(f"{len(previsions_jour)} prévisions sauvegardées pour le {doc_id}")
    else:
        print("Aucune prévision sauvegardée car la date n'est pas celle d'aujourd'hui.")

except Exception as e:
    print("Erreur :", e)

finally:
    # Suppression sécurisée du fichier temporaire
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
