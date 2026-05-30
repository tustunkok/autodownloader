#!/bin/sh

openvpn --daemon ovpn \
        --status /tmp/openvpn.status \
        --log-append /logs/openvpn.log \
        --config /etc/openvpn/autodownloader.conf

for i in $(seq 1 60); do
    if ip route show default | grep -q tun0; then
        echo "OpenVPN connected"
        break
    fi
    sleep 1
done

exec "$@"
