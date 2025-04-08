import time
import gpiod
import firebase_admin
from firebase_admin import credentials, db
from gpiozero import DistanceSensor  # For ultrasonic sensor

# --- GPIO Pin Definitions ---
'''
LED_PIN_17 = 22  # bottom light
LED_PIN_27 = 17  # top light
LED_PIN_22 = 13  # bottom water valve
LED_PIN_10 = 19  # top water valve
LED_PIN_9  = 0   # shared water pump
LED_PIN_11 = 10  # heater
'''
LED_PIN_17 = 21  # bottom light
LED_PIN_27 = 20  # top light
LED_PIN_22 = 16  # bottom water valve
LED_PIN_10 = 12  # top water valve
LED_PIN_9  = 1   # shared water pump
LED_PIN_11 = 25  # heater

# --- Initialize GPIO Chip and Lines ---
chip = gpiod.Chip('gpiochip0')
led_line_17 = chip.get_line(LED_PIN_17)
led_line_27 = chip.get_line(LED_PIN_27)
led_line_22 = chip.get_line(LED_PIN_22)
led_line_10 = chip.get_line(LED_PIN_10)
led_line_9  = chip.get_line(LED_PIN_9)
heater_line = chip.get_line(LED_PIN_11)

# Request lines for output
led_line_17.request(consumer="LED_17", type=gpiod.LINE_REQ_DIR_OUT)
led_line_27.request(consumer="LED_27", type=gpiod.LINE_REQ_DIR_OUT)
led_line_22.request(consumer="LED_22", type=gpiod.LINE_REQ_DIR_OUT)
led_line_10.request(consumer="LED_10", type=gpiod.LINE_REQ_DIR_OUT)
led_line_9.request(consumer="LED_9", type=gpiod.LINE_REQ_DIR_OUT)
heater_line.request(consumer="HEATER", type=gpiod.LINE_REQ_DIR_OUT)

# --- Initialize Firebase ---
cred = credentials.Certificate("/home/pi/final_testing/sensor_firebase_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://simple-sprouts-database-default-rtdb.firebaseio.com/'
})
# "flags_test" holds mode and schedule info plus the TTS/TTW values.
ref = db.reference("flags_test")
# Separate reference for sensor readings.
sensor_readings_ref = db.reference("sensor_readings/latest")

# --- Initialize Ultrasonic Sensor ---
# (Trigger on GPIO 23, echo on GPIO 27; adjust as needed)
ultrasonic_sensor = DistanceSensor(echo=27, trigger=23, max_distance=4)
next_ultrasonic_sample = time.monotonic()

# --- Component State Dictionary ---
# For water, gpio is a tuple: (valve, pump) – valve control is independent.
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
    "bottom_water": {
        "gpio": (led_line_22, led_line_9),  # (valve, pump)
        "state": False,
        "on_duration": 0,   # water "amount" (on) stays as seconds
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "bottom_initialized",
        "mode_key": "bottom_mode",
        "edit_flag": "bottom_mode_water_edit"
    },
    "top_water": {
        "gpio": (led_line_10, led_line_9),  # (valve, pump)
        "state": False,
        "on_duration": 0,   # water "amount" (on) stays as seconds
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "top_initialized",
        "mode_key": "top_mode",
        "edit_flag": "top_mode_water_edit"
    }
}

# Heater state variable (independent of other modes)
heater_state = False

# --- Countdown Update Helper Functions ---

