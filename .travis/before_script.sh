#!/usr/bin/env sh
set -v

psql -U postgres -c 'CREATE USER pulp WITH SUPERUSER LOGIN;'
psql -U postgres -c 'CREATE DATABASE pulp OWNER pulp;'

mkdir -p ~/.config/pulp_smash
cp ../pulp/.travis/pulp-smash-config.json ~/.config/pulp_smash/settings.json

sudo mkdir -p /var/lib/pulp/tmp
sudo mkdir /var/cache/pulp
sudo mkdir /etc/pulp/
sudo chown -R travis:travis /var/lib/pulp
sudo chown travis:travis /var/cache/pulp

sudo cp ../pulp/.travis/server.yaml /etc/pulp/server.yaml

echo "SECRET_KEY: \"$(cat /dev/urandom | tr -dc 'a-z0-9!@#$%^&*(\-_=+)' | head -c 50)\"" | sudo tee -a /etc/pulp/server.yaml
