import time
from machine import I2C, Pin

#datasheet https://www.mouser.com/datasheet/2/418/MS5837-30BA-736494.pdf?srsltid=AYCX9vIWxsrw0gxYwFgX4naeRT8CpY4-WciT9SYMw1dXpRnMSHFikFi8

i2c_scl_pin = Pin(5) # default i2c scl pin, gpio 5, physical pin 7
i2c_sda_pin = Pin(4) # default i2c sda pin, gpio 4, physical pin 6
i2c_freq = 400000 #high frequency for the i2c comm

MS5837_ADDR = 0x76

CMD_RESET = 0x1E #reloads the calibration PROM into the sensor's internal register
CMD_ADC_READ = 0x00 #returns the 24-bit result of the last conversion
CMD_PROM_READ = 0xA0 #0xA0, 0xA2 ... 0xAC reads PROM words 0 - 6 (factory calibration coefficients C0 - C6)
CMD_CONVERT_D1 = 0x40 #start a pressure conversion
CMD_CONVERT_D2 = 0x50 #start a temperature conversion

crc_polynomial = 0x3000
#oversampling ratio (OSR): higher = less noise but each conversion takes longer
#datasheet page 2 - max conversion time, page 3 - resolution RMS
#OSR: (command offset, max conversion time in microseconds)
OSR_SETTINGS = { #a lopkup table for the osr settings. The setting followed by the offset for each command and the max amount of microseconds a reading takes
    256:  (0x00, 600),    #1.57 mbar RMS
    512:  (0x02, 1170),   #0.84 mbar RMS
    1024: (0x04, 2280),   #0.54 mbar RMS
    2048: (0x06, 4540),   #0.38 mbar RMS
    4096: (0x08, 9040),   #0.28 mbar RMS
    8192: (0x0A, 18080),  #0.20 mbar RMS, about 2 mm of water
}
osr = 8192 #oversampling ratio , how many samples the adc averages into 1 result, more samples = more accurate

grav_constant = 9.80665 # constant to convert to pascals of water column, m/s^2
fluid_density_freshwater = 997 #kg/m^3 - fresh water
fluid_density_saltwater = 1029
surface_samples = 20 #number of readings averaged at startup to get the surface (air) pressure

poll_rate = 50 #the rate at which the sensor will be polled in ms

i2c = I2C(0, scl = i2c_scl_pin, sda = i2c_sda_pin, freq = i2c_freq) #declare the i2c object on channel 0 with the given pin numbers and frequencies

def check_for_sensor(): #Scan the I2C bus and check which addresses are available on it
    devices = i2c.scan()
    if MS5837_ADDR not in devices: #if the depth sensor is not on the bus
        raise RuntimeError( #throw error and terminate
            "MS5837 sensor was not found. "
            f"Devices on the bus: {[hex(a) for a in devices]}"
        )
    else: #otherwise print confirmation
        print("MS5837 sensor was found!")

def send_command(cmd): #Send a one byte command, commands are specified at the top of the program
    i2c.writeto(MS5837_ADDR, bytes([cmd]))

def read_prom(): #Sensor stores 7 distinct calibration factors, read and return them all
    calibration_factors = [] #empty list to hold the factors
    for i in range(7): #for each factor
        send_command(CMD_PROM_READ + 2 * i) #each factor is two bytes long, increment the command by 2 for each factor
        factor = i2c.readfrom(MS5837_ADDR, 2) #read the 2 byte factor
        #MSB is sent first
        #shift msb left by 8 bits then OR with the lsb to get the full 16 bit value
        calibration_factors.append((factor[0] << 8) | (factor[1]))
    return calibration_factors

def crc4(calibration_factors): # A function that calculates a polynomial division check to verify the integrity of the calibration factors
    #This function was adapted from the provided C code on page 12 of the datasheet
    crc4_calibration_factors = list(calibration_factors) + [0] # add an 8th word to be used in the crc check
    crc4_calibration_factors[0] = crc4_calibration_factors[0] & 0x0FFF #the crc sits in the top 4 bits of the first word, initialize them to 0
    remainder = 0
    for count in range(16): #iterate through each of the bytes, 16 bytes in the 8 words
        current_word = count >> 1 #the current word is the integer division of the count by 2
        if count % 2 == 1: #if we are on an odd byte, we use the low byte of the current word
            remainder = remainder ^ (crc4_calibration_factors[current_word] & 0x00FF) # XOR against the lower 8 bits of the word
        else: #We must be on an even byte, use the high byte of the current word
            remainder = (remainder ^ crc4_calibration_factors[current_word] >> 8) # XOR against the higher 8 bits of the word
        for bit in range(8): #iterate thru each bit of the selected byte
            if remainder & 0x8000: #if the MSB is set,
                #shift the remainder left by 1 bit
                #XOR with the polynomial from the datasheet
                #AND against 0xFFFF to chop off any bits above the lower 16, they arent needed
                remainder = ((remainder << 1) ^ crc_polynomial) & 0xFFFF 
            else: #if its not set
                #Just shift and chop higher bits off
                remainder = (remainder << 1) & 0xFFFF
    return (remainder >> 12) & 0x000F
    
