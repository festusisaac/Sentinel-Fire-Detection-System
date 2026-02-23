import cv2
import numpy as np
import os
import pygame
import time
import asyncio
import certifi
import json
import threading
from datetime import datetime
from flask import Flask, Response, jsonify, render_template_string, request, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from twilio.rest import Client

# Fix SSL Certificate Error (FileNotFoundError)
# If the environment variable is set to a non-existent file, we unset it or fix it
if "SSL_CERT_FILE" in os.environ:
    # Use certifi's bundle as a reliable fallback
    os.environ["SSL_CERT_FILE"] = certifi.where()

# Initialize Alarm System
pygame.mixer.init(frequency=44100, size=-16, channels=1)

# Telegram Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
# Note: we will initialize the application inside the main async loop
tg_app = None 
bot = Bot(token=BOT_TOKEN)

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "YOUR_TWILIO_SID")   
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "+YOUR_TWILIO_NUMBER")
TO_PHONE_NUMBER = os.getenv("TO_PHONE_NUMBER", "+TARGET_PHONE_NUMBER")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Alert Cooldown Logic
last_telegram_time = 0
TELEGRAM_COOLDOWN = 60 # Send alert at most once every 60 seconds
last_call_time = 0
CALL_COOLDOWN = 300 # Phone call cooldown (5 minutes) to avoid spam
is_sending_alert = False # Prevention for concurrent uploads

# Global State for Web Dashboard
latest_frame = None
system_armed = True
incident_logs = []
LOG_FILE = "logs.json"

# Load existing logs if available
if os.path.exists(LOG_FILE):
    try:
        with open(LOG_FILE, "r") as f:
            incident_logs = json.load(f)
    except:
        incident_logs = []

def save_log(event):
    global incident_logs
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event
    }
    incident_logs.insert(0, log_entry) # Add to start
    # Keep last 50 logs
    incident_logs = incident_logs[:50]
    with open(LOG_FILE, "w") as f:
        json.dump(incident_logs, f, indent=4)

