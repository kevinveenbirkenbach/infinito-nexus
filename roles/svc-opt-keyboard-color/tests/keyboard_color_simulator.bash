#!/bin/bash

# Pfad zum Keyboard-Color-Skript
KEYBOARD_COLOR_SCRIPT="$1"
DEVICE_ID="$2"

# NTP deaktivieren
timedatectl set-ntp false

# Startzeit speichern
START_TIME=$(date +%s)

# 2 Minuten (120 Sekunden) für den gesamten Tag simulieren
for i in {0..60}; do
    # Berechnung der aktuellen simulierten Zeit
    CURRENT_TIME=$((START_TIME + (( 86400 / 60 ) * i )))

    # Systemzeit auf die simulierte Zeit setzen
    date +%s -s "@$CURRENT_TIME"

    # Keyboard-Color-Skript ausführen
    python $KEYBOARD_COLOR_SCRIPT $DEVICE_ID

    # 2 Sekunden Pause
    sleep 2
done

# NTP wieder aktivieren
timedatectl set-ntp true