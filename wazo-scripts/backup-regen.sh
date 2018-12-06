#! /bin/sh
# -*- encoding: utf-8 -*-
# Author : Alexis de Lattre <alexis.delattre@akretion.com>
# Small script to regenerate Xivo backups
# Backups can then be downloaded from the Web administration interface
# from the menu "Services > IPBX > Backup files"

echo -n "Starting to generate backup data-manual... "

xivo-backup data /var/backups/xivo/data-manual

echo "done."

echo -n "Starting to generate backup db-manual... "

xivo-backup db /var/backups/xivo/db-manual

echo "done."

echo "You can now get the archives from the Web interface, menu IPBX > Backup files."
