#!/usr/bin/env bash
iptables -I INPUT -m tcp -p tcp -m multiport --dports 443,8443 -d 192.168.42.0/24 -j ACCEPT
iptables -I FORWARD -m tcp -p tcp -m multiport --dports 443,8443 -d 192.168.42.0/24 -j ACCEPT
iptables -I FORWARD -s 192.168.42.0/24 -j ACCEPT
