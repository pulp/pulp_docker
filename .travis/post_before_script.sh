#!/usr/bin/env sh

echo "machine localhost
login admin
password password

machine 127.0.0.1
login admin
password password
" > ~/.netrc

$CMD_PREFIX bash -c "dnf install -y openssl"
$CMD_PREFIX bash -c "openssl ecparam -genkey -name prime256v1 -noout -out /var/lib/pulp/tmp/private.key"
$CMD_PREFIX bash -c "openssl ec -in /var/lib/pulp/tmp/private.key -pubout -out /var/lib/pulp/tmp/public.key"
