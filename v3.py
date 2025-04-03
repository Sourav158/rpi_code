import time
import gpiod
import firebase_admin
from firebase_admin import credentials, db

# Define GPIO pins
LED_PIN_17 = 17  # bottom light
LED_PIN_27 = 27  # top light
LED_PIN_22 = 22  # bottom water
LED_PIN_10 = 10  # top water
LED_PIN_9  = 9   # shared water control

# Initialize GPIO chip and lines
chip = gpiod.Chip('gpiochip0')
led_line_17 = chip.get_line(LED_PIN_17)
led_line_27 = chip.get_line(LED_PIN_27)
led_line_22 = chip.get_line(LED_PIN_22)
led_line_10 = chip.get_line(LED_PIN_10)
led_line_9  = chip.get_line(LED_PIN_9)

# Request lines for output
led_line_17.request(consumer="LED_17", type=gpiod.LINE_REQ_DIR_OUT)
led_line_27.request(consumer="LED_27", type=gpiod.LINE_REQ_DIR_OUT)
led_line_22.request(consumer="LED_22", type=gpiod.LINE_REQ_DIR_OUT)
led_line_10.request(consumer="LED_10", type=gpiod.LINE_REQ_DIR_OUT)
led_line_9.request(consumer="LED_9", type=gpiod.LINE_REQ_DIR_OUT)

# Initialize Firebase
cred = credentials.Certificate("/home/pi/project_code/firebase_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://simple-sprouts-database-default-rtdb.firebaseio.com/'
})
ref = db.reference("flags_test")

# Dictionary holding state for each component
components = {
    "bottom_light": {
        "gpio": led_line_17,
        "state": False,
        "on_duration": 0,
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "bottom_initialized",
        "mode_key": "bottom_mode",
        "edit_flag": "bottom_mode_light_edit"
    },
    "bottom_water": {
        "gpio": (led_line_22, led_line_9),
        "state": False,
        "on_duration": 0,
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "bottom_initialized",
        "mode_key": "bottom_mode",
        "edit_flag": "bottom_mode_water_edit"
    },
    "top_light": {
        "gpio": led_line_27,
        "state": False,
        "on_duration": 0,
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "top_initialized",
        "mode_key": "top_mode",
        "edit_flag": "top_mode_light_edit"
    },
    "top_water": {
        "gpio": (led_line_10, led_line_9),
        "state": False,
        "on_duration": 0,
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "top_initialized",
        "mode_key": "top_mode",
        "edit_flag": "top_mode_water_edit"
    }
}

def update_schedule(comp_name, data):
    """Update on/off durations from Firebase for the given component."""
    comp = components[comp_name]
    if comp_name in ["bottom_light", "top_light"]:
        # Compute on and off durations in seconds
        total_on = data.get(f"{comp_name}_ref_on_hrs", 0) * 3600 + data.get(f"{comp_name}_ref_on_mins", 0) * 60
        total_off = data.get(f"{comp_name}_ref_off_hrs", 0) * 3600 + data.get(f"{comp_name}_ref_off_mins", 0) * 60
        comp["on_duration"] = total_on
        comp["off_duration"] = total_off
        # Reset the next toggle to start immediately
        comp["next_toggle"] = time.monotonic()
    elif comp_name in ["bottom_water", "top_water"]:
        # For water: on_duration from amount; off_duration from days, hrs, and mins
        amount = data.get(f"{comp_name}_amount", 0)
        total_off = (data.get(f"{comp_name}_ref_days", 0) * 86400 +
                     data.get(f"{comp_name}_ref_hrs", 0) * 3600 +
                     data.get(f"{comp_name}_ref_mins", 0) * 60)
        comp["on_duration"] = amount
        comp["off_duration"] = total_off
        comp["next_toggle"] = time.monotonic()

def set_gpio(comp, value):
    """Set GPIO output; supports a tuple of lines for multi-pin control."""
    if isinstance(comp["gpio"], tuple):
        for gpio in comp["gpio"]:
            gpio.set_value(1 if value else 0)
    else:
        comp["gpio"].set_value(1 if value else 0)

def handle_manual_mode(data):
    """Control manual mode for bottom and top levels based on Firebase flags."""
    level_under_test = data.get("level_under_test", 0)
    if level_under_test == 1:
        if data.get("bottom_initialized", False):
            if data.get("bottom_mode", "manual") == "manual":
                bottom_man_light = data.get("bottom_man_light", False)
                bottom_man_water = data.get("bottom_man_water", False)
                led_line_17.set_value(1 if bottom_man_light else 0)
                # For water, update both relevant GPIOs
                led_line_22.set_value(1 if bottom_man_water else 0)
                led_line_9.set_value(1 if bottom_man_water else 0)
    elif level_under_test == 2:
        if data.get("top_initialized", False):
            if data.get("top_mode", "manual") == "manual":
                top_man_light = data.get("top_man_light", False)
                top_man_water = data.get("top_man_water", False)
                led_line_27.set_value(1 if top_man_light else 0)
                led_line_10.set_value(1 if top_man_water else 0)
                led_line_9.set_value(1 if top_man_water else 0)

# Main event loop: Poll Firebase and update each component
while True:
    current_time = time.monotonic()
    data = ref.get()  # Fetch latest flags and scheduling values from Firebase

    # Process bottom light
    comp = components["bottom_light"]
    if data.get(comp["init_key"], False):
        mode = data.get(comp["mode_key"], "manual")
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("bottom_light", data)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                # Toggle the state
                comp["state"] = not comp["state"]
                set_gpio(comp, comp["state"])
                # Schedule next toggle based on current state
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
        # In manual mode, the manual_mode() function below handles it

    # Process top light
    comp = components["top_light"]
    if data.get(comp["init_key"], False):
        mode = data.get(comp["mode_key"], "manual")
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("top_light", data)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_gpio(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]

    # Process bottom water
    comp = components["bottom_water"]
    if data.get(comp["init_key"], False):
        mode = data.get(comp["mode_key"], "manual")
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("bottom_water", data)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_gpio(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]

    # Process top water
    comp = components["top_water"]
    if data.get(comp["init_key"], False):
        mode = data.get(comp["mode_key"], "manual")
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("top_water", data)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_gpio(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]

    # Run manual mode handling for both levels (if mode is manual)
    handle_manual_mode(data)

    time.sleep(0.5)  # Short sleep to avoid busy waiting
