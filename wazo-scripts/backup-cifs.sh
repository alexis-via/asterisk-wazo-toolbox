#! /bin/sh
# Backup to NAS mounted via CIFS
# Author : Alexis de Lattre <alexis.delattre@akretion.com>
# Date : May 2014

set -x

CIFS_URL=//192.168.0.42/informatique
CIFS_LOGIN=xivo
CIFS_PASSWD=enter_pwd_here
NAS_SUBDIR=xivo
LOCAL_MOUNTPOINT=/mnt/nas

do_backup () {
    if [ -d $LOCAL_MOUNTPOINT/$NAS_SUBDIR ]
    then
        echo -n "Start rsync..."
        rsync -av --no-o --no-g --delete-after --safe-links /var/backups/xivo $LOCAL_MOUNTPOINT/$NAS_SUBDIR
        echo "done."
    fi
    echo -n "Unmounting $LOCAL_MOUNTPOINT..."
    umount $LOCAL_MOUNTPOINT
    echo "done."
}

mountpoint $LOCAL_MOUNTPOINT

if [ $? -eq 0 ]
    then
    echo "The NAS is already mounted to $LOCAL_MOUNTPOINT"
    do_backup
else
    echo -n "Mounting NAS to $LOCAL_MOUNTPOINT..."
    mount.cifs -o user=$CIFS_LOGIN,password=$CIFS_PASSWD $CIFS_URL $LOCAL_MOUNTPOINT
    echo "done."
    mountpoint $LOCAL_MOUNTPOINT
    if [ $? -eq 0 ]
    then
        do_backup
    else
        echo "Didn't succeed to mount NAS. Exiting."
        exit 1
    fi
fi
