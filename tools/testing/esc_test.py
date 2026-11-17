import time
from machine import Pin, PWM

esc_pins = [10, 11, 12, 13, 14, 15] #esc signal pins on pico gpio pins 10,11,12,13,14,15
pulse_width_min = 1000
pulse_width_middle = 1500 #stop pulse width for the ESC: 1500 for bidirectional
pulse_width_max = 2000
initialization_time = 2000 #Time that the program uses to setup the escs before accepting motor commands, ms
motor_runtime = 500 #The time the motor will spin for after a command is given
esc_freq = 50 # 50 hz esc signal

ESCs = []

def set_pulse_width_us(esc, us):
    esc.duty_ns(int(us * 1000))

def stop_all_motors():
    for esc in ESCs:
        set_pulse_width_us(esc, pulse_width_middle)

def initialize_escs():
    print(f"Initializing ESCs on Pins: {esc_pins}")
    for pin in esc_pins:
        ESCs.append(PWM(Pin(pin), freq=esc_freq)) #initialize each pin as a PWM pin
    stop_all_motors()
    time.sleep_ms(initialization_time)
    print(f"Stop signal of |{pulse_width_middle} us| has been sent to all ESCs")
    print("Initialization Complete")
    print("=" * 50)
    print("ESCs and their pins:")
    for index, pin in enumerate(esc_pins):
        print(f"ESC{index}: GPIO pin #{pin}")
    print("=" * 50)

def parse_cmd(line):
    line = line.replace(",", " ") #replace all commas with spaces
    parts = line.split() #split the string into different partswhere there is spaces and return a list with each part
    if len(parts) != 2:
        return None
    esc_id = int(parts[0])
    value = int(parts[1])
    if esc_id < 0 or esc_id >= len(ESCs):
        return None
    if value > pulse_width_max or value < pulse_width_min:
        return None
    return esc_id, value

def run_motor(esc_id, pulse_width):
    print(f"Running ESC{esc_id} at a pulse width of {pulse_width} microseconds for {motor_runtime} ms")
    print('Running...')
    set_pulse_width_us(ESCs[esc_id], pulse_width)
    time.sleep_ms(motor_runtime)
    set_pulse_width_us(ESCs[esc_id], pulse_width_middle)
    print('Done')

initialize_escs()
print("Enter the ESC ID followed by the pulse length in microseconds")
try:
    while True:
        user_input = input("> ").strip()
        cmd = parse_cmd(user_input)
        if cmd is None:
            print("Invalid Command")
            continue
        esc_id = cmd[0]
        pulse_width = cmd[1]
        run_motor(esc_id, pulse_width)
        stop_all_motors()
finally:
    stop_all_motors()




