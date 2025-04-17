# E‑Ink Weather Display — Final Polished Version

A self‑contained Python 3 application that turns a **Raspberry Pi Zero 2 W** and a **Waveshare 10.3″ IT8951 e‑paper HAT** into an ultra‑low‑power framed weather dashboard.

---

## Key features

* **Config‑driven refresh** – base interval in `config.yaml` (default **120 min**) automatically **doubles when battery SoC < 25 %**.
* **Circuit breaker** – backs off × 4 after 3 consecutive API failures.
* **Daily full white‑black‑white refresh** removes any ghosting.
* **PiJuice RTC** set on first network sync each boot.
* `/var/log` & `/tmp` mounted on **tmpfs** (longer SD life, saves ≈ 1–2 mA).
* **Wi‑Fi APS‑SD**; HDMI, Bluetooth, LEDs disabled; CPU powersave @ 700 MHz.
* **VCOM = ‑1.45 V** verified at runtime for maximum contrast.
* Auto‑darkening battery icon when SoC < 25 %.
* Full OpenWeather One Call 3.0 ingestion, Jinja2 HTML → PNG via `wkhtmltoimage`, GC16 greyscale display.

---

## Directory Tree

```text
weather-display/
├── .gitignore
├── LICENSE
├── README.md
├── config-sample.yaml
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── display/
│   └── epaper.py
├── weather/
│   ├── __init__.py
│   ├── api.py
│   ├── errors.py
│   └── helpers.py
├── templates/
│   └── dashboard.html
├── static/
│   ├── css/
│   │   ├── style.css
│   │   ├── weather-icons-wind.css
│   │   └── weather-icons.css
│   └── fonts/
│       ├── Atkinson-Hyperlegible-Regular-102a.woff2
│       ├── weathericons-regular-webfont.eot
│       ├── weathericons-regular-webfont.svg
│       ├── weathericons-regular-webfont.ttf
│       ├── weathericons-regular-webfont.woff
│       └── weathericons-regular-webfont.woff2
└── system/
    ├── weather-display.service
    └── scripts/
        └── install.sh
```

*(config.yaml exists only on your local machine/Pi and is ignored by Git.)*

---

## Quick Start

```bash
ssh pi@raspberrypi.local
curl -sSL https://raw.githubusercontent.com/YOUR‑GH/weather-display/main/system/scripts/install.sh | bash
```

The installer will:

* Install Python deps & wkhtmltoimage
* Clone this repo to `/home/pi/weather-display`
* Enable `weather-display.service`
* Disable HDMI, Bluetooth, ACT/PWR LEDs
* Cap CPU @ 700 MHz powersave
* Enable Wi‑Fi APS‑SD
* Mount `/var/log` and `/tmp` on tmpfs
* Reboot

After reboot the display updates every **2 h** (4 h when SoC < 25 %).

---

## Configuration (`config.yaml`)

```yaml
lat: 33.8852
lon: -84.5144
city: Smyrna, GA
api_key: "YOUR_OPENWEATHER_KEY"

units: imperial        # or metric
time_24h: false        # true for 24‑hour clock

hourly_count: 8        # forecast hours to display
daily_count: 5         # forecast days

refresh_minutes: 120   # base interval; doubles automatically below 25 % SoC
```

---

## Power‑Saving Summary

| Tweak                          | Savings |
|--------------------------------|---------|
| HDMI disabled                  | ~25 mA  |
| CPU 700 MHz + powersave        | ~20 mA  |
| Bluetooth off                  | ~6 mA   |
| ACT & PWR LEDs off             | ~3 mA   |
| Wi‑Fi APS‑SD                   | ~10 mA  |
| tmpfs `/var/log` & `/tmp`      | ~1–2 mA |

Average idle **≈ 18 mA**; a refresh adds ~2 mAh/day → **≈ 21–23 days** on a 12 000 mAh pack.

---

## Manual Update

```bash
ssh pi@frame.local 'git -C ~/weather-display pull --ff-only && sudo systemctl restart weather-display'
```

---

## Credits

* Weather data © [OpenWeather](https://openweathermap.org/)
* Icons © [Erik Flowers](https://github.com/erikflowers/weather-icons)
* Typeface: [Atkinson Hyperlegible](https://brailleinstitute.org/freefont)
* Waveshare IT8951 driver © Waveshare

MIT License – see `LICENSE`.