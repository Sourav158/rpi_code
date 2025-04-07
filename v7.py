import time
import gpiod
import firebase_admin
from firebase_admin import credentials, db

# Define GPIO pins
LED_PIN_17 = 17  # bottom light
LED_PIN_27 = 27  # top light
LED_PIN_22 = 22  # bottom water valve
LED_PIN_10 = 10  # top water valve
LED_PIN_9  = 9   # shared water pump
LED_PIN_11 = 11  # heater

# Initialize GPIO chip and lines
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

# Initialize Firebase
cred = credentials.Certificate("/home/pi/final_testing/fire_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://finaltesting-bcb9e-default-rtdb.firebaseio.com/'
})
ref = db.reference("Flags")

# Dictionary holding state for each component.
# For water, gpio is a tuple: (valve, pump). Valve control is independent.
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
        "on_duration": 0,
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "bottom_initialized",
        "mode_key": "bottom_mode",
        "edit_flag": "bottom_mode_water_edit"
    },
    "top_water": {
        "gpio": (led_line_10, led_line_9),  # (valve, pump)
        "state": False,
        "on_duration": 0,
        "off_duration": 0,
        "next_toggle": time.monotonic(),
        "init_key": "top_initialized",
        "mode_key": "top_mode",
        "edit_flag": "top_mode_water_edit"
    }
}

# Heater state variable (independent of other modes)
heater_state = False

def update_schedule(comp_name, data, current_time):
    """Update schedule for 'scheduling' mode without resetting next_toggle if it’s in the future."""
    comp = components[comp_name]
    if comp_name in ["bottom_light", "top_light"]:
        total_on = data.get(f"{comp_name}_ref_on_hrs", 0) * 1 + data.get(f"{comp_name}_ref_on_mins", 0) * 1
        total_off = data.get(f"{comp_name}_ref_off_hrs", 0) * 1 + data.get(f"{comp_name}_ref_off_mins", 0) * 1
        comp["on_duration"] = total_on
        comp["off_duration"] = total_off
    elif comp_name in ["bottom_water", "top_water"]:
        amount = data.get(f"{comp_name}_amount", 0)
        total_off = (data.get(f"{comp_name}_ref_days", 0) * 1 +
                     data.get(f"{comp_name}_ref_hrs", 0) * 1 +
                     data.get(f"{comp_name}_ref_mins", 0) * 1)
        comp["on_duration"] = amount
        comp["off_duration"] = total_off
    if comp["next_toggle"] < current_time:
        if comp["state"]:
            comp["next_toggle"] = current_time + comp["on_duration"]
        else:
            comp["next_toggle"] = current_time + comp["off_duration"]

def update_adaptive_schedule(comp_name, data, current_time):
    """
    Update schedule for light components in 'adaptive' mode.
    Convert adaptive hours to seconds.
    """
    comp = components[comp_name]
    if comp_name == "bottom_light":
        total_on = data.get("adp_bottom_light_on_hrs", 0) * 1
        total_off = data.get("adp_bottom_light_off_hrs", 0) * 1
    elif comp_name == "top_light":
        total_on = data.get("adp_top_light_on_hrs", 0) * 1
        total_off = data.get("adp_top_light_off_hrs", 0) * 1
    comp["on_duration"] = total_on
    comp["off_duration"] = total_off
    if comp["next_toggle"] < current_time:
        if comp["state"]:
            comp["next_toggle"] = current_time + comp["on_duration"]
        else:
            comp["next_toggle"] = current_time + comp["off_duration"]

def set_valve(comp, value):
    """
    Set the GPIO output for the valve only.
    For water components, update the first element (valve) only.
    """
    if isinstance(comp["gpio"], tuple):
        comp["gpio"][0].set_value(1 if value else 0)
    else:
        comp["gpio"].set_value(1 if value else 0)

def adaptive_water_logic(comp_name, sensor_value, current_time):
    """
    For adaptive water mode:
      - If sensor_value is below 450, trigger watering (set state True and water for 5 seconds).
      - If already watering and sensor_value remains below 680, extend watering by 5 seconds.
      - Only when sensor_value is >=680, stop watering.
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
        # else: if not already watering, keep state False.
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
    Update pump (led_line_9) state.
    Pump is ON if either water component (scheduling, adaptive, or manual) indicates watering.
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
    Update heater (controlled by heater_line, GPIO 11).
    Read current temperature from sensors ("temp").
    From Flags, read "target_temp".
    If current temp is less than (target_temp - 5) and heater is off, turn heater on.
    If heater is on and current temp is >= target_temp, turn heater off.
    """
    global heater_state
    current_temp = sensors.get("temp", 20)
    target_temp = data.get("target_temp", 25)
    if not heater_state and current_temp < (target_temp - 5):
        heater_state = True
    elif heater_state and current_temp >= target_temp:
        heater_state = False
    heater_line.set_value(1 if heater_state else 0)

# Initialize heater state
heater_state = False

# --- Main Event Loop ---
while True:
    current_time = time.monotonic()
    data = ref.get()  # Fetch latest Flags values

    # Process bottom light
    comp = components["bottom_light"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("bottom_light", data, current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
        elif mode == "adaptive":
            if data.get("adp_bottom_light_edit", False):
                update_adaptive_schedule("bottom_light", data, current_time)
                ref.update({"adp_bottom_light_edit": False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]

    # Process top light
    comp = components["top_light"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("top_light", data, current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
        elif mode == "adaptive":
            if data.get("adp_top_light_edit", False):
                update_adaptive_schedule("top_light", data, current_time)
                ref.update({"adp_top_light_edit": False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                comp["gpio"].set_value(1 if comp["state"] else 0)
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]

    # Process bottom water
    comp = components["bottom_water"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("bottom_water", data, current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_valve(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
        elif mode == "adaptive":
            sensors = db.reference("Sensors").get()
            soil_value = sensors.get("soil_2", 700)
            adaptive_water_logic("bottom_water", soil_value, current_time)
            set_valve(comp, comp["state"])

    # Process top water
    comp = components["top_water"]
    mode = data.get(comp["mode_key"], "manual")
    if data.get(comp["init_key"], False):
        if mode == "scheduling":
            if data.get(comp["edit_flag"], False):
                update_schedule("top_water", data, current_time)
                ref.update({comp["edit_flag"]: False})
            if current_time >= comp["next_toggle"]:
                comp["state"] = not comp["state"]
                set_valve(comp, comp["state"])
                if comp["state"]:
                    comp["next_toggle"] = current_time + comp["on_duration"]
                else:
                    comp["next_toggle"] = current_time + comp["off_duration"]
        elif mode == "adaptive":
            sensors = db.reference("Sensors").get()
            soil_value = sensors.get("soil_1", 700)
            adaptive_water_logic("top_water", soil_value, current_time)
            set_valve(comp, comp["state"])

    # Process manual mode for lights and water valves
    handle_manual_mode(data)

    # Update pump state based on combined water states
    update_pump(data)

    # Heater control: Independent of other modes.
    sensors = db.reference("Sensors").get()
    update_heater(data, sensors)

    time.sleep(0.5)
