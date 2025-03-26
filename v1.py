import time
import gpiod
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# Define GPIO pins
LED_PIN_17 = 17  # GPIO 17
LED_PIN_27 = 27  # GPIO 27
LED_PIN_22 = 22  # GPIO 22
LED_PIN_10 = 10  # GPIO 10
LED_PIN_9 = 9    # GPIO 9

'''
distance sensor - non resistor pin gpio 23, w/resistor = 27
top_light = 22
bottom_light = 17
top_water = 13
bottom_water = 19
pump = 0

heater = 10
'''

# Use the correct GPIO chip (Check with ls /dev/gpiochip*)
chip = gpiod.Chip('gpiochip0')  # Change this if needed

# Get the GPIO lines for LEDs
led_line_17 = chip.get_line(LED_PIN_17)
led_line_27 = chip.get_line(LED_PIN_27)
led_line_22 = chip.get_line(LED_PIN_22)
led_line_10 = chip.get_line(LED_PIN_10)
led_line_9 = chip.get_line(LED_PIN_9)

# Request exclusive access to the lines and configure them as outputs
led_line_17.request(consumer="LED_17", type=gpiod.LINE_REQ_DIR_OUT)
led_line_27.request(consumer="LED_27", type=gpiod.LINE_REQ_DIR_OUT)
led_line_22.request(consumer="LED_22", type=gpiod.LINE_REQ_DIR_OUT)
led_line_10.request(consumer="LED_10", type=gpiod.LINE_REQ_DIR_OUT)
led_line_9.request(consumer="LED_9", type=gpiod.LINE_REQ_DIR_OUT)

# Initialize Firebase
cred = credentials.Certificate("/home/pi/project_code/firebase_key.json")  # Replace with your actual credentials file
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://simple-sprouts-database-default-rtdb.firebaseio.com/'
})

# Reference to the database location
ref = db.reference("flags_test")
data = ref.get()

# Function to track time with ON/OFF cycles for Timer One
def run_timer_bottom_light():

    total_on = 0
    total_off = 0

    while True:

        bottom_initialized = data.get("bottom_initialized", False)
        bottom_mode = data.get("bottom_mode", "manual")

        if bottom_initialized == True:
            if bottom_mode == "scheduling":
                bottom_mode_light_edit = data.get("bottom_mode_light_edit", False)
                
                if bottom_mode_light_edit == True:

                    bottom_light_ref_off_hrs = data.get("bottom_light_ref_off_hrs", 0)
                    bottom_light_ref_on_hrs = data.get("bottom_light_ref_on_hrs", 0)
                    bottom_light_ref_off_mins = data.get("bottom_light_ref_off_mins", 0)
                    bottom_light_ref_on_mins = data.get("bottom_light_ref_on_mins", 0)

                    total_on = (bottom_light_ref_on_hrs*1) + (bottom_light_ref_on_mins*1)
                    total_off = (bottom_light_ref_off_hrs*1) + (bottom_light_ref_off_mins*1)

                    counter = total_on  # Start counter
                    ref.update({"bottom_mode_light_edit": False})

                while counter > 0:
                    print("Bottom Light: ON")
                    led_line_17.set_value(1)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    #ref.update({"bottom_light_tts_hrs": counter//3600})
                    #ref.update({"bottom_light_tts_mins": counter % 3600})
                    ref.update({"bottom_light_enabled": True})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_off

                while counter > 0:
                    print("Bottom light: OFF")
                    led_line_17.set_value(0)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"bottom_light_enabled": False})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_on

def run_timer_bottom_water():
    
    total_on = 0
    total_off = 0

    while True:
        bottom_initialized = data.get("bottom_initialized", False)
        bottom_mode = data.get("bottom_mode", "manual")

        if bottom_initialized == True:
            if bottom_mode == "scheduling":
                bottom_mode_water_edit = data.get("bottom_mode_water_edit", False)
                
                if bottom_mode_water_edit == True:
                    bottom_water_ref_days = data.get("bottom_water_ref_days", 0)
                    bottom_water_ref_hrs = data.get("bottom_water_ref_hrs", 0)
                    bottom_water_ref_mins = data.get("bottom_water_ref_mins", 0)
                    bottom_water_amount = data.get("bottom_water_amount", 0)

                    total_on = bottom_water_amount
                    total_off = (bottom_water_ref_days*1) + (bottom_water_ref_hrs*1) + (bottom_water_ref_mins*1)
                    counter = total_off  # Start counter
                    ref.update({"bottom_mode_water_edit": False})

                while counter > 0:
                    print("Bottom Water: OFF")
                    led_line_22.set_value(0)
                    led_line_9.set_value(0)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"bottom_water_enabled": False})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_on

                while counter > 0:
                    print("Bottom Water: ON")
                    led_line_22.set_value(1)
                    led_line_9.set_value(1)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"bottom_water_enabled": True})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_off

