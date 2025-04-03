import firebase_admin
from firebase_admin import credentials, db

# Replace this with the actual path to your Firebase service account key
cred_path = "/path/to/your/serviceAccountKey.json"

# Initialize Firebase
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://finaltesting-bcb9e-default-rtdb.firebaseio.com/'
})

# Create the Flags dictionary with default values
Flags = {
    "app_open": False,
    "level_under_test": 0,
    "bottom_initialized": False,
    "bottom_mode": "manual",
    "bottom_man_light": False,
    "bottom_man_water": False,
    "botton_mode_edited": False,
    "bottom_light_ref_off_hrs": 0,
    "bottom_light_ref_on_hrs": 0,
    "bottom_light_ref_off_mins": 0,
    "bottom_light_ref_on_mins": 0,
    "bottom_light_tts_hrs": 0,
    "bottom_light_tts_mins": 0,
    "bottom_water_ref_days": 0,
    "bottom_water_ref_hrs": 0,
    "bottom_water_ref_min": 0,
    "bottom_water_ttw_days": 0,
    "bottom_water_ttw_hrs": 0,
    "bottom_water_ttw_min": 0,
    "top_initialized": False,
    "top_mode": "manual",
    "top_man_light": False,
    "top_man_water": False,
    "top_mode_edited": False,
    "top_light_ref_off_hrs": 0,
    "top_light_ref_on_hrs": 0,
    "top_light_ref_off_mins": 0,
    "top_light_ref_on_mins": 0,
    "top_light_tts_hrs": 0,
    "top_light_tts_mins": 0,
    "top_water_ref_days": 0,
    "top_water_ref_hrs": 0,
    "top_water_ref_min": 0,
    "top_water_ttw_days": 0,
    "top_water_ttw_hrs": 0,
    "top_water_ttw_min": 0
}

# Push the Flags dictionary to Firebase under the "Flags" node
ref = db.reference("Flags")
ref.set(Flags)

print("Flags data successfully uploaded to Firebase.")
