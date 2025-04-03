import firebase_admin
from firebase_admin import credentials, db
import time
import threading

# Path to the Firebase credentials JSON
cred_path = '/home/pi/final_testing/fire_key.json'

# Initialize the Firebase app
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://finaltesting-bcb9e-default-rtdb.firebaseio.com/'
})

# Function to continuously fetch Flags every 3 seconds
def read_flags_loop():
    while True:
        try:
            ref = db.reference('Flags')
            flags = ref.get()

            if flags:
                bottom_light = flags.get('bottom_light', 'N/A')
                bottom_water = flags.get('bottom_water', 'N/A')
                top_light = flags.get('top_light', 'N/A')
                top_water = flags.get('top_water', 'N/A')

                print("=== Current Flags ===")
                print(f"Bottom Light : {bottom_light}")
                print(f"Bottom Water : {bottom_water}")
                print(f"Top Light    : {top_light}")
                print(f"Top Water    : {top_water}")
                print("=====================\n")
            else:
                print("Flags not found in database.\n")

            time.sleep(3)
        except Exception as e:
            print(f"Error reading from Firebase: {e}")
            time.sleep(3)

# Start the Firebase reading thread
firebase_thread = threading.Thread(target=read_flags_loop, daemon=True)
firebase_thread.start()

# Main loop does nothing, just keeps the script alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Program terminated by user.")
