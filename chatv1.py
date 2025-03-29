import time
import gpiod
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

def run_timer_bottom_light():
    total_on = 0
    total_off = 0

    while True:
        data = ref.get()
        bottom_initialized = data.get("bottom_initialized", False)
        bottom_mode = data.get("bottom_mode", "manual")

        if bottom_initialized:
            if bottom_mode == "scheduling":
                bottom_mode_light_edit = data.get("bottom_mode_light_edit", False)
                if bottom_mode_light_edit:
                    bottom_light_ref_off_hrs = data.get("bottom_light_ref_off_hrs", 0)
                    bottom_light_ref_on_hrs = data.get("bottom_light_ref_on_hrs", 0)
                    bottom_light_ref_off_mins = data.get("bottom_light_ref_off_mins", 0)
                    bottom_light_ref_on_mins = data.get("bottom_light_ref_on_mins", 0)

                    total_on = (bottom_light_ref_on_hrs) + (bottom_light_ref_on_mins)
                    total_off = (bottom_light_ref_off_hrs) + (bottom_light_ref_off_mins)
                    counter = total_on  # Start counter
                    ref.update({"bottom_mode_light_edit": False})

                # ON cycle with polling inside the loop
                while counter > 0:
                    data = ref.get()
                    if data.get("bottom_mode", "manual") != "scheduling":
                        print("Bottom mode changed; breaking out of ON scheduling loop")
                        break
                    print("Bottom Light: ON")
                    led_line_17.set_value(1)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"bottom_light_enabled": True})

                # OFF cycle with polling
                counter = total_off
                while counter > 0:
                    data = ref.get()
                    if data.get("bottom_mode", "manual") != "scheduling":
                        print("Bottom mode changed; breaking out of OFF scheduling loop")
                        break
                    print("Bottom Light: OFF")
                    led_line_17.set_value(0)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"bottom_light_enabled": False})
                # Reset counter for next cycle if needed
                counter = total_on
        time.sleep(1)  # Delay before next outer loop iteration

def run_timer_bottom_water():
    total_on = 0
    total_off = 0

    while True:
        data = ref.get()
        bottom_initialized = data.get("bottom_initialized", False)
        bottom_mode = data.get("bottom_mode", "manual")

        if bottom_initialized:
            if bottom_mode == "scheduling":
                bottom_mode_water_edit = data.get("bottom_mode_water_edit", False)
                if bottom_mode_water_edit:
                    bottom_water_ref_days = data.get("bottom_water_ref_days", 0)
                    bottom_water_ref_hrs = data.get("bottom_water_ref_hrs", 0)
                    bottom_water_ref_mins = data.get("bottom_water_ref_mins", 0)
                    bottom_water_amount = data.get("bottom_water_amount", 0)

                    total_on = bottom_water_amount
                    total_off = (bottom_water_ref_days) + (bottom_water_ref_hrs) + (bottom_water_ref_mins)
                    counter = total_off  # Start counter
                    ref.update({"bottom_mode_water_edit": False})

                # OFF cycle with polling
                while counter > 0:
                    data = ref.get()
                    if data.get("bottom_mode", "manual") != "scheduling":
                        print("Bottom mode changed; breaking out of bottom water OFF loop")
                        break
                    print("Bottom Water: OFF")
                    led_line_22.set_value(0)
                    led_line_9.set_value(0)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"bottom_water_enabled": False})
                # ON cycle with polling
                counter = total_on
                while counter > 0:
                    data = ref.get()
                    if data.get("bottom_mode", "manual") != "scheduling":
                        print("Bottom mode changed; breaking out of bottom water ON loop")
                        break
                    print("Bottom Water: ON")
                    led_line_22.set_value(1)
                    led_line_9.set_value(1)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"bottom_water_enabled": True})
                # Reset counter for next cycle
                counter = total_off
        time.sleep(1)

def run_timer_top_light():
    total_on = 0
    total_off = 0

    while True:
        data = ref.get()
        top_initialized = data.get("top_initialized", False)
        top_mode = data.get("top_mode", "manual")

        if top_initialized:
            if top_mode == "scheduling":
                top_mode_light_edit = data.get("top_mode_light_edit", False)
                if top_mode_light_edit:
                    top_light_ref_off_hrs = data.get("top_light_ref_off_hrs", 0)
                    top_light_ref_on_hrs = data.get("top_light_ref_on_hrs", 0)
                    top_light_ref_off_mins = data.get("top_light_ref_off_mins", 0)
                    top_light_ref_on_mins = data.get("top_light_ref_on_mins", 0)

                    total_on = (top_light_ref_on_hrs) + (top_light_ref_on_mins)
                    total_off = (top_light_ref_off_hrs) + (top_light_ref_off_mins)
                    counter = total_on  # Start counter
                    ref.update({"top_mode_light_edit": False})

                # ON cycle with polling
                while counter > 0:
                    data = ref.get()
                    if data.get("top_mode", "manual") != "scheduling":
                        print("Top mode changed; breaking out of top light ON loop")
                        break
                    print("Top Light: ON")
                    led_line_27.set_value(1)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"top_light_enabled": True})
                # OFF cycle with polling
                counter = total_off
                while counter > 0:
                    data = ref.get()
                    if data.get("top_mode", "manual") != "scheduling":
                        print("Top mode changed; breaking out of top light OFF loop")
                        break
                    print("Top Light: OFF")
                    led_line_27.set_value(0)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"top_light_enabled": False})
                # Reset counter for next cycle
                counter = total_on
        time.sleep(1)

