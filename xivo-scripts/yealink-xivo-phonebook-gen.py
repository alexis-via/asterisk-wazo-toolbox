#! /usr/bin/python
# -*- encoding: utf-8 -*-
#
# Copyright (C) 2014 Alexis de Lattre <alexis _at_ via.ecp.fr>
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version. See http://www.gnu.org/licenses/gpl.html


import sys
from optparse import OptionParser
import psycopg2
from lxml import etree
from xivo_provd_cli import client as cli_client
# from pprint import pprint

# Get postgres data as unicode
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

XIVO_PROVD_PLUGIN_PATH = '/var/lib/xivo-provd/plugins/'

options = [
    {
        'names': ('-f', '--filename'),
        'type': 'string',
        'dest': 'filename',
        'help': "Specify the name of the XML file that will be generated "
        "(without the '.xml' extension).",
        'action': 'store',
        'default': 'ContactData'},
    {
        'names': ('-r', '--remote'),
        'dest': 'remote',
        'help': "Generate a format for a Remote Phonebook (instead of a "
        "local Phonebook).",
        'action': 'store_true',
        'default': False},
    ]


def reformat_phone_number(number):
    if number:
        for char_to_del in [' ', '.', '-', '_', '(', ')']:
            number = number.replace(char_to_del, '')
    return number

if __name__ == '__main__':
    usage = "usage: %prog [options] xivo-plugin1 xivo-plugin2 ..."
    epilog = "Script written by Alexis de Lattre. " \
        "Published under the GNU GPL licence."
    description = "This script generates the XML file for Yealink " \
        "phonebook from Xivo's database. If the script is started without " \
        "arguments, it will generale the XML file in all Yealink " \
        "provisionning plugins. To use this script, you need " \
        "to install the Debian package 'python-lxml'."
    parser = OptionParser(usage=usage, epilog=epilog, description=description)
    for option in options:
        param = option['names']
        del option['names']
        parser.add_option(*param, **option)
    options, arguments = parser.parse_args()
    sys.argv[:] = arguments
    print "arguments=", arguments
    print "filename=", options.filename
    print "remote=", options.remote

    dsn = 'dbname=asterisk host=localhost port=5432 user=asterisk '\
        'password=proformatique'
    res = False
    try:
        conn = psycopg2.connect(dsn)
        cr = conn.cursor()
        cr.execute(
            "SELECT pb.id, pb.displayname, pbn.number, pbn.type FROM "
            "phonebooknumber pbn LEFT JOIN phonebook pb ON "
            "pbn.phonebookid=pb.id WHERE type IN ('mobile', 'office')")
        res = cr.fetchall()

    except:
        print "Failed to connect to DB"
    finally:
        if cr:
            cr.close()
        if conn:
            conn.close()

    if not res:
        print "No entry found in Xivo's phonebook"
        sys.exit(1)
    else:
        print "SQL query returned some results"

    # W52P can only accept 100 entries max
    res = res[0:100]
    # pprint(res)

    yphonebook = {}
    # key = id in phonebook table
    # values= {'name': u'Alex', 'office': '0142124212', 'mobile': '0788997766'}
    for entry in res:
        if entry[0] in yphonebook:
            yphonebook[entry[0]][entry[3]] = entry[2]
        else:
            yphonebook[entry[0]] = {
                'name': entry[1],
                entry[3]: entry[2],
                }

    # pprint(yphonebook)

    if options.remote:
        root = etree.Element('YealinkIPPhoneDirectory')

        for contact in yphonebook.values():
            direntry = etree.SubElement(root, 'DirectoryEntry')
            direntryname = etree.SubElement(direntry, 'Name')
            direntryname.text = contact['name']
            if contact.get('office'):
                office_number = reformat_phone_number(
                    contact.get('office', ''))
                direntrytel1 = etree.SubElement(direntry, 'Telephone')
                direntrytel1.text = office_number
            if contact.get('mobile'):
                mobile_number = reformat_phone_number(
                    contact.get('mobile', ''))
                direntrytel2 = etree.SubElement(direntry, 'Telephone')
                direntrytel2.text = mobile_number

    else:
        root = etree.Element('root_contact')

        for contact in yphonebook.values():
            office_number = reformat_phone_number(contact.get('office', ''))
            mobile_number = reformat_phone_number(contact.get('mobile', ''))
            direntry = etree.SubElement(
                root, 'contact', display_name=contact['name'],
                office_number=office_number,
                mobile_number=mobile_number)

    xml_content = etree.tostring(
        root, pretty_print=True, encoding='UTF-8', xml_declaration=True)

    plugin_list = arguments

    if not plugin_list:
        client = cli_client.new_cli_provisioning_client(
            'http://localhost:8666/provd', ('admin', ''))
        installed_plugins = client.plugins().installed().keys()
        print "installed_plugins=", installed_plugins
        for plugin in installed_plugins:
            if plugin.startswith('xivo-yealink-'):
                plugin_list.append(plugin)

    print "plugin_list=", plugin_list

    for plugin in plugin_list:
        fullfilename = '%s%s/var/tftpboot/%s.xml' % (
            XIVO_PROVD_PLUGIN_PATH, plugin, options.filename)
        print "Writing to file %s" % fullfilename
        f = open(fullfilename, 'w')
        f.write(xml_content)
        f.close()
