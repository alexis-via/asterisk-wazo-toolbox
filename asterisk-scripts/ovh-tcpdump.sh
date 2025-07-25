#! /bin/sh
# -*- encoding: utf-8 -*-
# Author : Alexis de Lattre <alexis.delattre@akretion.com>
# Lunch tcpdump with the right options to analyse the SIP trafic to OVH

set -x

/usr/bin/tcpdump -n -i eth0 -A -s 0 port 5060 and net 91.121.0.0/16

