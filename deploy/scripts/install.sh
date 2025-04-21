#!/usr/bin/env bash
# E‑Ink Weather Display — unattended installer for Raspberry Pi OS (Bookworm)
#
# One‑liner:
#   curl -sSL https://raw.githubusercontent.com/sjnims/raspberry-pi-weather-display/main/deploy/scripts/install.sh | bash
#
# The script:
#   • installs Python 3.11 + Poetry (if missing)
#   • creates /opt/rpiweather venv and installs the latest wheel from GitHub Releases
#   • deploys /etc/systemd/system/weather-display.service
#   • applies power‑saving tweaks (CPU 700 MHz, HDMI/Bluetooth/LED off, Wi‑Fi APS‑SD)
#   • reboots once everything is configured
set -euo pipefail

readonly REPO="sjnims/raspberry-pi-weather-display"
readonly VERSION="${VERSION:-latest}"
readonly INSTALL_DIR="/opt/rpiweather"
readonly VENV_DIR="${INSTALL_DIR}/venv"
readonly SERVICE_FILE="/etc/systemd/system/weather-display.service"

info()  { echo -e "\e[32m[install]\e[0m $1"; }
warn()  { echo -e "\e[33m[install]\e[0m $1"; }

###############################################################################
# 1. Ensure Python 3.11 and system packages                                   #
###############################################################################
info "Updating apt & installing base packages"
sudo apt-get update -qq
sudo apt-get install -y python3.11 python3.11-venv git wget wkhtmltopdf cpufrequtils iw

###############################################################################
# 2. Create application user & folders                                        #
###############################################################################
if ! id -u rpiweather &>/dev/null; then
  info "Creating system user 'rpiweather'"
  sudo useradd -r -d "$INSTALL_DIR" -s /usr/sbin/nologin rpiweather
fi

sudo mkdir -p "$INSTALL_DIR"
sudo chown rpiweather:rpiweather "$INSTALL_DIR"

###############################################################################
# 3. Create venv & install the project wheel                                  #
###############################################################################
if [[ ! -d $VENV_DIR ]]; then
  info "Creating virtual-env in $VENV_DIR"
  sudo -u rpiweather python3.11 -m venv "$VENV_DIR"
fi

# Install / upgrade wheel from GitHub Releases
# Fetch latest tag JSON if VERSION=latest
if [[ "$VERSION" == "latest" ]]; then
  TAG=$(wget -qO- "https://api.github.com/repos/${REPO}/releases/latest" | grep -Po '"tag_name": "\K[^"]+')
else
  TAG="$VERSION"
fi

WHEEL_URL="https://github.com/${REPO}/releases/download/${TAG}/rpiweather-${TAG#v}-py3-none-any.whl"

info "Installing rpiweather wheel $TAG"
sudo -u rpiweather "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u rpiweather "$VENV_DIR/bin/pip" install --upgrade "$WHEEL_URL"

###############################################################################
# 4. Deploy systemd unit                                                      #
###############################################################################
cat <<EOF | sudo tee "$SERVICE_FILE" >/dev/null
[Unit]
Description=E-Ink Weather Display
After=network-online.target

[Service]
Type=simple
User=rpiweather
ExecStart=$VENV_DIR/bin/weather run --config /home/rpiweather/config.yaml
Restart=on-failure
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable weather-display.service

###############################################################################
# 5. Power‑saving tweaks                                                      #
###############################################################################
CONFIG=/boot/config.txt
apply_once() { grep -qF "$1" "$CONFIG" || echo "$1" | sudo tee -a "$CONFIG" >/dev/null; }

info "Applying power-saving tweaks"
apply_once "# Weather display power tweaks"
apply_once "arm_freq=700"
apply_once "dtparam=hdmi_force_hotplug=0"
apply_once "dtoverlay=disable-bt"
apply_once "dtparam=act_led_trigger=none"
apply_once "dtparam=act_led_activelow=on"
apply_once "dtparam=pwr_led_trigger=none"
apply_once "dtparam=pwr_led_activelow=on"

echo 'GOVERNOR="powersave"' | sudo tee /etc/default/cpufrequtils >/dev/null
sudo systemctl enable --now cpufrequtils.service

info "Enabling Wi-Fi APS-SD power-save"
cat <<'EOF' | sudo tee /etc/systemd/system/wifi-powersave.service >/dev/null
[Unit]
Description=Enable WiFi APS-SD power save
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

###############################################################################
# 6. Done                                                                     #
###############################################################################
info "Installation complete. Rebooting…"
sudo reboot