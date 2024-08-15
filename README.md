# HelperBee24
Hey everyone! This project is a Voice Assistant designed to run on a Raspberry PI and aimed to provide a seamless voice interaction. This document will guide you through the setup process, required libraries, and hardware specifications.

# **Table of Contents**

1. Introduction
2. Features
3. Hardware Requirements
4. Software Requirements
5. Installation Guide
6. Usage

# **Introduction**

HelperBee is an open-source voice AI assistant tailored for Raspberry Pi. It leverages speech recognition and natural language processing to interact with users through voice commands. The assistant listens for a wake word, responds to commands, and can handle follow-up queries making it ideal for hands-free operation.

# Features

- Wake Word Detection: Activates upon detecting a pre-defined wake word.
- Continuous Listening: Listens for follow-up commands after responding to an initial query.
- Lightweight: Optimized for performance on Raspberry Pi.

# Hardware Requirements

To run HelperBee Voice AI, you'll need the following hardware:

- **Raspberry Pi 4 or later**: The project is designed for Raspberry Pi 4 but may work on earlier versions.
- **USB Microphone**: For capturing voice input.
- **Speakers or Headphones**: For audio output.
- **MicroSD Card (32GB or larger)**: For installing the operating system and storing files.
- **Power Supply**: A 5V, 3A power supply is recommended for stable operation.

## Software Requirements

The following libraries and software are required to run HelperBee:

- **Python 3.7 or later**: The main programming language used in this project.
- **sounddevice**: For audio input and output.
- **numpy**: Required for handling numerical operations.
- **pyaudio**: An optional library for handling audio streams.
- **picovoice**: For wake word detection (or any other wake word detection library of your choice).
- **SpeechRecognition**: For recognizing spoken words.
- **Threading**: For managing multiple tasks concurrently.
- **Raspbian OS**: Recommended operating system for the Raspberry Pi- Rasberry Pi OS lite.

# Installation Guide

# **Prepare the MicroSD Card**

1. Download and Install the Raspberry Pi Imager from [this link](https://www.raspberrypi.com/software/)
2. Use Imager to flash ****the latest version of **Raspberry Pi OS Lite (64-Bit)**
    1. Make sure you select the **Lite** image, which may be under the Raspberry Pi OS (other) menu
    2. Make sure 64-bit is selected
    3. Configure Wireless connection before flashing, if necessary

# Setting Up Raspberry Pi

Insert the flashed MicroSD card into the Raspberry Pi with 6.1 version https://www.raspberrypi.com/software/operating-systems/

### **Raspberry Pi OS (Legacy) Lite**

- Release date: July 4th 2024
- System: 32-bit
- Kernel version: 6.1
- Debian version: 11 (bullseye)
- Size: 366 MB
1. Connect the Raspberry Pi to an external display
2. Power on the Raspberry Pi
3. Run the following commands to install and initial updates:

```php
sudo apt update
sudo apt full-upgrade
```

1. Run the following commands to install the necessary audio drivers:

```php
sudo apt install alsa-utils 
```

# Install [Hintak SeeedStudio Driver](https://github.com/HinTak/seeed-voicecard)

1. Install Dependencies

```php
sudo apt install build-essential git dkms libusb-1.0-0-dev
```

2. Clone the Repository

```php
git clone https://github.com/HinTak/seeed-voicecard
cd seeed-voicecard
```

3. Switch to the current kernel branch

```php
uname -a //checks kernel version, skip if known

```

4. Install & Reboot

```php
sudo ./install.sh
sudo reboot
```

1. Verify the installation by running commands & verifying Respeaker device:

```php
arecord -l
aplay -l
```

# Configure ALSA Defaults for Playback & Recording

1. **Create or Modify `.asoundrc`**:

Create or edit the `~/.asoundrc` file (`nano ~/.asoundrc`) to set the ReSpeaker as the default audio device. Here’s an example configuration:

```
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:seeed2micvoicec"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:seeed2micvoicec"
    }
}

ctl.!default {
    type hw
    card seeed2micvoicec
}

```

Replace `seeed4micvoicec` with the actual name of your ReSpeaker device most likely will be seeed2micvoicec, or you can find from the `arecord -l` output in previous step

1. Test Playback through ReSpeaker
2. Test Recording through Respeaker

```php
arecord -D hw:seeed2micvoicec -f cd test.wav
aplay test.wav
```

**If audio does not play from speakers, troubleshoot before moving to next step**

# Clone and Run Python Script

1. Clone the repo using the following command:

```php
git clone https://github.com/alouderback/HelperBee24
```

1. Navigate to the directory

```php
cd HelperBee24
ls
python3 voiceassistant.py
sudo apt-get install python3 python3-pip
sudo apt-get install portaudio19-dev
nano .env(add all the API keys)
```

1. Install necessary dependencies
2. Run the Python script

## Usage

Once the application is running, HelperBee will listen for the wake word. After detecting the wake word, you can issue commands. The assistant will process the commands and respond accordingly. For follow-up commands, you do not need to repeat the wake word unless there is a period of silence.
