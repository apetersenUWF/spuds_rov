#include <Servo.h> //for writeMicroseconds()

const unsigned long BAUD = 115200; //serial bitrate
const int motor_spin_time = 500; //the time to activate the motor for in ms
const unsigned int pulse_width_middle = 1500; //the center value for the motor, tells the motor to stop spinning
const unsigned int motors_count = 4; //the number of motors or esc channels to control
const unsigned int motor_signals[4] = {30, 31, 32, 33}; //the pins that drive the esc signals

Servo motors[4]; //not actually used for servos, has same functionality
unsigned int pulse_width = pulse_width_middle; //initialize the pulse width as the stopping value

void attachAllMotors() { //a function that attaches each motor to the cooresponding signal pin
  for (unsigned int i = 0; i < motors_count; i++) motors[i].attach(motor_signals[i], 1000, 2000);
}
void stopAllMotors() { //a function that sets all the motors to the middle value i.e stop
  for (unsigned int i = 0; i < motors_count; i++) motors[i].writeMicroseconds(pulse_width_middle);
}
void printMotorInfo() { //a function that prints which motor/esc channel is connected to what pin
  Serial.println("******************************");
  for (unsigned int i = 0; i < motors_count; i++) {
    Serial.print("Motor #");
    Serial.print(i+1); //user reads them as 1-4 instead of 0-3 for readability
    Serial.print(" is on pin ");
    Serial.print(motor_signals[i]);
    Serial.print("\n");
  }
  Serial.println("******************************");
}

void initializeMotors() { //a function that attaches all motors and stops them for 5 seconds to initialize
  Serial.print("Initializing motors on pins ");
  for (unsigned int i = 0; i < motors_count; i++) { //print all of the pins being used
    Serial.print(motor_signals[i]);
    if (i != motors_count - 1) Serial.print(", ");
  }
  Serial.print("\n");
  attachAllMotors();
  stopAllMotors();
  delay(2000); //wait for the esc to finish startup sequence
  Serial.println("Initialization Complete!");
  printMotorInfo();
}

void setup() {
  Serial.begin(BAUD);
  initializeMotors();
  Serial.println("Enter the motor ID followed by the desired speed:");
}

void loop() {
  if (Serial.available() > 0) {
    int id = Serial.parseInt(); //id of the motor, valid inputs are 1 - (number of motors)
    int cmd = Serial.parseInt(); //speed command, valid inputs are -100 - 100, negative means reverse direction

  while (Serial.available() > 0) { //keep reading any trailing characters to clear the serial buffer
      Serial.read();
    }

    if (cmd > 100 || cmd < -100 || id <= 0 || id > motors_count) { //verify its a valid command
      Serial.print("Invalid command\n");
    }
    else {
      pulse_width = pulse_width_middle + (cmd * 5);
      Serial.print("Toggling motor #");
      Serial.print(id);
      Serial.print(" at ");
      Serial.print(abs(cmd));
      Serial.print("% speed");
      if (cmd < 0) Serial.print(" in reverse");
      Serial.print(" for ");
      Serial.print(motor_spin_time);
      Serial.println(" milliseconds...");
      motors[id - 1].writeMicroseconds(pulse_width);
      delay(motor_spin_time);
      Serial.print("Complete\n");
      pulse_width = pulse_width_middle;
    }
  }
  stopAllMotors();
}
