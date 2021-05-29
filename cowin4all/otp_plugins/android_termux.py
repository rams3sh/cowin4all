from datetime import datetime
import logging
import subprocess
import json
import threading
import time
import re

from cowin4all.settings import OTP_REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

timeout = False
otp = None
time_of_request = None
event_waiter = threading.Event()


def get_otp_from_termux_api():
    global otp, timeout, time_of_request
    otp = None
    time_of_request = datetime.now()
    logger.info("Waiting for OTP !! ")
    message_listener = threading.Thread(target=listen_on_new_messages)
    message_listener.start()

    event_waiter.wait(timeout=OTP_REQUEST_TIMEOUT_SECONDS)
    event_waiter.clear()
    if otp:
        logger.info("OTP Received: " + str(otp))
    else:
        logger.info("OTP wait timed-out !! Re-requesting !!")
    return otp


def listen_on_new_messages():
    global event_waiter, time_of_request, otp

    while True:
        if event_waiter.is_set():
            break

        tmux_sms_list = subprocess.Popen(
            'termux-sms-list -l 10 -t inbox',
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True)

        if tmux_sms_list.returncode != 0:
            otp = None
            event_waiter.set()
            raise Exception("termux-api is not installed !!")

        messages = tmux_sms_list.communicate()[0].decode('utf-8')
        messages = json.loads(messages)

        for message in messages:
            match = re.findall("(?<=CoWIN is )[0-9]{6}", message)
            if match:
                received_time = datetime.strptime(message["received"], "%Y-%m-%d %H:%M:%S")
                # Maximum limit of message receipt is 180.
                # Keeping 150 is a safer option.
                if (received_time - time_of_request).seconds < 150:
                    otp = match[0]
                    event_waiter.set()
                    break

        time.sleep(2)