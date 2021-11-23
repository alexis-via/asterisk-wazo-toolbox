#! /usr/bin/python3
#
# Copyright (C) 2012-2021 Alexis de Lattre <alexis _at_ via.ecp.fr>
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version. See http://www.gnu.org/licenses/gpl.html


# TODO
# Add header Auto-Submitted: auto-generated
# https://bitbucket.org/ginstrom/mailer/issue/10/ability-to-add-auto-submitted-header

from asterisk.ami import AMIClient, SimpleAction
from mailer import Mailer, Message
from pprint import pformat
import socket
import sys
import argparse
import time
import os
import logging


def send_mail(subject, body):
    logger.info('Sending email with subject=%s', subject)
    asterisk_install = socket.gethostname()
    if args.fromemail == 'asterisk@hostname':
        mail_from = 'asterisk@' + socket.getfqdn()
    else:
        mail_from = args.fromemail
    message = Message(From=mail_from, To=args.dest_email_list, charset="utf-8")
    message.Subject = '[%s] %s'  % (args.flag or asterisk_install, subject)
    message.Body = "Hostname : %s\n\n%s\n\n-- \nAutomatic e-mail sent by the monitoring script check_pjsip_trunks.py. Do not reply." % (asterisk_install, body)
    sender = Mailer(args.smtp)
    try:
        sender.send(message)
        logger.info("Mail sent")
    except Exception as e:
        logger.error("CANNOT send e-mail : %s" % e)
    return True

def ami_event_listener(event, **kwargs):
    logger.debug('New event')
    if event.keys.get('Status') and event.keys.get('ClientUri'):
        status = event.keys['Status']
        server = event.keys['ClientUri'][4:]
        if status != 'Registered':
            logger.warning('%s status %s', server, status)
            res[server] = status
        else:
            logger.info('%s is Registered', server)

def main(args):
    try:
        # Connect to AMI
        logger.debug('AMI login')
        client = AMIClient(address=args.ip, port=args.port)
        client.login(username=args.login, secret=args.passwd)
    except Exception as e:
        logger.error('Failed to connect to AMI. Error: %s', e)
        subject = 'Cannot connect to the Asterisk Manager'
        body = """The monitoring script can't connect to the Asterisk Manager.\n\nHere are the details of the error :\n%s""" % e
        send_mail(subject, body)
        raise

    client.add_event_listener(
        ami_event_listener,
        white_list=['OutboundRegistrationDetail'])
    try:
        action = SimpleAction('PJSIPShowRegistrationsOutbound')
        future_registration = client.send_action(action)
        res_registration = future_registration.response
        if res_registration.status != 'Success':
            logger.erro('PJSIPShowRegistrationsOutbound returned %s. Existing.' % res_registration.status)
            raise
        logger.info("PJSIPShowRegistrationsOutbound returned %s", res_registration.status)
    except Exception as e:
        logger.error('PJSIPShowRegistrationsOutbound request failed. Error: %s', e)
        subject = 'PJSIPShowRegistrationsOutbound failed'
        body = """The monitoring script can't execute the request PJSIPShowRegistrationsOutbound.\n\nHere are the details of the error :\n%s""" % e
        send_mail(subject, body)
        raise

    logger.debug('Sleep while waiting for all events')
    time.sleep(3)
    if res:
        # Do a pjSIP reload unless --nopjsipreload option has been set
        if not args.nopjsipreload:
            reload_command = 'module reload res_pjsip.so'
            reload_success = False
            try:
                action_reload = SimpleAction('Command', Command=reload_command)
                logger.info('Reloading pjsip module')
                future_reload = client.send_action(action_reload)
                print('future_reload=', future_reload)
                res_reload = future_reload.response
                print('res_reload=', res_reload)
                print('dur=', dir(res_reload))
#                if res_reload.status == 'Success':
                reload_success = True
                #else:
                #    logger.warning('The reload command returned %s', res_reload.status)
            except Exception as e:
                logger.error("Command 'reload_command' failed. Error: %s", reload_command, e)
                subject = "pjsip reload failed"
                body = """The command '%s' failed !\n\nTechnical error:\n%s""" % (reload_command, e)
                send_mail(subject, body)

            if len(res) > 1:
                trunk_str = 'trunks'
                subject = """%d SIP %s down""" % (len(res), trunk_str)
            else:
                trunk_str = 'trunk'
                subject = """%d SIP %s down %s""" % (len(res), trunk_str, ', '.join(list(res.keys())))
            body = """There are %d SIP %s down:\n%s""" % (len(res), trunk_str, '\n'.join(["- %s : '%s'" % (server, status) for (server, status) in res.items()]))
            if reload_success:
                body += """\n\nThe command '%s' has been executed in the hope that it may fix the problem.""" % reload_command
            send_mail(subject, body)

    logger.debug('AMI Logoff')
    # Disconnect from AMI
    client.logoff()

if __name__ == '__main__':
    usage = "usage: check_pjsip_trunk.py [options] email1 email2 email3 ..."
    epilog = "Script written by Alexis de Lattre. Published under the GNU GPL licence."
    description = "This script sends an e-mail when a SIP trunk is not registered."
    parser = argparse.ArgumentParser(usage=usage, epilog=epilog, description=description)
    parser.add_argument(
        '-s', '--silent', dest='silent', action='store_true', help="Don't print anything on standard output if everything is fine. Use this option when the cron runs the script.")
    parser.add_argument(
        '-p', '--port', dest='port', type=int, default=5038, help="Port of Asterisk Manager. Default = 5038")
    parser.add_argument(
        '-a', '--ip', dest='ip', default='127.0.0.1', help="IP address of Asterisk Manager. Default = 127.0.0.1")
    parser.add_argument('-u', '--login', dest='login', help="Login for the Asterisk Manager.")
    parser.add_argument('-w', '--password', dest='passwd', help="Password for the Asterisk Manager.")
    parser.add_argument('-t', '--smtp', dest='smtp', default='localhost', help="IP address of DNS name of the SMTP server.")
    parser.add_argument('-m', '--from', dest='fromemail', default='asterisk@hostname', help="E-mail address used in the From header. Default = asterisk@hostname")
    parser.add_argument('-f', '--flag', dest='flag', help="Content of the flag present in the subject of the e-mail. Only use ASCII characters. Default = hostname of the machine that runs the script.")
    parser.add_argument('-o', '--nopjsipreload', dest='nopjsipreload', action='store_true', help="Don't execute the command 'sip reload' when a SIP trunk is not registered.")
    parser.add_argument(
        "dest_email_list", nargs='*',
        help="List of destination e-mail adresses")

    args = parser.parse_args()
    logger = logging.getLogger('check_pjsip_trunks')
    log_level = "DEBUG"
    if args.silent:
        log_level = "WARN"
    logging.basicConfig(level=os.environ.get("LOGLEVEL", log_level))

    res = {}  # key = server, value = registration status
    main(args)