def run_timer_top_water():
    total_on = 0
    total_off = 0

    while True:
        data = ref.get()
        top_initialized = data.get("top_initialized", False)
        top_mode = data.get("top_mode", "manual")

        if top_initialized:
            if top_mode == "scheduling":
                top_mode_water_edit = data.get("top_mode_water_edit", False)
                if top_mode_water_edit:
                    top_water_ref_days = data.get("top_water_ref_days", 0)
                    top_water_ref_hrs = data.get("top_water_ref_hrs", 0)
                    top_water_ref_mins = data.get("top_water_ref_mins", 0)
                    top_water_amount = data.get("top_water_amount", 0)

                    total_on = top_water_amount
                    total_off = (top_water_ref_days) + (top_water_ref_hrs) + (top_water_ref_mins)
                    counter = total_off  # Start counter
                    ref.update({"top_mode_water_edit": False})

                # OFF cycle with polling
                while counter > 0:
                    data = ref.get()
                    if data.get("top_mode", "manual") != "scheduling":
                        print("Top mode changed; breaking out of top water OFF loop")
                        break
                    print("Top Water: OFF")
                    led_line_10.set_value(0)
                    led_line_9.set_value(0)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"top_water_enabled": False})
                # ON cycle with polling
                counter = total_on
                while counter > 0:
                    data = ref.get()
                    if data.get("top_mode", "manual") != "scheduling":
                        print("Top mode changed; breaking out of top water ON loop")
                        break
                    print("Top Water: ON")
                    led_line_10.set_value(1)
                    led_line_9.set_value(1)
                    time.sleep(5)
                    counter -= 5
                    ref.update({"top_water_enabled": True})
                # Reset counter for next cycle
                counter = total_off
        time.sleep(1)

def manual_mode():
    while True:
        data = ref.get()
        level_under_test = data.get("level_under_test", 0)
        print("Level under test:", level_under_test)

        if level_under_test == 1:
            bottom_initialized = data.get("bottom_initialized", False)
            print("Bottom initialized:", bottom_initialized)
            if bottom_initialized:
                bottom_mode = data.get("bottom_mode", "manual")
                print("Bottom mode:", bottom_mode)
                if bottom_mode == "manual":
                    bottom_man_light = data.get("bottom_man_light", False)
                    bottom_man_water = data.get("bottom_man_water", False)
                    print("Bottom manual light:", bottom_man_light, "Bottom manual water:", bottom_man_water)
                    if bottom_man_light:
                        led_line_17.set_value(1)
                    else:
                        led_line_17.set_value(0)
                    if bottom_man_water:
                        led_line_22.set_value(1)
                        led_line_9.set_value(1)
                    else:
                        led_line_22.set_value(0)
                        led_line_9.set_value(0)

        if level_under_test == 2:
            top_initialized = data.get("top_initialized", False)
            print("Top initialized:", top_initialized)
            if top_initialized:
                top_mode = data.get("top_mode", "manual")
                print("Top mode:", top_mode)
                if top_mode == "manual":
                    top_man_light = data.get("top_man_light", False)
                    top_man_water = data.get("top_man_water", False)
                    print("Top manual light:", top_man_light, "Top manual water:", top_man_water)
                    if top_man_light:
                        led_line_27.set_value(1)
                    else:
                        led_line_27.set_value(0)
                    if top_man_water:
                        led_line_10.set_value(1)
                        led_line_9.set_value(1)
                    else:
                        led_line_10.set_value(0)
                        led_line_9.set_value(0)
        time.sleep(2)

# Create threads for each timer and manual mode
timer_one_thread = threading.Thread(target=run_timer_bottom_light, daemon=True)
timer_two_thread = threading.Thread(target=run_timer_bottom_water, daemon=True)
timer_three_thread = threading.Thread(target=run_timer_top_light, daemon=True)
timer_four_thread = threading.Thread(target=run_timer_top_water, daemon=True)
timer_five_thread = threading.Thread(target=manual_mode, daemon=True)

# Start all threads
timer_one_thread.start()
timer_two_thread.start()
timer_three_thread.start()
timer_four_thread.start()
timer_five_thread.start()

# Keep the main program running
while True:
    time.sleep(1)
