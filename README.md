# Air Quality Monitoring System — IoT with Cloud Integration

Real-time Air Quality Index (AQI) monitoring system built on Raspberry Pi, measuring 
environmental parameters and streaming data to the cloud via ThingSpeak API for 
live visualization and reporting.

---

## 📡 System Overview

Sensors collect air quality data continuously. The Raspberry Pi processes the readings, 
calculates AQI, and pushes data to ThingSpeak every 30 seconds for remote monitoring 
via dashboard.

---

## 📊 Parameters Monitored

| Parameter | Sensor | Unit |
|---|---|---|
| Particulate Matter (PM2.5) | Dust sensor | µg/m³ |
| Carbon Monoxide (CO) | MQ-7 | ppm |
| Temperature | DHT22 | °C |
| Air Quality Index (AQI) | Calculated | — |

---

## 🛠️ Hardware & Tools

- Raspberry Pi (main controller)
- MQ-7 CO sensor
- DHT22 temperature & humidity sensor
- PM2.5 dust sensor
- Python 3
- ThingSpeak API (cloud storage & visualization)

---

## 📂 File Structure

| File | Description |
|---|---|
| `main.py` | Main loop — reads sensors, calculates AQI, pushes to ThingSpeak |
| `requirements.txt` | Python dependencies |

---

## ▶️ How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run on Raspberry Pi
python main.py
```

---

## 👤 My Contribution

Solo project — designed the full system architecture, wired and configured all sensors 
to Raspberry Pi GPIO, wrote the data acquisition and AQI calculation logic in Python, 
and integrated ThingSpeak API for real-time cloud visualization and alerting.

---

## 🔗 Live Dashboard

*(Add your ThingSpeak channel link here if public)*
