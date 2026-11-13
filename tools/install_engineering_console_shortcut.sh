#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
launcher="$repo_root/tools/launch_engineering_console.sh"
applications_dir="$HOME/.local/share/applications"
desktop_dir="$HOME/Desktop"
desktop_file="$applications_dir/makerspace-engineering-console.desktop"

mkdir -p "$applications_dir" "$desktop_dir"
cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Makerspace Engineering Console
Comment=Hardware test and scale calibration
Exec=/bin/bash "$launcher"
Path="$repo_root"
Icon=utilities-system-monitor
Terminal=true
Categories=Utility;
EOF
chmod +x "$desktop_file"
cp "$desktop_file" "$desktop_dir/Makerspace Engineering Console.desktop"
chmod +x "$desktop_dir/Makerspace Engineering Console.desktop"

echo "Installed desktop shortcut: $desktop_dir/Makerspace Engineering Console.desktop"
