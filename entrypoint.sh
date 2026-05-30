#!/bin/sh

openvpn --daemon ovpn \
        --status /tmp/openvpn.status \
        --log-append /app/logs/openvpn.log \
        --config /etc/openvpn/autodownloader.conf

for i in $(seq 1 60); do
    if ip route show | grep tun0; then
        echo "OpenVPN connected"
        break
    fi
    sleep 1
done

exec "$@"
