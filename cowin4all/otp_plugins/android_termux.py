from datetime import datetime
import logging
import subprocess
import json
import threading
import time
import requests
import re

from cowin4all.settings import OTP_REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

timeout = False
otp = None
time_of_request = None
event_waiter = threading.Event()


def get_otp_from_termux_api(client=None):
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


def listen_on_new_messages(otp_forwarder_mode=False, url=None):
    global event_waiter, time_of_request, otp
    sleep_time = 2
    last_received_message = None
    last_message_received_time = datetime.now()
    logger.info("Listening for new messages ... !!! The screen may seem frozen. "
                "But don't worry !! I am actually listening !!")
    otp_expiry_seconds = 180

    while True:
        if not otp_forwarder_mode:
            if event_waiter.is_set():
                break

        tmux_sms_list = subprocess.Popen(
            'termux-sms-list -l 10 -t inbox',
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True)

        output = tmux_sms_list.communicate()
        stdout = output[0].decode('utf-8')
        stderr = output[1].decode('utf-8').lower()
        # Normally the message with "found" or "no" pertains to "command not found / No such command etc..".
        if "found" in stderr or "no" in stderr:
            otp = None
            event_waiter.set()
            raise Exception("termux-api is not installed !! Error message : {}".format(stderr))

        messages = json.loads(stdout)
        for message in messages:
            match = re.findall("(?<=CoWIN is )[0-9]{6}", message["body"])
            if match:
                if message != last_received_message:
                    message_received_time = datetime.strptime(message["received"], "%Y-%m-%d %H:%M:%S")
                    # We  want to consider only new messages that were not encountered during last listen loop.
                    if last_message_received_time <= message_received_time:
                        # We don't want to send stale OTPs to the webhook. Hence the below condition
                        if not (datetime.now() - message_received_time).seconds >= otp_expiry_seconds:
                            if not otp_forwarder_mode:
                                otp = match[0]
                                last_received_message = message
                                last_message_received_time = message_received_time
                                event_waiter.set()
                                break
                            else:
                                logger.info("Received OTP Message: {message}. Sending to the webhook service !!"
                                            "".format(message=message))
                                try:
                                    requests.put(url=url, json=message)
                                    last_received_message = message
                                    last_message_received_time = message_received_time
                                except Exception:
                                    logger.error(
                                        "External Service not accepting connections !! "
                                        "Kindly check the webhook service !!")
                        else:
                            # Consider the message as sent if found stale
                            logger.info("Message: {} has gone stale and no more valid !! Ignoring the message "
                                        "going forward !!".format(message))
                            # Since this goes in a for loop , there may be multiple messages which may have been
                            # going stale. Hence this check is required to set the latest stale message
                            # as last received.
                            if message_received_time > last_message_received_time:
                                last_received_message = message
                                last_message_received_time = message_received_time

        time.sleep(sleep_time)

