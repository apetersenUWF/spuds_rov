# Underwater Search And Rescue ROV

**University of West Florida**

Senior Capstone Design Project by Ayden Petersen, Lucas Garrett, Marissa Guidry, Sean Holman, Gunnar Gressett, and Charis Allen

*Mentored by Dr. Shaer*

The goal of this project is to build an underwater search and rescue ROV that can be deployed from a 'mothership' and controlled from afar by an operator. The ROV will provide the user with a low latency HD video stream as well as some basic sensor telemetry. The project consists of four independently running devices:
1. **Raspberry Pi 4** - *Underwater ROV*: The Raspberry Pi will be responsible for hosting the livestream via a connected Pi Cam 3 module as well as forwarding controller inputs to the Raspberry Pi Pico and forwarding sensor readings back to the mothership.
2. **Raspberry Pi Pico** - *Underwater ROV*: The Raspberry Pi Pico onboard the underwater ROV will be responsible for reading the sensors, running PID algorithms to stabilize and hold the depth of the ROV, and send PWM signals to the ESCs to control the motors.
3. **Raspberry Pi Pico** - *Mothership*: The Raspberry Pi Pico on the mothership will be responsible for parsing incoming motor commands targetted at the mothership and driving the two motors as well as triggering the release/return mechanism for the ROV.
4. **C# User Interface** - *Ground Station Computer*: The Ground Station Computer will be running the C# User Interface on Microsoft Visual Studio and it will be responsible for receiving and displaying the live video stream and sensor telemetry. It will also be responsible for parsing inputs from the Xbox controller and sending them to the mothership to control the mothership and ROV.

This repository contains the software for the each of these subsystems.

## docs
Contains documentation such as network ports, ips, communication protocols, message formats, and config files.

## mothership-pico
Contains the program running on the Raspberry Pi Pico on the morthership. Run by connecting the pico to the Raspberry pi 4 over USB and using:

```bash
cd mothership-pico
mpremote run main.py
```

## rov-pi
Contains the program to setup the pi cam, configure the encoder, and output the video to the MediaMTX stream. Run using:

```bash
cd rov-pi
python3 webtrc_stream.py
```

## rov-pico
Contains the program running on the Raspberry Pi Pico on the underwater ROV. Run by connecting the pico to the Raspberry pi 4 over USB and using:

```bash
cd rov-pico
mpremote run main.py
```

## tools
Contains test scripts pertaining to the various sensors and microcontrollers.

## topside
Contains the solution to run the main UI in Microsoft Visual Studio.
