#! /usr/bin/python
# -*- encoding: utf-8 -*-
#
# Copyright (C) 2012 Alexis de Lattre <alexis _at_ via.ecp.fr>
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version. See http://www.gnu.org/licenses/gpl.html


# TODO
# Add header Auto-Submitted: auto-generated
# https://bitbucket.org/ginstrom/mailer/issue/10/ability-to-add-auto-submitted-header
# better logging than a simple print

from Asterisk import Manager
from mailer import Mailer, Message
from pprint import pformat
import socket
import sys
from optparse import OptionParser


option_silent = {'names': ('-s', '--silent'), 'dest': 'silent', 'help': "Don't print anything on standard output if everything is fine. Use this option when the cron runs the script.", 'action': 'store_true', 'default': False}
option_port = {'names': ('-p', '--port'), 'dest': 'port', 'type': 'int', 'help': "Port of Asterisk Manager. Default = 5038", 'action': 'store', 'default': 5038}
option_ip = {'names': ('-a', '--ip'), 'dest': 'ip', 'type': 'string', 'help': "IP address of Asterisk Manager. Default = 127.0.0.1", 'action': 'store', 'default': '127.0.0.1'}
option_login = {'names': ('-u', '--login'), 'dest': 'login', 'type': 'string', 'help': "Login for the Asterisk Manager. Default = alexis", 'action': 'store', 'default': 'alexis'}
option_passwd = {'names': ('-w', '--password'), 'dest': 'passwd', 'type': 'string', 'help': "Password for the Asterisk Manager. Default = ast12rulz42", 'action': 'store', 'default': 'ast12rulz42'}
option_smtp = {'names': ('-t', '--smtp'), 'dest': 'smtp', 'type': 'string', 'help': "IP address of DNS name of the SMTP server. Default = localhost", 'action': 'store', 'default': 'localhost'}
option_fromemail = {'names': ('-m', '--from'), 'dest': 'fromemail', 'type': 'string', 'help': "E-mail address used in the From header. Default = asterisk@hostname", 'action': 'store', 'default': 'asterisk@hostname'}
option_flag = {'names': ('-f', '--flag'), 'dest': 'flag', 'type': 'string', 'help': "Content of the flag present in the subject of the e-mail. Only use ASCII characters. Default = hostname of the machine that runs the script.", 'action': 'store', 'default': False}
option_nosipreload = {'names': ('-o', '--nosipreload'), 'dest': 'nosipreload', 'help': "Don't execute the command 'sip reload' when a SIP trunk is not registered.", 'action': 'store_true', 'default': False}

options = [option_silent, option_port, option_ip, option_login, option_passwd, option_smtp, option_fromemail, option_flag, option_nosipreload]


def send_mail(subject, body):
    asterisk_install = socket.gethostname()
    if options.fromemail == 'asterisk@hostname':
        mail_from = 'asterisk@' + socket.getfqdn()
    else:
        mail_from = options.fromemail
    message = Message(From=mail_from, To=arguments, charset="utf-8")
    message.Subject = '[' + (options.flag or asterisk_install) + '] ' + subject
    message.Body = u'Hostname : %s\n\n' % asterisk_install + body + u"\n-- \nAutomatic e-mail sent by the monitoring script check_sip_trunks.py. Do not reply."
    sender = Mailer(options.smtp)
    try:
        sender.send(message)
        if not options.silent:
            print "Mail sent"
    except Exception, e:
        print "CANNOT send e-mail : %s" % str(e)
    return True


if __name__ == '__main__':
    usage = "usage: %prog [options] email1 email2 email3 ..."
    epilog = "Script written by Alexis de Lattre. Published under the GNU GPL licence."
    description = "This script sends an e-mail when a SIP trunk is not registered."
    parser = OptionParser(usage=usage, epilog=epilog, description=description)
    for option in options:
        param = option['names']
        del option['names']
        parser.add_option(*param, **option)
    options, arguments = parser.parse_args()
    sys.argv[:] = arguments

    try:
        # Connect to AMI
        m = Manager.Manager((options.ip, options.port), options.login, options.passwd)
        res = m.SipShowRegistry()
        if not options.silent:
            print "Sip show REGISTRY =", pformat(res)
    except Exception, e:
        subject = 'Cannot connect to the Asterisk Manager'
        body = u"""The monitoring script can't connect to the Asterisk Manager.\n\nHere are the details of the error :\n%s""" % e
        send_mail(subject, body)
        raise

    if not res:
            subject = "No SIP trunk"
            body = u"""The command "sip show registry" doesn't show any SIP trunk !\n\nHere are the details :\n%s""" % pformat(res)
            send_mail(subject, body)

    else:
        unregistered_sip_trunks = []
        for trunk in res.items():
            if not options.silent:
                print "TRUNK :", trunk[0]
                print "State =", trunk[1].get('State')
            if trunk[1].get('State') != 'Registered':
                unregistered_sip_trunks.append(trunk[0])
        if unregistered_sip_trunks:
            # Do a SIP reload unless --nosipreload option has been set
            res_sipreload = False
            if not options.nosipreload:
                try:
                    res_sipreload = m.Command('sip reload')
                    if not options.silent:
                        print "Command 'sip reload' executed."
                except Exception, e:
                    subject = "Command 'sip reload' failed"
                    body = u"""The command "sip reload" failed !\n\nHere are the details :\n%s""" % pformat(res_sipreload)
                    send_mail(subject, body)

            if len(unregistered_sip_trunks) > 1:
                trunk_str = 'trunks'
            else:
                trunk_str = 'trunk'
            subject = """%d SIP %s down : %s""" % (len(unregistered_sip_trunks), trunk_str, str(unregistered_sip_trunks)[1:-1])
            body = u"""The command "sip show registry" shows %d unregistered SIP %s : %s.\n\nHere are the details :\n%s""" % (len(unregistered_sip_trunks), trunk_str, unicode(unregistered_sip_trunks)[1:-1], pformat(res))
            if res_sipreload:
                body += u"""\n\nThe script successfully executed the command 'sip reload', in the hope that it may fix the problem."""
            send_mail(subject, body)

    # Disconnect from AMI
    m.Logoff()