# Flask Application
app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24) # Secure key for sessions
web_password = "admin123" # Default password

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] != web_password:
            error = 'ACCESS DENIED: INVALID CREDENTIALS'
        else:
            session['logged_in'] = True
            save_log("Security: Remote user logged in")
            return redirect(url_for('index'))
            
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SENTINEL | SECURE LOGIN</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap');
            body { 
                background: #050a0f; 
                color: #00f2ff; 
                font-family: 'Outfit', sans-serif; 
                margin: 0; 
                height: 100vh;
                display: flex; 
                justify-content: center;
                align-items: center;
                overflow: hidden;
            }
            .login-box {
                background: rgba(0, 242, 255, 0.05);
                border: 2px solid #00f2ff;
                padding: 40px;
                border-radius: 15px;
                width: 350px;
                text-align: center;
                box-shadow: 0 0 40px rgba(0, 242, 255, 0.2);
                backdrop-filter: blur(10px);
            }
            h2 { margin-bottom: 30px; letter-spacing: 4px; font-weight: 700; }
            input[type="password"] {
                width: 100%;
                padding: 15px;
                margin-bottom: 20px;
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(0, 242, 255, 0.3);
                border-radius: 5px;
                color: #00f2ff;
                font-size: 1rem;
                box-sizing: border-box;
                outline: none;
            }
            input[type="password"]:focus {
                border-color: #00f2ff;
                box-shadow: 0 0 10px rgba(0, 242, 255, 0.5);
            }
            .btn {
                width: 100%;
                background: transparent;
                border: 2px solid #00f2ff;
                color: #00f2ff;
                padding: 15px;
                font-size: 1rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s;
                border-radius: 5px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            .btn:hover {
                background: #00f2ff;
                color: #050a0f;
                box-shadow: 0 0 20px #00f2ff;
            }
            .error { color: #ff0000; margin-top: 20px; font-weight: 700; font-size: 0.8rem; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>SENTINEL</h2>
            <form method="post">
                <input type="password" name="password" placeholder="ENTER ACCESS KEY" required autofocus>
                <button type="submit" class="btn">AUTHENTICATE</button>
            </form>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
        </div>
    </body>
    </html>
    ''', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    save_log("Security: Remote user logged out")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SENTINEL COMMAND CENTER</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap');
            body { 
                background: #050a0f; 
                color: #00f2ff; 
                font-family: 'Outfit', sans-serif; 
                margin: 0; 
                display: flex; 
                flex-direction: column; 
                align-items: center;
                overflow-x: hidden;
            }
            .header {
                width: 100%;
                padding: 20px;
                background: rgba(0, 242, 255, 0.05);
                border-bottom: 2px solid #00f2ff;
                text-align: center;
                box-shadow: 0 0 20px rgba(0, 242, 255, 0.2);
            }
            .main-container {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 30px;
                padding: 40px;
                max-width: 1200px;
            }
            .feed-container {
                position: relative;
                border: 3px solid #00f2ff;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 0 30px rgba(0, 242, 255, 0.3);
                background: #000;
            }
            .feed-container img {
                display: block;
                max-width: 100%;
                height: auto;
            }
            .controls-panel {
                background: rgba(0, 242, 255, 0.05);
                border: 1px solid #00f2ff;
                padding: 30px;
                border-radius: 10px;
                width: 320px;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 15px;
                font-size: 1.2rem;
                font-weight: 700;
            }
            .dot {
                width: 15px;
                height: 15px;
                border-radius: 50%;
                background: #ff0000;
                box-shadow: 0 0 10px #ff0000;
            }
            .dot.online {
                background: #00ff00;
                box-shadow: 0 0 10px #00ff00;
            }
            .btn {
                background: transparent;
                border: 2px solid #00f2ff;
                color: #00f2ff;
                padding: 15px;
                font-size: 1rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s;
                border-radius: 5px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            .btn:hover {
                background: #00f2ff;
                color: #050a0f;
                box-shadow: 0 0 20px #00f2ff;
            }
            .logs-panel {
                width: 100%;
                background: rgba(0, 242, 255, 0.03);
                border: 1px solid rgba(0, 242, 255, 0.2);
                padding: 20px;
                border-radius: 10px;
                max-height: 300px;
                overflow-y: auto;
            }
            .log-entry {
                padding: 10px;
                border-bottom: 1px solid rgba(0, 242, 255, 0.1);
                font-size: 0.9rem;
            }
            .log-time { color: #888; margin-right: 15px; }
            .log-msg { color: #ff5500; font-weight: 700; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>SENTINEL COMMAND CENTER</h1>
        </div>
        <div class="main-container">
            <div class="feed-container">
                <img src="/video_feed" alt="Video Feed">
            </div>
            <div class="controls-panel">
                <div class="status-indicator">
                    <div id="statusDot" class="dot"></div>
                    <span id="statusText">SYSTEM STATUS</span>
                </div>
                <button class="btn" onclick="toggleArm()">Toggle Arm System</button>
                <div class="logs-panel" id="logsContainer">
                    <!-- Logs will be injected here -->
                </div>
            </div>
        </div>
        <script>
            async function updateStatus() {
                const response = await fetch('/status');
                const data = await response.json();
                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusText');
                if (data.armed) {
                    dot.classList.add('online');
                    text.innerText = "SYSTEM ARMED";
                    text.style.color = "#00ff00";
                } else {
                    dot.classList.remove('online');
                    text.innerText = "SYSTEM DISARMED";
                    text.style.color = "#ff0000";
                }
                
                const logResponse = await fetch('/logs');
                const logs = await logResponse.json();
                const container = document.getElementById('logsContainer');
                container.innerHTML = '<h3>INCIDENT LOGS</h3>';
                logs.forEach(log => {
                    container.innerHTML += `<div class="log-entry">
                        <span class="log-time">${log.timestamp}</span>
                        <span class="log-msg">${log.event}</span>
                    </div>`;
                });
            }
            
            async function toggleArm() {
                await fetch('/toggle', { method: 'POST' });
                updateStatus();
            }
            
            setInterval(updateStatus, 1000);
            updateStatus();
        </script>
    </body>
    </html>
    ''')

@app.route('/video_feed')
@login_required
def video_feed():
    def gen():
        while True:
            if latest_frame is not None:
                ret, buffer = cv2.imencode('.jpg', latest_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.04) # Limit to ~25fps
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
@login_required
def get_status():
    return jsonify({"armed": system_armed})

@app.route('/toggle', methods=['POST'])
@login_required
def toggle_arm():
    global system_armed
    system_armed = not system_armed
    save_log(f"System {'ARMED' if system_armed else 'DISARMED'} remotely")
    return jsonify({"armed": system_armed})

@app.route('/logs')
@login_required
def get_logs():
    return jsonify(incident_logs)

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

# Start Flask in a background thread
web_thread = threading.Thread(target=run_flask, daemon=True)
web_thread.start()

# Initial log
save_log("Sentinel System Online - Command Center Ready")

# --- Telegram Command Handlers ---
async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global latest_frame
    if str(update.effective_chat.id) != CHAT_ID: return
    
    await update.message.reply_text("🔎 CAPTURING SENTINEL VISION...")
    if latest_frame is not None:
        temp_path = "tg_status_request.jpg"
        cv2.imwrite(temp_path, latest_frame)
        with open(temp_path, "rb") as photo:
            await context.bot.send_photo(chat_id=CHAT_ID, photo=photo, 
                                       caption=f"🛡️ STATUS: {'ARMED' if system_armed else 'DISARMED'}\n🕒 {datetime.now().strftime('%H:%M:%S')}")
        if os.path.exists(temp_path): os.remove(temp_path)
    else:
        await update.message.reply_text("❌ ERROR: VISION FEED UNAVAILABLE")

async def tg_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global system_armed
    if str(update.effective_chat.id) != CHAT_ID: return
    system_armed = False
    save_log("Security: System DISARMED via Telegram")
    await update.message.reply_text("🔇 ALARM MUTED. SYSTEM DISARMED.")

async def tg_arm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global system_armed
    if str(update.effective_chat.id) != CHAT_ID: return
    system_armed = True
    save_log("Security: System ARMED via Telegram")
    await update.message.reply_text("🔋 SYSTEM ARMED. SENTINEL ONLINE.")

async def tg_disarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await tg_mute(update, context)

async def trigger_voice_call():
    """Initiates an emergency voice call via Twilio."""
    global last_call_time
    try:
        print(f"--- Initiating Emergency Voice Call to {TO_PHONE_NUMBER} ---")
        # Update timestamp before calling to prevent race conditions
        last_call_time = time.time()
        
        call = twilio_client.calls.create(
            twiml='<Response><Say voice="alice">Emergency! Fire detected at your location by the Sentinel system. Please check your system immediately!</Say></Response>',
            to=TO_PHONE_NUMBER,
            from_=TWILIO_FROM_NUMBER
        )
        print(f"Voice call initiated. SID: {call.sid}")
    except Exception as e:
        if "21215" in str(e) or "international permissions" in str(e).lower():
            print(f"CRITICAL ERROR: Twilio Geo-Permission blocked the call to {TO_PHONE_NUMBER}.")
            print("👉 Please enable Nigeria (+234) permissions here: https://console.twilio.com/us1/develop/voice/settings/geo-permissions")
        else:
            print(f"Failed to initiate voice call: {e}")
        last_call_time = 0 # Reset on failure to allow retry

async def send_telegram_photo(image):
    """Sends a photo to the Telegram bot."""
    global last_telegram_time, is_sending_alert
    
    if is_sending_alert:
        return
        
    is_sending_alert = True
    try:
        # Update timestamp immediately to block other tasks
        last_telegram_time = time.time()
        
        # Save frame temporarily
        temp_path = "fire_alert.jpg"
        cv2.imwrite(temp_path, image)
        
        print(f"--- Sending Telegram Alert to {CHAT_ID} ---")
        # Send via Bot
        with open(temp_path, "rb") as photo:
            await bot.send_photo(chat_id=CHAT_ID, photo=photo, caption="🔥 ALERT: FIRE DETECTED by Sentinel!")
        
        print("Telegram alert sent successfully.")
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        # Reset cooldown on failure so it can retry sooner if it's a transient error
        if "Chat not found" in str(e):
            print(f"CRITICAL ERROR: Telegram Chat ID {CHAT_ID} not found. Did you message the bot first?")
        else:
            print(f"Failed to send Telegram alert: {e}")
        last_telegram_time = 0 
    finally:
        is_sending_alert = False

def generate_beep(duration=1.0, frequency=1000, volume=0.5):
    """Generates a simple beep sound using numpy."""
    sample_rate = 44100
    n_samples = int(duration * sample_rate)
    # Generate a sine wave
    t = np.linspace(0, duration, n_samples, False)
    wave = np.sin(2 * np.pi * frequency * t) * volume * 32767
    wave = wave.astype(np.int16)
    
    # Check if mixer is stereo and adjust array dimensions
    mixer_info = pygame.mixer.get_init()
    if mixer_info and mixer_info[2] > 1: # channels > 1
        wave = np.repeat(wave[:, np.newaxis], 2, axis=1) # Make it 2D for stereo
        
    return pygame.sndarray.make_sound(wave)

# Prepare the fallback alarm sound
try:
    alarm_sound = generate_beep(duration=0.5, frequency=1500, volume=0.7)
except Exception as e:
    print(f"Warning: Could not generate synth alarm: {e}")
    alarm_sound = None

alarm_playing = False
last_alarm_time = 0
fire_persistence_counter = 0
PERSISTENCE_THRESHOLD = 7 # Number of consecutive frames needed to trigger alarm

def draw_hud(img, fire_detected):
    height, width, _ = img.shape
    
    # Corner Brackets
    length = 50
    thickness = 2
    color = (0, 255, 255) # Cyan HUD color
    
    # Top Left
    cv2.line(img, (20, 20), (20 + length, 20), color, thickness)
    cv2.line(img, (20, 20), (20, 20 + length), color, thickness)
    # Top Right
    cv2.line(img, (width - 20, 20), (width - 20 - length, 20), color, thickness)
    cv2.line(img, (width - 20, 20), (width - 20, 20 + length), color, thickness)
    # Bottom Left
    cv2.line(img, (20, height - 20), (20 + length, height - 20), color, thickness)
    cv2.line(img, (20, height - 20), (20, height - 20 - length), color, thickness)
    # Bottom Right
    cv2.line(img, (width - 20, height - 20), (width - 20 - length, height - 20), color, thickness)
    cv2.line(img, (width - 20, height - 20), (width - 20, height - 20 - length), color, thickness)

    # Status Text
    status_text = "SCANNING SYSTEM READY"
    status_color = (0, 255, 255)
    
    if fire_detected:
        status_text = "CRITICAL: FIRE DETECTED"
        status_color = (0, 0, 255) # Red for danger
        # Flashing Overlay effect
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.2, img, 0.8, 0, img)

    cv2.putText(img, f"STATUS: {status_text}", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    cv2.putText(img, "PROTOCOL: THERMAL/COLOUR FILTRATION", (40, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

async def detect_fire():
    global last_alarm_time, alarm_playing, fire_persistence_counter, last_telegram_time, last_call_time, latest_frame, tg_app
    
    # Initialize Telegram Application for 2-way comms
    print("--- Initializing Telegram 2-Way Protocol ---")
    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("status", tg_status))
    tg_app.add_handler(CommandHandler("mute", tg_mute))
    tg_app.add_handler(CommandHandler("arm", tg_arm))
    tg_app.add_handler(CommandHandler("disarm", tg_disarm))
    
    # Start polling in background
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    print("--- Telegram Listener: ACTIVE ---")

    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("--- Sentinel Active: Armed for Web Control & Streaming ---")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        height, width, _ = frame.shape

        # Convert to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Balanced Fire Detection Logic
        # Primary Range: Vibrant Orange/Yellow
        lower_fire = np.array([0, 110, 200], dtype="uint8")
        upper_fire = np.array([35, 255, 255], dtype="uint8")
        mask_fire = cv2.inRange(hsv, lower_fire, upper_fire)
        
        # Secondary Range: Deep Red Fire
        lower_red = np.array([160, 110, 200], dtype="uint8")
        upper_red = np.array([179, 255, 255], dtype="uint8")
        mask_red = cv2.inRange(hsv, lower_red, upper_red)
        
        # Combine both ranges
        mask = cv2.bitwise_or(mask_fire, mask_red)
        
        # Apply morphological operations
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        instant_fire_detected = False
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 100: 
                instant_fire_detected = True
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(frame, "THERMAL SIGNATURE", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Persistence Logic
        if instant_fire_detected and system_armed:
            fire_persistence_counter = min(PERSISTENCE_THRESHOLD * 2, fire_persistence_counter + 2)
        else:
            fire_persistence_counter = max(0, fire_persistence_counter - 1)

        fire_detected = fire_persistence_counter >= PERSISTENCE_THRESHOLD

        # Trigger Alarm and Alerts
        if fire_detected and system_armed:
            # Audible Alarm
            current_time = time.time()
            if current_time - last_alarm_time > 0.6:
                if alarm_sound:
                    alarm_sound.play()
                last_alarm_time = current_time
            
            # Telegram Alert (Asynchronous)
            if current_time - last_telegram_time >= TELEGRAM_COOLDOWN:
                save_log("FIRE INCIDENT: Telegram alert dispatched")
                asyncio.create_task(send_telegram_photo(frame.copy()))

            # Twilio Voice Call (Asynchronous)
            if current_time - last_call_time >= CALL_COOLDOWN:
                save_log("CRITICAL: Emergency voice call initiated")
                asyncio.create_task(trigger_voice_call())

        # Update HUD overlays
        draw_hud(frame, fire_detected)
        
        # Status Label for HUD (Bottom Right, Sleeker)
        hud_status = "ARMED" if system_armed else "DISARMED"
        hud_color = (0, 255, 0) if system_armed else (0, 0, 255)
        cv2.putText(frame, f"WEB INTERFACE: {hud_status}", (width - 220, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, hud_color, 1)

        # Update latest frame for web stream
        latest_frame = frame.copy()

        cv2.imshow('Antigravity Fire Sentinel - V1.1 (Standard)', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        await asyncio.sleep(0.01)

    # Shutdown bot polling
    if tg_app:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(detect_fire())
