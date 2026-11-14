import time
from machine import I2C, Pin

#datasheet: https://learn.adafruit.com/lsm6dsox-and-ism330dhc-6-dof-imu/downloads

i2c_scl_pin = Pin(5) # default i2c scl pin, gpio 5, physical pin 7
i2c_sda_pin = Pin(4) # default i2c sda pin, gpio 4, physical pin 6
i2c_freq = 400000 #high frequency for the i2c comm

LSM6DSOX_ADDR = 0x6A
WHO_AM_I_REG = 0x0F
who_am_i_val = 0x6C

LSM6DSOX_CTRL1_XL = 0x10 #datashett page 54 - accelerometer control reg
ctrl1_val = 0b01100000 #datasheet page 54 - sets to 416Hz (high-performance mode) and +-2g sensitivity

LSM6DSOX_CTRL2_G = 0x11 #datasheet page 55 - gyroscope control reg
ctrl2_val = 0b01100000 #datsheet page 55 - sets to 416Hz (high-performance mode) and +-250 dps sensitivity

LSM6DSOX_CTRL3_C = 0x12 #datasheet page 56 - R/W control reg
ctrl3_val = 0b01000100 #BDU = 1: output regs don't update until both bytes of a reading are read IF_INC = 1: reigister address automatically increments

LSM6DSOX_OUTX_L_A = 0x28 #datasheet page 70 - acceleration output regs
                                                #0x28 - 0x29 x accel.
                                                #0x2A - 0x2B y accel.
                                                #0x2C - 0x2D z accel.
sensor_data_length = 6 # 2 byte for each direction x,y,z
accel_constant = 0.061 #datasheet page 10 Typ. column - constant to multiply the data by for +-2g sensitivity setting
grav_constant = 9.80665 # constant to convert g-force to meters per second squared

LSM6DSOX_OUTX_L_G = 0x22 #datasheet page 68 - gyro output regs
                                                #0x22 - 0x23 pitch x angular rate
                                                #0x24 - 0x25 roll y angular rate
                                                #0x26 - 0x27 yaw z angular rate
gyro_constant = 8.75 #datasheet page 10 Typ. column - constant to multiply the data by for +-250dps sensitivity setting

poll_rate = 20 #the rate at which the sensor will be polled in ms

i2c = I2C(0, scl = i2c_scl_pin, sda = i2c_sda_pin, freq = i2c_freq) #declare the i2c object on channel 0 with the given pin numbers and frequencies

ax_offset, ay_offset, az_offset = 0, 0, 0 #calibration values, stores the value that the sensor outputs while still so it can be subtracted later

gx_offset, gy_offset, gz_offset = 0, 0, 0 #calibration values, stores the value that the sensor outputs while still so it can be subtracted later

vx, vy, vz = 0, 0, 0 #velocity values, integrated acceleration

pitch, roll, yaw = 0, 0, 0 #orientation values, integrated angular velocity

def who_am_i(addr): # a function that asks the sensor to respond with its internally stored address
    
    data = i2c.readfrom_mem(addr, WHO_AM_I_REG, 1) #read 1 byte from the who_am_i register
    stored_addr = data[0] 

    if stored_addr != who_am_i_val: #check if the address is what we expected it to be from the datasheet
        raise RuntimeError( #if its not, stop the program and print the error
            f"LSM6DSOX sensor was not found"
            f"Querying the WHO_AM_I register returned {hex(stored_addr)}"
        )
    else: # if it was, report it as found and continue
        print("LSM6DSOX sensor was found!")

def find_offsets(): # a function that finds the sensor offsets when it is sitting still
                    # improves the accuracy of readings by reducing drift
    #initialize sum variables to track all the data
    ax_offset_sum, ay_offset_sum, az_offset_sum = 0, 0, 0 
    gx_offset_sum, gy_offset_sum, gz_offset_sum = 0, 0, 0
    for i in range(0, 100): #take 100 samples
        accel, gyro = read_sensor() #read the sensor
        #sum each of the values for all 100 samples
        ax_offset_sum += accel[0]
        ay_offset_sum += accel[1]
        az_offset_sum += accel[2]
        gx_offset_sum += gyro[0]
        gy_offset_sum += gyro[1]
        gz_offset_sum += gyro[2]
        time.sleep_ms(20) #wait 20ms between samples, whole process takes 2 seconds
    
    #take the average value over all 100 samples
    ax_off = ax_offset_sum / 100.0
    ay_off = ay_offset_sum / 100.0
    az_off = az_offset_sum / 100.0
    gx_off = gx_offset_sum / 100.0
    gy_off = gy_offset_sum / 100.0
    gz_off = gz_offset_sum / 100.0
    return (ax_off, ay_off, az_off), (gx_off, gy_off, gz_off)


