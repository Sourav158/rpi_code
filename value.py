import firebase_admin
from firebase_admin import credentials, db

# Path to your Firebase service account key JSON
cred_path = "/home/pi/final_testing/fire_key.json"

# Initialize Firebase app
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://finaltesting-bcb9e-default-rtdb.firebaseio.com/'
})

# Define Flags with updated default values
Flags = {
    "app_open": False,
    "level_under_test": 0,
    "bottom_initialized": False,
    "bottom_mode": "manual",
    "bottom_man_light": False,
    "bottom_man_water": False,
    "bottom_mode_light_edit": False,
    "bottom_mode_water_edit": False,
    "bottom_light_ref_off_hrs": 0,
    "bottom_light_ref_on_hrs": 0,
    "bottom_light_ref_off_mins": 0,
    "bottom_light_ref_on_mins": 0,
    "bottom_light_tts_hrs": 0,
    "bottom_light_tts_mins": 0,
    "bottom_water_ref_days": 0,
    "bottom_water_ref_hrs": 0,
    "bottom_water_ref_mins": 0,
    "bottom_water_ttw_days": 0,
    "bottom_water_ttw_hrs": 0,
    "bottom_water_ttw_min": 0,
    "top_initialized": False,
    "top_mode": "manual",
    "top_man_light": False,
    "top_man_water": False,
    "top_mode_light_edit": False,
    "top_mode_water_edit": False,
    "top_light_ref_off_hrs": 0,
    "top_light_ref_on_hrs": 0,
    "top_light_ref_off_mins": 0,
    "top_light_ref_on_mins": 0,
    "top_light_tts_hrs": 0,
    "top_light_tts_mins": 0,
    "top_water_ref_days": 0,
    "top_water_ref_hrs": 0,
    "top_water_ref_mins": 0,
    "top_water_ttw_days": 0,
    "top_water_ttw_hrs": 0,
    "top_water_ttw_min": 0,
    "bottom_light_enabled": False,
    "top_light_enabled": False,
    "bottom_water_enabled": False,
    "top_water_enabled": False,
    "top_water_amount": 0,
    "bottom_water_amount": 0
}

# Upload Flags data to Firebase
ref = db.reference("Flags")
ref.set(Flags)

print("Flags have been successfully set in Firebase.")