def run_timer_top_light():
   
    total_on = 0
    total_off = 0

    while True:
        top_initialized = data.get("top_initialized", False)
        top_mode = data.get("top_mode", "manual")

        if top_initialized == True:
            if top_mode == "scheduling":
                top_mode_light_edit = data.get("top_mode_light_edit", False)

                if top_mode_light_edit == True:
                    top_light_ref_off_hrs = data.get("top_light_ref_off_hrs", 0)
                    top_light_ref_on_hrs = data.get("top_light_ref_on_hrs", 0)
                    top_light_ref_off_mins = data.get("top_light_ref_off_mins", 0)
                    top_light_ref_on_mins = data.get("top_light_ref_on_mins", 0)

                    total_on = (top_light_ref_on_hrs*1) + (top_light_ref_on_mins*1)
                    total_off = (top_light_ref_off_hrs*1) + (top_light_ref_off_mins*1)
                    counter = total_on  # Start counter
                    ref.update({"top_mode_light_edit": False})

                while counter > 0:
                    print("Top Light: ON")
                    led_line_27.set_value(1)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"top_light_enabled": True})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_off

                while counter > 0:
                    print("Top light: OFF")
                    led_line_27.set_value(0)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"top_light_enabled": False})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_on

def run_timer_top_water():
    
    total_on = 0
    total_off = 0
    while True:
        top_initialized = data.get("top_initialized", False)
        top_mode = data.get("top_mode", "manual")

        if top_initialized == True:
            if top_mode == "scheduling":
                top_mode_water_edit = data.get("top_mode_water_edit", False)

                if top_mode_water_edit == True:
                    top_water_ref_days = data.get("top_water_ref_days", 0)
                    top_water_ref_hrs = data.get("top_water_ref_hrs", 0)
                    top_water_ref_mins = data.get("top_water_ref_mins", 0)
                    top_water_amount = data.get("top_water_amount", 0)

                    total_on = top_water_amount
                    total_off = (top_water_ref_days*1) + (top_water_ref_hrs*1) + (top_water_ref_mins*1)
                    counter = total_off  # Start counter
                    ref.update({"top_mode_water_edit": False})

                while counter > 0:
                    print("Top Water: OFF")
                    led_line_10.set_value(0)
                    led_line_9.set_value(0)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"top_water_enabled": False})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_on

                while counter > 0:
                    print("Top Water: ON")
                    led_line_10.set_value(1)
                    led_line_9.set_value(1)
                    time.sleep(5)  # Wait for 5 seconds
                    counter -= 5    # Increment counter by 5
                    ref.update({"top_water_enabled": True})
                    #print(f"Timer One Counter: {counter} seconds")
                counter = total_off


def manual_mode():
   
    level_under_test = data.get("level_under_test", 0)
    print(level_under_test)

    if level_under_test == 1:
        bottom_initialized = data.get("bottom_initialized", False)
        print(bottom_initialized)

        if bottom_initialized == True:
            bottom_mode = data.get("bottom_mode", "manual")
            print(bottom_mode)

            if bottom_mode == "manual":
                bottom_man_light = data.get("bottom_man_light", False)
                bottom_man_water = data.get("bottom_man_water", False)
                print("3")

                if bottom_man_light == True:
                    print("4")
                    led_line_17.set_value(1)
                else: 
                    led_line_17.set_value(0)

                if bottom_man_water == True:
                    led_line_22.set_value(1)
                    led_line_9.set_value(1)
                else:
                    led_line_22.set_value(0)
                    led_line_9.set_value(0)
                    
    if level_under_test == 2:
        top_initialized = data.get("top_initialized", False)

        if top_initialized == True:
            top_mode = data.get("top_mode", "manual")

            if top_mode == "manual":
                top_man_light = data.get("top_man_light", False)
                top_man_water = data.get("top_man_water", False)

                if top_man_light == True:
                    led_line_27.set_value(1)
                else: 
                    led_line_27.set_value(0)

                if top_man_water == True:
                    led_line_10.set_value(1)
                    led_line_9.set_value(1)
                else:
                    led_line_10.set_value(0)
                    led_line_9.set_value(0)
    
    time.sleep(2)

            
# Start fetch_flags() in a separate thread
#firebase_thread = threading.Thread(target=fetch_flags, daemon=True)
#firebase_thread.start()

# Create threads for each timer
timer_one_thread = threading.Thread(target=run_timer_bottom_light, daemon=True)
timer_two_thread = threading.Thread(target=run_timer_bottom_water, daemon=True)
timer_three_thread = threading.Thread(target=run_timer_top_light, daemon=True)
timer_four_thread = threading.Thread(target=run_timer_top_water, daemon=True)
#timer_five_thread = threading.Thread(target=manual_mode, daemon=True)

# Start both threads
timer_one_thread.start()
timer_two_thread.start()
timer_three_thread.start()
timer_four_thread.start()
#timer_five_thread.start()

# Keep the main program running
while True:
    manual_mode()
   # time.sleep(1)
