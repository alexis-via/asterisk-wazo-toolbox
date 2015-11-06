#! /usr/bin/python
# -*- coding: utf-8 -*-
#  Copyright (C) 2015 Alexis de Lattre <alexis@via.ecp.fr>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This script is usefull if you want to have shortcuts for some
contacts present in Xivo's phonebook.

In the phonebook, you can enter the shortcut number in the "URL" field
of the contact.

Make sure that the shortcut numbers don't interfere with the internal
or public phone numbers. In the example below, the shortcut numbers
use 4 digits and start with 8 (8XXX).

Here is an example of Dialplan that uses this AGI script:

[default]
exten = _8XXX,1,NoOp(Phonebook shortcut dialed)
same = n,AGI(/var/lib/asterisk/agi-bin/phonebook-shortcut.py)
same = n,GotoIf(${SHORTCUT_FULLNUMBER}?FOUND:NOTFOUND)
same = n(FOUND),NoOp(Shortcut found)
same = n,Set(CONNECTEDLINE(name,i)=${CONNECTEDLINENAME})
same = n,Set(CONNECTEDLINE(name-pres,i)=allowed)
same = n,Set(CONNECTEDLINE(num,i)=${SHORTCUT_FULLNUMBER})
same = n,Set(CONNECTEDLINE(num-pres)=allowed)
same = n,Goto(to-extern,${SHORTCUT_FULLNUMBER},1)
same = n,Hangup()
same = n(NOTFOUND),Playback(invalid)
same = n,Hangup()

"""

import sys
import psycopg2
from optparse import OptionParser

__author__ = "Alexis de Lattre <alexis.delattre@akretion.com>"
__date__ = "June 2015"
__version__ = "0.1"

# Define command line options
options = [
    {'names': ('-f', '--field'), 'dest': 'field', 'type': 'string',
        'action': 'store', 'default': 'url',
        'help': 'Technical name of the field of the phonebook '
        'in which the shortcut is stored. Default = url.'},
]


def stdout_write(string):
    '''Wrapper on sys.stdout.write'''
    sys.stdout.write(
        (string + '\n').encode(sys.stdout.encoding or 'utf-8', 'replace'))
    sys.stdout.flush()
    # When we output a command, we get an answer "200 result=1" on stdin
    # Purge stdin to avoid these Asterisk error messages :
    # utils.c ast_carefulwrite: write() returned error: Broken pipe
    sys.stdin.readline()
    return True


def stderr_write(string):
    '''Wrapper on sys.stderr.write'''
    sys.stderr.write(
        (string + '\n').encode(sys.stdout.encoding or 'utf-8', 'replace'))
    sys.stdout.flush()
    return True


def main(options, arguments):
    # print 'options = %s' % options
    # print 'arguments = %s' % arguments

    # AGI passes parameters to the script on standard input
    stdinput = {}
    while 1:
        input_line = sys.stdin.readline()
        if not input_line:
            break
        line = input_line.strip()
        try:
            variable, value = line.split(':')
        except:
            break
        if variable[:4] != 'agi_':  # All AGI parameters start with 'agi_'
            stderr_write("bad stdin variable : %s" % variable)
            continue
        variable = variable.strip()
        value = value.strip()
        if variable and value:
            stdinput[variable] = value
    stderr_write("full AGI environnement :")

    for variable in stdinput.keys():
        stderr_write("%s = %s" % (variable, stdinput.get(variable)))

    stdout_write('VERBOSE "Shortcut field is %s"' % options.field)
    stdout_write('VERBOSE "Dialed shortcut is %s"' % stdinput['agi_extension'])

    res = False
    try:
        conn = psycopg2.connect("""
            dbname='asterisk' user='asterisk' host='localhost'
            password='proformatique'""")
        cr = conn.cursor()
        cr.execute("""
            SELECT pb.displayname, pbn.number, pbn.type FROM phonebooknumber pbn
            LEFT JOIN phonebook pb ON pb.id = pbn.phonebookid
            WHERE """ + options.field + "=%s", (stdinput['agi_extension'], ))
        res = cr.fetchall()
        stderr_write("Result of SQL query = %s" % (res))
    except:
        stdout_write('VERBOSE "Unable to connect to the postgresql database"')
        return False

    if not res:
        stdout_write('VERBOSE "This shortcut is NOT present in the phonebook"')
        return False
    stdout_write('VERBOSE "This shortcut is present in the phonebook"')
    stdout_write('SET VARIABLE CONNECTEDLINENAME "%s"' % res[0][0])
    rdict = {}
    for entry in res:
        rdict[entry[2]] = entry[1]
    if rdict.get('mobile'):
        stdout_write('SET VARIABLE SHORTCUT_FULLNUMBER "%s"' % rdict['mobile'])
    elif rdict.get('office'):
        stdout_write('SET VARIABLE SHORTCUT_FULLNUMBER "%s"' % rdict['office'])
    elif rdict.get('home'):
        stdout_write('SET VARIABLE SHORTCUT_FULLNUMBER "%s"' % rdict['home'])
    elif rdict.get('other'):
        stdout_write('SET VARIABLE SHORTCUT_FULLNUMBER "%s"' % rdict['other'])
    return True

if __name__ == '__main__':
    usage = "Usage: phonebook-shortcut.py [options]"
    epilog = "Script written by Alexis de Lattre. "
    "Published under the GNU AGPL licence."
    description = "This is an AGI script that implements shortcut numbers "
    "with Xivo phonebook."
    parser = OptionParser(usage=usage, epilog=epilog, description=description)
    for option in options:
        param = option['names']
        del option['names']
        parser.add_option(*param, **option)
    options, arguments = parser.parse_args()
    sys.argv[:] = arguments
    main(options, arguments)
