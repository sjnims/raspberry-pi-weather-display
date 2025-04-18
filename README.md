# Raspberry Pi E‑Ink Weather Display

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
* Full OpenWeather One Call 3.0 ingestion
* Jinja2 HTML → PNG via `wkhtmltoimage`, GC16 greyscale display.
* **Error visualization** – API failures display a clear error message on the e-ink screen, showing error details, time of last attempt, and battery status.

---

## Hardware

| Item              | Model / Notes                                                      |
|-------------------|--------------------------------------------------------------------|
| Compute           | **Raspberry Pi Zero 2 W**                                          |
| E‑paper display   | **Waveshare 10.3″ 1872 × 1404 IT8951 HAT** (SKU 18434)             |
| Power / UPS       | **PiJuice Zero** plus **PiJuice 12 000 mAh Li‑Po** battery         |
| Storage           | 8 GB + micro‑SD card (Raspberry Pi OS Lite)                        |
| Frame             | Deep‑set picture frame with 10.5‑inch mat opening (optional)       |

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

*Note that config.yaml exists only on your local machine/Pi and is ignored by Git.*

---

## Quick Start

```bash
ssh YOUR-USERNAME@YOUR-PI-IP
curl -sSL https://raw.githubusercontent.com/sjnims/raspberry-pi-weather-display/main/system/scripts/install.sh | bash

# The script creates .venv in ~/weather-display and installs all deps there.
# Logs & service remain identical; to activate venv manually for local testing:
source ~/weather-display/.venv/bin/activate
```

*Be sure to replace `YOUR-USERNAME` and `YOUR-PI-IP` with your actual Raspberry Pi's SSH username and IP address/hostname.*

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

## Local Preview while Developing

You can render the dashboard **locally** on your Mac/PC without touching the Pi. This speeds up template/CSS tweaks:

```bash
# one‑shot preview (opens the rendered HTML in your default browser)
python main.py --config config.yaml --preview --once
```

### Live‑reload (optional)
If you installed `watchdog` (in `requirements‑dev.txt`) run:

```bash
watchmedo shell-command \
  --patterns="*.html;*.css;*.py" \
  --recursive \
  --command='python main.py --config config.yaml --preview --once'
```

Every save automatically refreshes the browser tab—no Flask required.

---

## Manual Update

```bash
ssh YOUR-USERNAME@YOUR-PI-IP 'git -C ~/weather-display pull --ff-only && sudo systemctl restart weather-display'
```

*Be sure to replace `YOUR-USERNAME` and `YOUR-PI-IP` with your actual Raspberry Pi's SSH username and IP address/hostname.*
*Note: `git pull` will not overwrite your local `config.yaml` file.*

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

* `lat` and `lon` are your location's latitude and longitude (see [OpenWeather](https://openweathermap.org/) for details).
* `api_key` is your OpenWeather API key (see [OpenWeather](https://home.openweathermap.org/users/sign_up) for details).
* `units` is either `imperial` or `metric`.
* `time_24h` is either `true` or `false` (24‑hour clock).
* `hourly_count` is the number of hourly forecast hours to display (default **8**).
* `daily_count` is the number of daily forecast days to display (default **5**).
* `city` is the name of your city (for display purposes only).
* `refresh_minutes` is the base refresh interval in minutes (default **120**). This automatically scales based on battery level:
  * Above 50%: 1× (normal refresh rate)
  * 26-50%: 1.5× slower
  * 16-25%: 2× slower
  * 6-15%: 3× slower
  * 0-5%: 4× slower

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

## Credits

* Weather data © [OpenWeather](https://openweathermap.org/)
* Icons © [Erik Flowers](https://github.com/erikflowers/weather-icons)
* Typeface: [Atkinson Hyperlegible](https://brailleinstitute.org/freefont)
* Waveshare IT8951 driver © Waveshare

---

## Inspiration

* Kimmo Brunfeldt's [blog post](https://kimmo.blog/posts/7-building-eink-weather-display-for-our-home/) and [GitHub repository](https://github.com/kimmobrunfeldt/eink-weather-display)
* Faith Ak's InkyPi [YouTube video](https://www.youtube.com/watch?v=65sda565l9Y) and [GitHub repository](https://github.com/FaithAk/InkyPi)

---

## License

MIT License – see [LICENSE](LICENSE).