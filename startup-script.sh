#!/bin/bash

# Update the system and install required packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y squid apache2-utils curl ufw

# Download Squid configuration
sudo curl -o /etc/squid/squid.conf https://raw.githubusercontent.com/Bhavya031/proxy/refs/heads/main/squid.conf

# Verify Squid configuration
sudo squid -k parse

# Allow Squid default port (3128) through the firewall
sudo ufw allow 3128

# Restart Squid to apply changes
# Enable firewall
sudo ufw --force enable
sudo htpasswd -c -b /etc/squid/passwd bhavya 123
sudo chown proxy:proxy /etc/squid/passwd
sudo chmod 644 /etc/squid/passwd
sudo systemctl restart squid

