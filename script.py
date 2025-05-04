import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pytz
import os
import json

# === Initialisation Firebase ===
firebase_key_str = os.environ["FIREBASE_KEY_JSON"]
firebase_key = json.loads(firebase_key_str)

with open("temp_firebase_key.json", "w") as f:
    json.dump(firebase_key, f)

cred = credentials.Certificate("temp_firebase_key.json")
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

try:
    response = requests.get(URL)
    response.raise_for_status()
    data = response.json()

    previsions_jour = []

    for forecast in data["list"]:
        dt_utc = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
        dt_utc = pytz.utc.localize(dt_utc)
        dt_local = dt_utc.astimezone(tz_local)

        if dt_local.date() == date_ajd:
            prevision = {
                "dt_txt": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
                "weather_description": forecast["weather"][0]["description"],
                "pop": forecast.get("pop", 0),
                "rain": forecast.get("rain", {}).get("3h", 0.0)
            }
            previsions_jour.append(prevision)

    doc_id = date_ajd.strftime("%Y-%m-%d")
    collection_meteo.document(doc_id).set({
        "ville": VILLE.split(',')[0],
        "previsions": previsions_jour
    })

    print(f"{len(previsions_jour)} prévisions sauvegardées pour le {doc_id}")

except Exception as e:
    print("Erreur :", e)