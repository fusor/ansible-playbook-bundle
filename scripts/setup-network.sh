#!/usr/bin/env bash
MINISHIFT_SUBNET=${MINISHIFT_SUBNET:-192.168.42.0/24}

echo "Adding iptables rules for minishift subnet: ${MINISHIFT_SUBNET}"

if ! [[ $(id -u) = 0 ]]; then
  echo "ERROR: Must run setup-network.sh as root!"
  exit 1
fi

iptables -I INPUT -m tcp -p tcp -m multiport --dports 443,8443 -d ${MINISHIFT_SUBNET} -j ACCEPT
iptables -I FORWARD -m tcp -p tcp -m multiport --dports 443,8443 -d ${MINISHIFT_SUBNET} -j ACCEPT
iptables -I FORWARD -s ${MINISHIFT_SUBNET} -j ACCEPT
