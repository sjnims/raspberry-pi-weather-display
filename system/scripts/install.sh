#!/usr/bin/env bash
# Automated installer for the E‑Ink Weather Display with aggressive power‑saving
# tweaks.  Run on a fresh Raspberry Pi OS Lite (Bookworm).
#
#   curl -sSL https://raw.githubusercontent.com/YOUR-GH/weather-display/main/system/scripts/install.sh | bash

set -euo pipefail

REPO=https://github.com/YOUR-GH/weather-display.git
REPO_DIR=/home/pi/weather-display

info()  { echo -e "\e[32m[install]\e[0m $1"; }
warn()  { echo -e "\e[33m[install]\e[0m $1"; }

info "Updating apt & installing base packages"
sudo apt update
sudo apt install -y python3-pip wkhtmltopdf git cpufrequtils iw

info "Cloning repository"
if [[ ! -d $REPO_DIR ]]; then
  git clone "$REPO" "$REPO_DIR"
else
  warn "Repo already present, pulling latest"
  git -C "$REPO_DIR" pull --ff-only
fi

info "Installing Python requirements"
pip install --break-system-packages -r "$REPO_DIR/requirements.txt"

info "Installing systemd service"
sudo cp "$REPO_DIR/system/weather-display.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable weather-display.service

###############################################################################
# Power‑saving tweaks                                                         #
###############################################################################
CONFIG=/boot/config.txt

apply_once() {
  local line=$1
  grep -qF "${line}" "$CONFIG" || echo "$line" | sudo tee -a "$CONFIG" >/dev/null
}

info "Disabling HDMI output (≈25 mA saved)"
apply_once "dtparam=hdmi_force_hotplug=0"

info "Under‑clocking CPU & setting governor to powersave"
apply_once "# Weather display power tweaks"
apply_once "arm_freq=700"
echo 'GOVERNOR="powersave"' | sudo tee /etc/default/cpufrequtils >/dev/null
sudo systemctl enable --now cpufrequtils.service

info "Disabling onboard Bluetooth (≈6 mA)"
apply_once "dtoverlay=disable-bt"

info "Disabling ACT & PWR LEDs (≈3 mA)"
apply_once "dtparam=act_led_trigger=none"
apply_once "dtparam=act_led_activelow=on"
apply_once "dtparam=pwr_led_trigger=none"
apply_once "dtparam=pwr_led_activelow=on"

info "Aggressive Wi‑Fi power save (APS‑SD)"
cat <<'EOF' | sudo tee /etc/systemd/system/wifi-powersave.service >/dev/null
[Unit]
Description=Enable WiFi APS‑SD power save
After=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c '/sbin/iw dev wlan0 set power_save on && /sbin/iw dev wlan0 set ps-mode force'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable wifi-powersave.service

info "Mounting /var/log and /tmp on tmpfs"
grep -q "/var/log tmpfs" /etc/fstab || echo "tmpfs /var/log tmpfs defaults,size=20m 0 0" | sudo tee -a /etc/fstab
grep -q "/tmp tmpfs"     /etc/fstab || echo "tmpfs /tmp     tmpfs defaults,size=50m 0 0" | sudo tee -a /etc/fstab

info "All tweaks applied.  Rebooting…"
sudo reboot