def initialize_sensor():
    check_for_sensor()
    
    send_command(CMD_RESET) #make sure the sensor is reset before beginning
    time.sleep_ms(20) #give it time to fully reset
    
    calibration_factors = read_prom()
    
    crc_factory = calibration_factors[0] >> 12
    crc_calculated = crc4(calibration_factors)
    if crc_factory != crc_calculated:
        raise RuntimeError(
            "MS5837 calibration failed its CRC check. "
            f"factory {hex(crc_factory)}, calculated {hex(crc_calculated)}"
    )
    
    print("MS5837 initialized successfully!")
    return calibration_factors

def read_adc(conversion_cmd):
    offset, wait_time = OSR_SETTINGS[osr] #find the correct command offset and max read time from the lookup table
    send_command(conversion_cmd + offset) #send the basic command plus the offset from our OSR setting
    time.sleep_us(wait_time) #wait the max amount of time
    send_command(CMD_ADC_READ) #tell the adc you are ready for the result
    data = i2c.readfrom(MS5837_ADDR, 3) #24 bit result MSB comes first
    value = (data[0] << 16) | (data[1] << 8) | data[2] #combine each byte into one 24 bit value
    
    if value == 0: #probably read too early, conversion failed  datasheet page 9 talks about this
        raise OSError("ADC returned a 0") #skip this reading instead of calculating garbage from it
    return value

def calculate(D1, D2, C): #turns the raw pressure (D1) and temperature (D2) into mbar and degrees C
    #Based on the datasheets flowcharts page 7 and 8
 
    #first order calculation
    dT = D2 - C[5] * 256 #difference between actual and reference temperature (C5 * 2^8)
    TEMP = 2000 + dT * C[6] // 8388608 #actual temperature in 0.01 C (2^23)
    OFF = C[2] * 65536 + C[4] * dT // 128 #offset at actual temperature (C2 * 2^16 + C4 * dT / 2^7)
    SENS = C[1] * 32768 + C[3] * dT // 256 #sensitivity at actual temperature (C1 * 2^15 + C3 * dT / 2^8)
 
    #second order temperature compensation
    if TEMP < 2000: #low temperature, below 20 C
        Ti = 3 * dT * dT // 8589934592 #2^33
        OFFi = 3 * (TEMP - 2000) * (TEMP - 2000) // 2
        SENSi = 5 * (TEMP - 2000) * (TEMP - 2000) // 8
        if TEMP < -1500: #very low temperature, below -15 C
            OFFi += 7 * (TEMP + 1500) * (TEMP + 1500)
            SENSi += 4 * (TEMP + 1500) * (TEMP + 1500)
    else: #high temperature, 20 C and above
        Ti = 2 * dT * dT // 137438953472 #2^37
        OFFi = (TEMP - 2000) * (TEMP - 2000) // 16
        SENSi = 0
 
    OFF2 = OFF - OFFi
    SENS2 = SENS - SENSi
    TEMP2 = TEMP - Ti #still in 0.01 C
    P2 = (D1 * SENS2 // 2097152 - OFF2) // 8192 #pressure in 0.1 mbar (D1 * SENS2 / 2^21 - OFF2) / 2^13
 
    return P2 / 10.0, TEMP2 / 100.0 #convert to mbar and degrees C

def read_sensor(C): #reads pressure and temperature, returns them in mbar and degrees C
    D1 = read_adc(CMD_CONVERT_D1) #raw pressure
    D2 = read_adc(CMD_CONVERT_D2) #raw temperature
    return calculate(D1, D2, C)

def pressure_to_depth(pressure, surface_pressure): #converts the mbar pressure reading into the depth below the water
    # eqn used: depth = pressure above the sensor / (density * gravity)
    curr_pressure_difference = pressure - surface_pressure
    pascals = curr_pressure_difference * 100
    return pascals / (fluid_density_freshwater * grav_constant)

def find_surface_pressure(C): #averages a few readings in the air to find the current surface pressure
    #pressure is dependant on weather and other factors
    # this should be run while the sensor is outside of the water to get accurate readings
    total = 0.0
    for i in range (surface_samples):
        pressure, temperature = read_sensor(C)
        total += pressure
        time.sleep_ms(poll_rate)
    surface_pressure = total / surface_samples #only after all the samples have been added up
    print(f"Surface pressure: {surface_pressure} mbar")
    return surface_pressure

C = initialize_sensor()
surface_pressure = find_surface_pressure(C)

while True: #infinite loop to read and print sensor data
    start = time.ticks_ms()
    try:
        pressure, temperature = read_sensor(C)
        depth = pressure_to_depth(pressure, surface_pressure)
 
        print( #print formatted data
        f"Pressure: {pressure:8.1f} mbar | "
        f"Temp: {temperature:6.2f} C | "
        f"Depth: {depth:7.3f} m"
        )
    except OSError as e: #i2c errors (loose wire, sensor brownout, etc.) - a bug in the code still stops the program
        #dont end the program, just print the exception and try again next loop
        print("Error communicating with sensor:", e)
 
    #sleep for whatever is left of the poll_rate period so the loop runs at a steady rate
    remaining = poll_rate - time.ticks_diff(time.ticks_ms(), start) #ticks_diff handles the ms counter wrapping around
    if remaining > 0: #if the reading took longer than poll_rate, skip the sleep
        time.sleep_ms(remaining)