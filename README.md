# Sentinel Fire Detection System

A comprehensive fire detection system that uses computer vision to monitor for fire hazards in real-time. The system features a web-based command center, Telegram bot integration for remote control, automated alerts via SMS and voice calls, and persistent logging of all incidents.

## Features

### Core Detection
- **Real-time Fire Detection**: Uses advanced color-based computer vision algorithms to detect fire signatures in HSV color space
- **Persistence Filtering**: Implements a smart persistence counter to reduce false positives from transient light sources
- **Multi-range Detection**: Detects both vibrant orange/yellow flames and deep red fire signatures

### Alert System
- **Audible Alarms**: Generates synthetic beep sounds using Pygame when fire is detected
- **Telegram Integration**: Sends photo alerts to a configured Telegram chat with real-time snapshots
- **Voice Calls**: Initiates emergency voice calls via Twilio when fire is detected
- **Cooldown Management**: Prevents alert spam with configurable cooldown periods

### Web Interface
- **Live Video Feed**: Streams real-time video from the webcam with HUD overlays
- **Command Center**: Futuristic web dashboard for monitoring and control
- **System Control**: Arm/disarm the system remotely through the web interface
- **Incident Logs**: Real-time display of all system events and alerts
- **Secure Access**: Password-protected login system (default: admin123)

### Remote Control
- **Telegram Bot Commands**:
  - `/status` - Get current system status with live photo
  - `/arm` - Arm the detection system
  - `/disarm` or `/mute` - Disarm the system
- **Web Dashboard**: Full control through responsive web interface

### Logging & Monitoring
- **Persistent Logs**: All events saved to JSON file with timestamps
- **Real-time Updates**: Web interface updates logs and status in real-time
- **Event Tracking**: Logs system arming/disarming, alerts sent, and incidents

## Requirements

### System Requirements
- Python 3.7+
- Webcam/Camera device
- Internet connection (for Telegram and Twilio alerts)
- Audio output (for alarm sounds)

### Python Dependencies
```
opencv-python>=4.1.1
numpy>=1.18.5
pygame>=2.0.0
flask>=2.0.0
flask-cors>=3.0.0
python-telegram-bot>=20.0
twilio>=7.0.0
certifi>=2020.0.0
```

## Installation

1. **Clone or Download** the project files to your local machine

2. **Install Dependencies**:
   ```bash
   pip install opencv-python numpy pygame flask flask-cors python-telegram-bot twilio certifi
   ```

3. **Configure Telegram Bot**:
   - Create a new bot with [@BotFather](https://t.me/botfather) on Telegram
   - Get your BOT_TOKEN
   - Start a chat with your bot and get the CHAT_ID (you can use tools like `@userinfobot`)

4. **Configure Twilio** (for voice calls):
   - Sign up at [Twilio](https://www.twilio.com/)
   - Get your ACCOUNT_SID, AUTH_TOKEN, and phone numbers
   - Enable geo-permissions for your target country if needed

5. **Update Configuration** in `detector.py`:
   ```python
   BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
   CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
   
   TWILIO_ACCOUNT_SID = "YOUR_TWILIO_SID"
   TWILIO_AUTH_TOKEN = "YOUR_TWILIO_TOKEN"
   TWILIO_FROM_NUMBER = "+YOUR_TWILIO_NUMBER"
   TO_PHONE_NUMBER = "+TARGET_PHONE_NUMBER"
   ```

## Usage

### Running the System

1. **Start the Detector**:
   ```bash
   python detector.py
   ```

2. **Access Web Interface**:
   - Open your browser and go to `http://localhost:5000`
   - Login with password: `admin123` (change this in the code for security)

3. **Monitor and Control**:
   - View live video feed with HUD overlays
   - Check system status and incident logs
   - Arm/disarm the system as needed

### Telegram Control

Send commands to your bot:
- `/status` - Receive current system status with photo
- `/arm` - Arm the fire detection system
- `/disarm` - Disarm the system

### System Operation

- The system starts armed by default
- When fire is detected, it will:
  - Sound audible alarms
  - Send Telegram photo alerts (every 60 seconds max)
  - Make emergency voice calls (every 5 minutes max)
  - Log all incidents
- Use the web interface or Telegram to arm/disarm as needed

## Configuration Options

### Detection Parameters
- `PERSISTENCE_THRESHOLD = 7` - Frames needed to confirm fire detection
- `TELEGRAM_COOLDOWN = 60` - Minimum seconds between Telegram alerts
- `CALL_COOLDOWN = 300` - Minimum seconds between voice calls

### Web Interface
- `web_password = "admin123"` - Change default password
- Server runs on `host='0.0.0.0', port=5000`

### Alarm Settings
- Alarm frequency: 1500 Hz
- Alarm duration: 0.5 seconds
- Alarm volume: 0.7

## File Structure

```
FireDetector/
├── detector.py              # Main detection script
├── fire.pt                  # YOLO model (reference/included)
├── logs.json                # Incident logs
├── assets/                  # Static assets (if any)
├── FireDetectionYOLOv8-main/ # YOLOv8 implementation (reference)
└── README.md               # This file
```

## Troubleshooting

### Common Issues

1. **Webcam Not Detected**:
   - Ensure your camera is connected and not used by other applications
   - Check camera permissions on your system

2. **Telegram Alerts Not Working**:
   - Verify BOT_TOKEN and CHAT_ID are correct
   - Make sure you've started a chat with your bot first
   - Check internet connection

3. **Twilio Calls Failing**:
   - Verify account credentials and phone numbers
   - Check Twilio geo-permissions for target country
   - Ensure sufficient Twilio credits

4. **Audio Alarms Not Playing**:
   - Check audio output device
   - Verify Pygame mixer initialization

5. **Web Interface Not Loading**:
   - Ensure port 5000 is not blocked
   - Check firewall settings
   - Verify Flask is running

### Logs and Debugging

- Check `logs.json` for system events
- Console output shows detailed error messages
- Telegram bot status is logged on startup

## Security Notes

- Change the default web password before deployment
- Keep API tokens and credentials secure
- Consider running on a local network for web access
- The system includes SSL certificate fixes for network requests

## Included YOLOv8 Implementation

The project includes a `FireDetectionYOLOv8-main/` folder containing a YOLOv8-based fire detection implementation for reference. This uses deep learning for more accurate detection but requires GPU resources and model training. The main script uses a lightweight color-based approach for broader compatibility.

## License

This project is provided as-is for educational and security purposes. Please ensure compliance with local laws and regulations regarding surveillance and emergency alert systems.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the system.

## Disclaimer

This system is designed for fire detection assistance but should not replace professional fire safety equipment or monitoring services. Always test thoroughly in your environment and have backup safety measures in place.</content>
<parameter name="filePath">c:\Users\Hp\Desktop\FireDetector\README.md