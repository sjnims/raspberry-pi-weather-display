# Raspberry Pi E‑Ink Weather Display

A self‑contained Python 3 application that turns a **Raspberry Pi Zero 2 W** and a **Waveshare 10.3″ IT8951 e‑paper HAT** into an ultra‑low‑power framed weather dashboard.

---

## Key features

* **Adaptive refresh logic** – the base interval in `config.yaml` (default **120 min**) automatically scales based on battery SoC: refresh slows as the battery drains.
* **Circuit breaker** – backs off × 4 after 3 consecutive API failures.
* **Daily full white‑black‑white refresh** removes any ghosting.
* **PiJuice RTC** set on first network sync each boot.
* **PiJuice UPS** with **12 000 mAh** LiPo battery
* `/var/log` & `/tmp` mounted on **tmpfs** (longer SD life, saves ≈ 1–2 mA).
* **Wi‑Fi APS‑SD**; HDMI, Bluetooth, LEDs disabled; CPU powersave @ 700 MHz.
* **VCOM = ‑1.45 V** verified at runtime for maximum contrast.
* Automatic power-off between refreshes unless overridden (e.g. via KEEP_AWAKE).
* Docker-compatible control interface via environment variable for remote preview/dev control.
* Automatic shutdown during quiet hours or low battery to conserve energy.
* Battery icon dynamically updates with SoC and charging state.
* Full OpenWeather One Call 3.0 ingestion
* Jinja2 HTML → PNG via `wkhtmltoimage`, GC16 greyscale display.
* **Error visualization** – API failures display a clear error message on the e-ink screen, showing error details, time of last attempt, and battery status.
* The weather API response is parsed into a typed Pydantic v2 model (`WeatherResponse`) for safe downstream access in both code and templates.
* Accurate SVG weather icons mapped from OpenWeather condition IDs (with day/night variants), powered by Weather Icons.
* Optimized e-ink rendering modes (GC16 for full refresh, partial updates for speed and battery savings).
* Preview mode renders to HTML and PNG without updating the e-ink display — useful for testing layouts or data.
* **Pure‑Python SVG sprite build** – no Node or npm required; run one script to regenerate `sprite.svg`.

A Typer‑based CLI (`weather`) replaces the old `python main.py` entry‑point: run `weather --help` for commands.

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

## Docker Integration

The weather display service can be controlled externally using a Docker container or orchestrator by setting the environment variable:

```bash
KEEP_AWAKE=1
```

When this variable is present, the system will skip auto power-off and remain awake for debugging or remote preview mode.

---

## Quick Start

```bash
ssh YOUR-USERNAME@YOUR-PI-IP
curl -sSL https://raw.githubusercontent.com/sjnims/raspberry-pi-weather-display/main/deploy/scripts/install.sh | bash

# The script installs Poetry and creates a `.venv` inside the project directory.
# To activate the virtual environment manually for local testing:
cd ~/raspberry-pi-weather-display
poetry shell
```

*Be sure to replace `YOUR-USERNAME` and `YOUR-PI-IP` with your actual Raspberry Pi's SSH username and IP address/hostname.*

The installer will:

* Clones the repository and installs dependencies via Poetry
* Enable `weather-display.service`
* Disable HDMI, Bluetooth, ACT/PWR LEDs
* Cap CPU @ 700 MHz powersave
* Enable Wi‑Fi APS‑SD
* Mount `/var/log` and `/tmp` on tmpfs
* Reboot

After reboot the display updates every **2 h** (less as SoC decreases beyond certain thresholds, see config below).

---

## Local Preview (HTML + PNG)

You can render the dashboard **locally** on your Mac/PC without touching the Pi. This speeds up template/CSS tweaks:

```bash
# one‑shot preview
poetry run weather run --config config.yaml --preview --once
```

### Live‑reload (optional)

If you installed `watchdog` (in `requirements‑dev.txt`) run:

