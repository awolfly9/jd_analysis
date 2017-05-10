#-*- coding: utf-8 -*-

import smtplib
import logging
import config

from cus_exception import CusException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to_email, subject, body):
    try:
        logging.debug('send_email start...')

        msg = MIMEMultipart()
        msg['From'] = config.self_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        if config.email_type == 'gmail':  # gmail send
            server = smtplib.SMTP('smtp.gmail.com:587')
        elif config.email_type == 'qq':  # qq send
            server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        else:  # default gmail
            server = smtplib.SMTP('smtp.gmail.com:587')

        server.set_debuglevel(1)
        server.ehlo()
        server.starttls()
        server.login(config.self_email, config.self_password)
        server.sendmail(config.self_email, to_email, msg.as_string())
        server.quit()
        logging.debug('send_email success...')
        return True
    except Exception, e:
        logging.exception('send_email exception msg:%s' % e)
        raise CusException('send_email', 'send_email error msg:%s' % e)
