import time
from machine import Pin, PWM

#a program to test 6 bidirectional escs using the raspberry pi pico

esc_pins = [10, 11, 12, 13, 14, 15] #esc signal pins on pico gpio pins 10,11,12,13,14,15
pulse_width_min = 1000 #full reverse pulse width, check datasheet to tweak this
pulse_width_middle = 1500 #stop pulse width for the ESC: 1500 for bidirectional
pulse_width_max = 2000 #full forward pulse width, check datasheet to tweak this
initialization_time = 2000 #Time that the program uses to setup the escs before accepting motor commands, ms
motor_runtime = 500 #The time the motor will spin for after a command is given
esc_freq = 50 # 50 hz esc signal

ESCs = [] 

def set_pulse_width_us(esc, us): #set the pulse duty cycle for the esc
    #takes an esc and pulse width in microseconds
    #valid inputs are usually between 1000-2000 us
    esc.duty_ns(int(us * 1000))  #use duty_ns to set a specific hightime in nanoseconds. Multiply by 1000 since we us emicroseconds

def stop_all_motors(): #set all the escs to their middle pulse value
    for esc in ESCs:
        set_pulse_width_us(esc, pulse_width_middle)

def initialize_escs(): #Setup the escs on the defined pins and print their information
    print(f"Initializing ESCs on Pins: {esc_pins}")
    for pin in esc_pins:
        ESCs.append(PWM(Pin(pin), freq=esc_freq)) #initialize each pin as a PWM pin, use defined esc frequency
    stop_all_motors() # set all escs to the middle value (STOP) for startup
    time.sleep_ms(initialization_time) #wait a few seconds to make sure it gets the stop signal
    print(f"Stop signal of {pulse_width_middle} us has been sent to all ESCs")
    print("Initialization Complete")
    print("=" * 50)
    print("ESCs and their pins:") #print which esc_id goes to which pin
    for index, pin in enumerate(esc_pins): #just prints the index of the esc next to its pin number
        print(f"ESC{index}: GPIO pin #{pin}")
    print("=" * 50)

def parse_cmd(line): #this function takes the full user input string and returns the esc_id and pulse_width 
    # upon success returns id, pulse_width
    # upon failure returns None
    # line is the user input
    line = line.replace(",", " ") #replace all commas with spaces
    parts = line.split() #split the string into different parts where there is spaces and return a list with each part
    if len(parts) != 2: #There should be 2 parts, id and pulse width
        return None #if not return none
    esc_id = int(parts[0]) #try to get the two parts
    value = int(parts[1])
    if esc_id < 0 or esc_id >= len(ESCs): #check if the id is valid
        return None
    if value > pulse_width_max or value < pulse_width_min: #check if the pulse width is valid
        return None
    return esc_id, value

def run_motor(esc_id, pulse_width): #this function runs the motor on esc (esc_id) with the defined pulse width
    print(f"Running ESC{esc_id} at a pulse width of {pulse_width} microseconds for {motor_runtime} ms")
    print('Running...')
    set_pulse_width_us(ESCs[esc_id], pulse_width)
    time.sleep_ms(motor_runtime) # only let the motor run for a certain amount of time for safety
    set_pulse_width_us(ESCs[esc_id], pulse_width_middle)
    print('Done')


#Start of the main program

initialize_escs()
print("Enter the ESC ID followed by the pulse length in microseconds")
try:
    while True:
        user_input = input("> ").strip() #strip any leading or trailing spaces "  1 1600   " becomes "1 1600"
        cmd = parse_cmd(user_input) # parse and return the two values we need
        if cmd is None: #parse_cmd failed
            print("Invalid Command")
            continue
        esc_id = cmd[0]
        pulse_width = cmd[1]
        run_motor(esc_id, pulse_width) #run the correct motor
        stop_all_motors() #always make sure all the motors are stopped afterwards
finally: #this block runs if ctrl+C was pressed or if the program is stopped unexpectedly
    stop_all_motors() #Make sure all motors are stopped incase the program crashes while they are moving




