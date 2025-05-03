# Raspberry Pi E‑Ink Weather Display

A self‑contained Python 3 application that transforms a **Raspberry Pi Zero 2 W** and a **Waveshare e‑paper HAT** into an ultra‑low‑power framed weather dashboard, capable of running for **50-60 days** on a single battery charge.

---

## Key features

### Display & Weather Data
* Full OpenWeather One Call API integration with beautiful e-ink optimized design
* Customizable time and date formats for all dashboard elements
* Accurate weather icons with day/night variants based on sun position

### Power Efficiency
* **Ultra-low power consumption** - 50-60 days runtime on a single charge
* Adaptive refresh rates based on battery level
* Automatic sleep between refreshes with environment variable override

### Developer Experience
* Preview mode for rapid development on any computer
* Comprehensive test suite with GitHub Actions CI integration
* Typed data models ensuring consistent access and rendering

---

## Hardware Requirements

| Item              | Model / Notes                                                      |
|-------------------|--------------------------------------------------------------------|
| Compute           | **Raspberry Pi Zero 2 W**                                          |
| E‑paper display   | **Waveshare 10.3″ 1872 × 1404 IT8951 HAT** (SKU 18434)             |
| Power / UPS       | **PiJuice Zero** plus **PiJuice 12 000 mAh Li‑Po** battery         |
| Storage           | 8 GB + micro‑SD card (Raspberry Pi OS Lite)                        |
| Frame             | Deep‑set picture frame with 10.5‑inch mat opening (optional)       |

---

## Power Optimizations

| Tweak                                  | Approx. Savings |
|----------------------------------------|-----------------|
| HDMI disabled                          | ~25 mA          |
| CPU 700 MHz + powersave                | ~20 mA          |
| Bluetooth off                          | ~6 mA           |
| ACT & PWR LEDs off                     | ~3 mA           |
| Wi‑Fi APS‑SD                           | ~10 mA          |
| tmpfs `/var/log` & `/tmp`              | ~1–2 mA         |
| Auto power-off (between refreshes + quiet hours) | ~15–18 mA  |

**Average current draw: ~6–9 mA** depending on refresh frequency.

Battery life estimates (12,000 mAh battery):

2 refreshes/day → **50–60 days**
4–6 refreshes/day → **30–40 days**
constant idle (no sleep) → **21–23 days**

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

This installer:

* Clones the repository and installs dependencies via Poetry
* Enables systemd service for automatic startup
* Applies power-saving optimizations (HDMI, Bluetooth, LEDs off)
* Caps CPU @ 700 MHz in powersave mode
* Configures Wi‑Fi power saving
* Sets up RAM-based logging
* Reboots the system to apply changes

After reboot the display updates every **2 h** (less as SoC decreases beyond certain thresholds, see config below).

---

## Update existing Installation

```bash
ssh YOUR-USERNAME@YOUR-PI-IP 'cd ~/raspberry-pi-weather-display && git pull --ff-only && poetry install --no-root && sudo systemctl restart weather-display'
```

*Be sure to replace `YOUR-USERNAME` and `YOUR-PI-IP` with your actual Raspberry Pi's SSH username and IP address/hostname.*
*This will update the source code and reinstall dependencies using Poetry. Your local `config.yaml` will not be overwritten.*

---

## Configuration (`config.yaml`)

```yaml
# Location / API
lat: 33.8852
lon: -84.5144
city: Smyrna, GA
api_key: "YOUR_OPENWEATHER_KEY"

# Units & formatting
units: imperial        # imperial or metric
timezone: "America/New_York"  # e.g. America/New_York

# Time formats
time_format_general: "%-I:%M %p"  # e.g. 6:04 AM
time_format_hourly: "%-I %p"      # e.g. 6 AM
time_format_daily: "%a"           # e.g. Mon
time_format_full_date: "%A, %B %-d"  # e.g. Monday, January 3

# How much forecast data to show
hourly_count: 8        # number of hourly entries (1–48)
daily_count: 5         # number of daily entries (1–7)

# Base refresh cadence (minutes)
# The program adjusts this value based on multiple battery SoC
# thresholds and other system conditions to optimize power consumption.
refresh_minutes: 120
```