def update_tts_firebase(comp_name, current_time):
    """
    For lights (TTS):
    Calculate the remaining time until the next switch and update Firebase.
    The raw input hours and minutes are used to compute the original schedule,
    and the fraction of simulation time remaining is used to scale these back.
    """
    comp = components[comp_name]
    remaining = max(0, comp["next_toggle"] - current_time)
    if comp["state"]:
        total_sim = comp.get("total_on_duration", 1) or 1
        raw_hr = comp.get("raw_on_hrs", 0)
        raw_min = comp.get("raw_on_mins", 0)
    else:
        total_sim = comp.get("total_off_duration", 1) or 1
        raw_hr = comp.get("raw_off_hrs", 0)
        raw_min = comp.get("raw_off_mins", 0)
    fraction = remaining / total_sim if total_sim > 0 else 0
    # Original schedule in minutes:
    original_total_minutes = raw_hr * 60 + raw_min
    remaining_minutes = original_total_minutes * fraction
    display_hrs = int(remaining_minutes // 60)
    display_mins = int(remaining_minutes % 60)
    if comp_name == "bottom_light":
        ref.update({"bottom_light_tts_hrs": display_hrs, "bottom_light_tts_mins": display_mins})
    elif comp_name == "top_light":
        ref.update({"top_light_tts_hrs": display_hrs, "top_light_tts_mins": display_mins})

def update_ttw_firebase(comp_name, current_time):
    """
    For water (TTW):
    Calculate the remaining off time until the next water cycle and update Firebase.
    The raw inputs for days, hours, and minutes are used and scaled using the
    fraction of simulation off time that remains.
    """
    comp = components[comp_name]
    remaining = max(0, comp["next_toggle"] - current_time)
    total_sim = comp.get("total_off_duration", 1) or 1
    fraction = remaining / total_sim if total_sim > 0 else 0
    raw_days = comp.get("raw_ref_days", 0)
    raw_hrs  = comp.get("raw_ref_hrs", 0)
    raw_min  = comp.get("raw_ref_mins", 0)
    display_days = int(raw_days * fraction)
    display_hrs  = int(raw_hrs * fraction)
    display_mins = int(raw_min * fraction)
    if comp_name == "bottom_water":
        ref.update({"bottom_water_ttw_days": display_days, "bottom_water_ttw_hrs": display_hrs, "bottom_water_ttw_min": display_mins})
    elif comp_name == "top_water":
        ref.update({"top_water_ttw_days": display_days, "top_water_ttw_hrs": display_hrs, "top_water_ttw_min": display_mins})

# --- Schedule Update Functions ---

def update_schedule(comp_name, data, current_time):
    """
    Update schedule for 'scheduling' mode.
    For lights: use 1 hour = 3600 seconds and 1 minute = 60 seconds.
    For water off time: use 1 day = 86400 seconds, 1 hour = 3600 seconds, and 1 minute = 60 seconds.
    Raw input values are stored for use when displaying countdowns.
    """
    comp = components[comp_name]
    if comp_name in ["bottom_light", "top_light"]:
        # Store raw input values.
        comp["raw_on_hrs"]  = data.get(f"{comp_name}_ref_on_hrs", 0)
        comp["raw_on_mins"] = data.get(f"{comp_name}_ref_on_mins", 0)
        comp["raw_off_hrs"]  = data.get(f"{comp_name}_ref_off_hrs", 0)
        comp["raw_off_mins"] = data.get(f"{comp_name}_ref_off_mins", 0)
        # Compute the durations in seconds.
        total_on  = comp["raw_on_hrs"] * 3600 + comp["raw_on_mins"] * 60
        total_off = comp["raw_off_hrs"] * 3600 + comp["raw_off_mins"] * 60
        comp["on_duration"] = total_on
        comp["off_duration"] = total_off
        comp["total_on_duration"] = total_on
        comp["total_off_duration"] = total_off
    elif comp_name in ["bottom_water", "top_water"]:
        # For water, the "amount" (on time) is taken as seconds.
        amount = data.get(f"{comp_name}_amount", 0)
        comp["raw_ref_days"] = data.get(f"{comp_name}_ref_days", 0)
        comp["raw_ref_hrs"]  = data.get(f"{comp_name}_ref_hrs", 0)
        comp["raw_ref_mins"] = data.get(f"{comp_name}_ref_mins", 0)
        total_off = comp["raw_ref_days"] * 86400 + comp["raw_ref_hrs"] * 3600 + comp["raw_ref_mins"] * 60
        comp["on_duration"] = amount   # water "on" time remains as seconds.
        comp["off_duration"] = total_off
        comp["total_off_duration"] = total_off
    # If the scheduled time has already passed, update next_toggle accordingly.
    if comp["next_toggle"] < current_time:
        if comp["state"]:
            comp["next_toggle"] = current_time + comp["on_duration"]
        else:
            comp["next_toggle"] = current_time + comp["off_duration"]

def update_adaptive_schedule(comp_name, data, current_time):
    """
    Update schedule for adaptive mode (lights only).
    The conversion math is the same as for scheduling mode.
    """
    comp = components[comp_name]
    if comp_name == "bottom_light":
        comp["raw_on_hrs"]  = data.get("adp_bottom_light_on_hrs", 0)
        comp["raw_on_mins"] = data.get("adp_bottom_light_on_mins", 0)
        comp["raw_off_hrs"]  = data.get("adp_bottom_light_off_hrs", 0)
        comp["raw_off_mins"] = data.get("adp_bottom_light_off_mins", 0)
    elif comp_name == "top_light":
        comp["raw_on_hrs"]  = data.get("adp_top_light_on_hrs", 0)
        comp["raw_on_mins"] = data.get("adp_top_light_on_mins", 0)
        comp["raw_off_hrs"]  = data.get("adp_top_light_off_hrs", 0)
        comp["raw_off_mins"] = data.get("adp_top_light_off_mins", 0)
    total_on  = comp["raw_on_hrs"] * 3600 + comp["raw_on_mins"] * 60
    total_off = comp["raw_off_hrs"] * 3600 + comp["raw_off_mins"] * 60
    comp["on_duration"] = total_on
    comp["off_duration"] = total_off
    comp["total_on_duration"] = total_on
    comp["total_off_duration"] = total_off
    if comp["next_toggle"] < current_time:
        if comp["state"]:
            comp["next_toggle"] = current_time + comp["on_duration"]
        else:
            comp["next_toggle"] = current_time + comp["off_duration"]

def set_valve(comp, value):
    """
    Set the GPIO output for the valve only.
    For water components (whose gpio is a tuple),
    only the valve (first element) is set.
    """
    if isinstance(comp["gpio"], tuple):
        comp["gpio"][0].set_value(1 if value else 0)
    else:
        comp["gpio"].set_value(1 if value else 0)

def adaptive_water_logic(comp_name, sensor_value, current_time):
    """
    For adaptive water mode:
      - If sensor_value < 450, start watering (set state True for 5 seconds).
      - If already watering and sensor_value remains below 680, extend watering.
      - Otherwise, stop watering.
    """
    comp = components[comp_name]
    if "watering_until" not in comp:
        comp["watering_until"] = 0
    if sensor_value < 450:
        comp["state"] = True
        comp["watering_until"] = current_time + 5
    elif sensor_value < 680:
        if comp["state"]:
            comp["watering_until"] = current_time + 5
    else:
        comp["state"] = False
        comp["watering_until"] = 0

def handle_manual_mode(data):
    """
    Handle manual mode for lights and water valves.
    (Pump control and heater are handled separately.)
    """
    # Bottom level
    if data.get("bottom_initialized", False):
        if data.get("bottom_mode", "manual") == "manual":
            led_line_17.set_value(1 if data.get("bottom_man_light", False) else 0)
            led_line_22.set_value(1 if data.get("bottom_man_water", False) else 0)
    # Top level
    if data.get("top_initialized", False):
        if data.get("top_mode", "manual") == "manual":
            led_line_27.set_value(1 if data.get("top_man_light", False) else 0)
            led_line_10.set_value(1 if data.get("top_man_water", False) else 0)

def update_pump(data):
    """
    Update the pump (via led_line_9).
    The pump is ON if either water component (scheduling, adaptive, or manual) indicates watering.
    """
    bottom_mode = data.get("bottom_mode", "manual")
    if bottom_mode in ["scheduling", "adaptive"]:
        bottom_state = components["bottom_water"]["state"]
    else:
        bottom_state = data.get("bottom_man_water", False)
    top_mode = data.get("top_mode", "manual")
    if top_mode in ["scheduling", "adaptive"]:
        top_state = components["top_water"]["state"]
    else:
        top_state = data.get("top_man_water", False)
    pump_state = bottom_state or top_state
    led_line_9.set_value(1 if pump_state else 0)

def update_heater(data, sensors):
    """
    Update the heater (controlled by heater_line).
    Use the current temperature from sensors and the target temperature from flags.
    If current temp < (target_temp - 5) and heater is off, turn it on.
    If heater is on and current temp >= target_temp, turn it off.
    """
    global heater_state
    current_temp = sensors.get("temp", 20)
    target_temp = data.get("target_temp", 25)
    if not heater_state and current_temp < (target_temp - 5):
        heater_state = True
    elif heater_state and current_temp >= target_temp:
        heater_state = False
    heater_line.set_value(1 if heater_state else 0)

# Initialize heater state.
heater_state = False

# --- Main Event Loop ---
while True:
    current_time = time.monotonic()
    
    # --- Ultrasonic Sensor Sampling (Every 5 Seconds) ---
    if current_time >= next_ultrasonic_sample:
        distance_cm = ultrasonic_sensor.distance * 100  # convert meters to centimeters
        sensor_readings_ref.update({"ultrasonic": distance_cm})
        next_ultrasonic_sample = current_time + 5

    data = ref.get()  # Get the latest flags values

    # --- Process Bottom Light ---
    comp = components["bottom_light"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("bottom_light", data, current_time)
                update_tts_firebase("bottom_light", current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
            update_tts_firebase("bottom_light", current_time)
        elif mode == "adaptive":
            if data.get("adp_bottom_light_edit", False):
                update_adaptive_schedule("bottom_light", data, current_time)
                update_tts_firebase("bottom_light", current_time)
                ref.update({"adp_bottom_light_edit": False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
            update_tts_firebase("bottom_light", current_time)

    # --- Process Top Light ---
    comp = components["top_light"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("top_light", data, current_time)
                update_tts_firebase("top_light", current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
            update_tts_firebase("top_light", current_time)
        elif mode == "adaptive":
            if data.get("adp_top_light_edit", False):
                update_adaptive_schedule("top_light", data, current_time)
                update_tts_firebase("top_light", current_time)
                ref.update({"adp_top_light_edit": False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
            update_tts_firebase("top_light", current_time)

    # --- Process Bottom Water ---
    comp = components["bottom_water"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("bottom_water", data, current_time)
                update_ttw_firebase("bottom_water", current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_valve(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
            update_ttw_firebase("bottom_water", current_time)
        elif mode == "adaptive":
            sensors = db.reference("Sensors").get()
            soil_value = sensors.get("soil_2", 700)
            adaptive_water_logic("bottom_water", soil_value, current_time)
            set_valve(comp, comp["state"])

    # --- Process Top Water ---
    comp = components["top_water"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("top_water", data, current_time)
                update_ttw_firebase("top_water", current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_valve(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
            update_ttw_firebase("top_water", current_time)
        elif mode == "adaptive":
            sensors = db.reference("Sensors").get()
            soil_value = sensors.get("soil_1", 700)
            adaptive_water_logic("top_water", soil_value, current_time)
            set_valve(comp, comp["state"])

    # --- Process Manual Mode for Lights and Water Valves ---
    handle_manual_mode(data)

    # --- Update Pump State ---
    update_pump(data)

    # --- Heater Control ---
    sensors = db.reference("Sensors").get()
    update_heater(data, sensors)

    time.sleep(0.5)
