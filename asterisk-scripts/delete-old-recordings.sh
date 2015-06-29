#! /bin/sh
# -*- encoding: utf-8 -*-
# Author : Alexis de Lattre <alexis.delattre@akretion.com>
# Small script to delete old recordings

RECPATH=/var/spool/asterisk/monitor
DAYSLIMIT=180

echo "Deleting old recodings... "

find $RECPATH -type f -name "*.wav" -mtime +$DAYSLIMIT -delete

echo "done."