* `lat` and `lon` are your location's latitude and longitude (see [OpenWeather](https://openweathermap.org/) for details).
* `city` is the name of your city (for display purposes only).
* `api_key` is your OpenWeather API key (see [OpenWeather](https://home.openweathermap.org/users/sign_up) for details).
* `units` is either `imperial` or `metric`.
* `timezone` is your IANA timezone name (see [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for details).
* `time_format_[general,hourly,daily,full_date]` is the format for displaying dates and time on the dashboard (see [Python strftime](https://strftime.org/) for details).
* `hourly_count` is the number of hourly forecast hours to display (default **8**).
* `daily_count` is the number of daily forecast days to display (default **5**).
* `refresh_minutes` is the base refresh interval in minutes (default **120**). This automatically scales based on battery level:
  * Above 50%: 1× (normal refresh rate)
  * 26-50%: 1.5× slower
  * 16-25%: 2× slower
  * 6-15%: 3× slower
  * 0-5%: 4× slower

---

## Local Preview (HTML + PNG)

You can render the dashboard **locally** on your Mac/PC without touching the Pi. This speeds up template/CSS tweaks:

```bash
# Generate HTML and PNG previews
poetry run weather run --config config.yaml --preview --once

# Start a local server to view the preview
poetry run weather run --config config.yaml --preview --serve
```

---

## Docker Integration

The weather display service can be controlled externally using a Docker container or orchestrator by setting the environment variable:

```bash
KEEP_AWAKE=1
```

When this variable is present, the system will skip auto power-off and remain awake for debugging or remote preview mode. EXPERIMENTAL!
*Note: This feature is still in development and may not work as expected.*

---

## Development

### Continuous Integration

GitHub Actions automatically run on every PR and push to main:

* Code formatting checks (black, isort)
* Type checking (mypy)
* Unit tests (pytest)
* Icon sprite generation

### Regenerate icon sprite

Whenever you add or edit individual SVG icons, rebuild the consolidated
`sprite.svg` via one command (no Node tool‑chain needed):

```bash
bash deploy/scripts/icons_build.sh
```

The script trims whitespace, converts fills to `currentColor`, and writes
`static/icons/sprite.svg` in one pass. CI runs the same script to keep the
sprite in sync.

### Live-reload Development

For rapid development with automatic refresh:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Auto-refresh on file changes
watchmedo shell-command \
  --patterns="*.html;*.css;*.py" \
  --recursive \
  --command='poetry run weather run --config config.yaml --preview --once'
```

---

## Contributing

hank you for considering contributing to this project! Here's how to get started:

1. **Fork the repository**: Click the "Fork" button at the top right of this page to create your own copy of the repository.

2. **Clone the forked repository**: Use the following command to clone your forked repository to your local machine:

   ```bash
   git clone <your-repo-url>
   ```
   Replace `<your-repo-url>` with the URL of your forked repository.

3. **Create a new branch**: Before making any changes, create a new branch for your feature or bug fix:

   ```bash
   git checkout -b my-feature-branch
   ```
   Replace `my-feature-branch` with a descriptive name for your branch.

4. **Make your changes**: Edit the code as needed in your branch.

5. **Test your changes**: Run the tests to ensure everything works as expected:

   ```bash
   ruff check .
   pyright
   poetry run pytest -q
   ```

6. **Commit your changes**: Once you're satisfied with your changes, commit them with a descriptive message:

   ```bash
   git add .
   git commit -m "Add my feature"
   ```

7. **Push your changes**: After committing, push your changes to your forked repository:

   ```bash
   git push origin my-feature-branch
   ```

Replace `my-feature-branch` with the name of your branch.

8. **Create a pull request**: Go to the original repository and click on the "Pull requests" tab. Click the "New pull request" button and select your branch. Provide a clear description of your changes and submit the pull request.

9. **Wait for review**: The project maintainers will review your pull request. They may ask for changes or provide feedback.

---

## Credits

* Weather data © [OpenWeather](https://openweathermap.org/)
* Weather Icons © [Erik Flowers](https://github.com/erikflowers/weather-icons)
* Battery icons © [Phosphor Icons](https://phosphoricons.com) – bold style variant
* Typeface: [Atkinson Hyperlegible Next](https://brailleinstitute.org/freefont)
* Waveshare IT8951 [driver](https://github.com/waveshareteam/IT8951-ePaper) © Waveshare

---

## Inspiration

* Kimmo Brunfeldt's [blog post](https://kimmo.blog/posts/7-building-eink-weather-display-for-our-home/) and [GitHub repository](https://github.com/kimmobrunfeldt/eink-weather-display)
* Faith Ak's InkyPi [YouTube video](https://www.youtube.com/watch?v=65sda565l9Y) and [GitHub repository](https://github.com/FaithAk/InkyPi)

---

## License

MIT License – see [LICENSE](LICENSE).
