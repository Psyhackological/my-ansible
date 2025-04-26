#!/usr/bin/env bash

set -euo pipefail

vars_location='../vars/main.yaml'

# Extract configs using yq and process with jq
yq eval -o=json '.rustup_cargo_list[] | select(.config != null) | .config' "$vars_location" | 
jq -c 'select(.src != null and .dest != null) | {src, dest}' |
while read -r config; do
    # Extract src and dest
    src=$(echo "$config" | jq -r '.src')
    dest=$(echo "$config" | jq -r '.dest')

    # Create destination directory if it doesn't exist
    mkdir -p "$(dirname "$dest")"

    # Execute rsync command
    echo "Syncing $dest to $src"
    rsync -a "$dest" "$src"
done