def initialize_imu(): #runs the who_am_i test and configures
    global ax_offset, ay_offset, az_offset, gx_offset, gy_offset, gz_offset #used so the function can modify global variables
    who_am_i(LSM6DSOX_ADDR)

    i2c.writeto_mem(LSM6DSOX_ADDR, LSM6DSOX_CTRL1_XL, bytes([ctrl1_val])) #write settings to the accelerometer control register

    i2c.writeto_mem(LSM6DSOX_ADDR, LSM6DSOX_CTRL2_G, bytes([ctrl2_val])) #write settings to the gyro control register
    
    i2c.writeto_mem(LSM6DSOX_ADDR, LSM6DSOX_CTRL3_C, bytes([ctrl3_val])) #write settings to the R/W control register

    print("Finding IMU offsets, keep the sensor completely still during this process.")
    time.sleep_ms(200) #wait a bit before taking the first readings
    
    (ax_offset, ay_offset, az_offset), (gx_offset, gy_offset, gz_offset) = find_offsets() #populate global offset variables
    print("Offsets have been populated")
    
    print("LSM6DSOX initialized successfully!")

def twos_comp(val, bits): #a function to properly convert sensor readings to negative
#if the most significant bit is a 1, this is supposed to be a negative reading
  if val & (1 << (bits - 1)): #check the MSB , if it is 1
    val -= 1 << bits #take the twos complement i.e subtract 2^(number of bits)
  return val

def raw_accel_to_mss(raw_accel_data): #a function that converts raw acceleration readings into meters per second squared
    data = [] #declare a list to store the converted data
    for i in range(0, len(raw_accel_data), 2): #for each piece of data in the raw data, increment i by 2 each time
        #do the following:
        #data is read as two 8 bit integers, first combine the two 8 bit integers into 1 16-bit value
        #shift the most significant byte to the left by 8 bits and OR it with the least significant byte
        #take the twos complement of this result to account for readings that should be negative
        #multiply by the constant found in the datasheet to convert raw reading to milli g forces
        #divide this result by 1000 to get standard g forces
        #multiply by the gravity constant to convert from g forces into m/s^2
        #append this to the data list
        #1 converted data value for every 2 raw data values
        data.append(twos_comp((raw_accel_data[i+1] << 8) | (raw_accel_data[i]), 16) * accel_constant / 1000.0 * grav_constant)
    return data
def raw_gyro_to_dps(raw_gyro_data): #a function that converts raw gyro readings into degrees per second
    data = []
    for i in range(0, len(raw_gyro_data), 2): #for each piece of data in the raw data, increment i by 2 each time
        #do the following:
        #data is read as two 8 bit integers, first combine the two 8 bit integers into 1 16-bit value
        #shift the most significant byte to the left by 8 bits and OR it with the least significant byte
        #take the twos complement of this result to account for readings that should be negative
        #multiply by the constant found in the datasheet to convert raw reading to milli degrees per second
        #divide this result by 1000 to get degrees per second
        #append this to the data list
        #1 converted data value for every 2 raw data values
        data.append(twos_comp((raw_gyro_data[i+1] << 8) | (raw_gyro_data[i]), 16) * gyro_constant / 1000.0)
    return data

def read_sensor(): #reads the acceleration and gyro data from the sensor and returns them in m/s^2 and dps
    accel_data = i2c.readfrom_mem(LSM6DSOX_ADDR, LSM6DSOX_OUTX_L_A, sensor_data_length) #read sensor_data_length bytes from the data registers
    ax,ay,az = raw_accel_to_mss(accel_data) #convert the acceleration values to m/s^2 and store them
    #subtract offsets
    ax -= ax_offset
    ay -= ay_offset
    az -= az_offset
    gyro_data = i2c.readfrom_mem(LSM6DSOX_ADDR, LSM6DSOX_OUTX_L_G, sensor_data_length) #read sensor_data_length bytes from the data registers
    gx, gy, gz = raw_gyro_to_dps(gyro_data) #convert the gyro values to dps and store them
    #subtract offsets
    gx -= gx_offset
    gy -= gy_offset
    gz -= gz_offset

    return (ax, ay, az), (gx, gy, gz) #return all the sensor values



initialize_imu()
    
while True: #infinite loop to read and print sensor data
        
    try: #wrap everything in a try block in case something goes wrong
        start = time.ticks_ms() #record the time that the reading starts
        
        accel, gyro = read_sensor()
        
        dt = poll_rate/1000.0
        vx += accel[0]*dt
        vy += accel[1]*dt
        vz += accel[2]*dt
        
        pitch += gyro[0]*dt
        roll += gyro[1]*dt
        yaw += gyro[2]*dt
        
#         print( #print formatted data
#         f"Accel (m/s^2) -> X: {accel[0]:6.2f} | Y: {accel[1]:6.2f} | Z:"
#         f" {accel[2]:6.2f}  ||  "
#         f"Gyro (dps) -> X: {gyro[0]:6.2f} | Y: {gyro[1]:6.2f} | Z:"
#         f" {gyro[2]:6.2f}"
#         )

        print( #print formatted data
        f"Acceleration (m/s^2) -> X: {accel[0]:6.2f} | Y: {accel[1]:6.2f} | Z:"
        f" {accel[2]:6.2f}  ||  "
        f"Gyro (degrees) -> X: {pitch:6.2f} | Y: {roll:6.2f} | Z:"
        f" {yaw:6.2f}"
        )
        
    except Exception as e: #if an exception was thrown
        #dont end the program, just print the exception and try again
        print("Error communicating with sensor:", e)
        
    remaining = poll_rate - time.ticks_diff(time.ticks_ms(), start) #ticks_diff handles the ms counter wrapping around
    if remaining > 0: #if the reading took longer than poll_rate, skip the sleep
        time.sleep_ms(remaining)

        

    