```bash
watchmedo shell-command \
  --patterns="*.html;*.css;*.py" \
  --recursive \
  --command='poetry run weather run --config config.yaml --preview --once'
```

Every save automatically refreshes the browser tab—no Flask required.

### Regenerate icon sprite

Whenever you add or edit individual SVG icons, rebuild the consolidated
`sprite.svg` via one command (no Node tool‑chain needed):

```bash
bash deploy/scripts/icons_build.sh
```

The script trims whitespace, converts fills to `currentColor`, and writes
`static/icons/sprite.svg` in one pass. CI runs the same script to keep the
sprite in sync.
---

## Manual Update

```bash
ssh YOUR-USERNAME@YOUR-PI-IP 'cd ~/raspberry-pi-weather-display && git pull --ff-only && poetry install --no-root && sudo systemctl restart weather-display'
```

*Be sure to replace `YOUR-USERNAME` and `YOUR-PI-IP` with your actual Raspberry Pi's SSH username and IP address/hostname.*
*This will update the source code and reinstall dependencies using Poetry. Your local `config.yaml` will not be overwritten.*

---

## Configuration (`config.yaml`)

```yaml
lat: 33.8852
lon: -84.5144
city: Smyrna, GA
api_key: "YOUR_OPENWEATHER_KEY"

units: imperial        # or metric
timezone: "America/New_York" # IANA timezone name
time_format: "%-I:%M %p"       # e.g. 6:04 AM

hourly_count: 8        # forecast hours to display
daily_count: 5         # forecast days

refresh_minutes: 120   # base interval; scales with SoC: 1× above 50%, 4× at 0–5%
```

* `lat` and `lon` are your location's latitude and longitude (see [OpenWeather](https://openweathermap.org/) for details).
* `api_key` is your OpenWeather API key (see [OpenWeather](https://home.openweathermap.org/users/sign_up) for details).
* `units` is either `imperial` or `metric`.
* `timezone` is your IANA timezone name (see [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for details).
* `time_format` is the format for displaying time (see [Python strftime](https://strftime.org/) for details).
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

| Tweak                                  | Approx. Savings |
|----------------------------------------|-----------------|
| HDMI disabled                          | ~25 mA          |
| CPU 700 MHz + powersave                | ~20 mA          |
| Bluetooth off                          | ~6 mA           |
| ACT & PWR LEDs off                     | ~3 mA           |
| Wi‑Fi APS‑SD                           | ~10 mA          |
| tmpfs `/var/log` & `/tmp`              | ~1–2 mA         |
| Auto power-off (between refreshes + quiet hours) | ~15–18 mA  |

With automatic power-off between refreshes and quiet hour shutdown, average current draw is **~6–9 mA** depending on refresh frequency. A full refresh adds ~2 mAh. Runtime on a 12 000 mAh pack:

* 2 refreshes/day → **50–60 days**
* 4–6 refreshes/day → **30–40 days**
* constant idle (no sleep) → **21–23 days**

---

## Credits

* Weather data © [OpenWeather](https://openweathermap.org/)
* Weather Icons © [Erik Flowers](https://github.com/erikflowers/weather-icons)
* Battery icons © [Phosphor Icons](https://phosphoricons.com) – bold style variant
* Typeface: [Atkinson Hyperlegible](https://brailleinstitute.org/freefont)
* Waveshare IT8951 [driver](https://github.com/waveshareteam/IT8951-ePaper) © Waveshare

---

## Inspiration

* Kimmo Brunfeldt's [blog post](https://kimmo.blog/posts/7-building-eink-weather-display-for-our-home/) and [GitHub repository](https://github.com/kimmobrunfeldt/eink-weather-display)
* Faith Ak's InkyPi [YouTube video](https://www.youtube.com/watch?v=65sda565l9Y) and [GitHub repository](https://github.com/FaithAk/InkyPi)

---

## License

MIT License – see [LICENSE](LICENSE).
