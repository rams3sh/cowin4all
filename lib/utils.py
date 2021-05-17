from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
import PySimpleGUI as sg
import requests
import logging
import re
import os
import tempfile
import datetime
import time

from lib.constants import endpoint_map, default_request_retry_backoff_factor_seconds, default_request_timeout_seconds, \
    default_connection_error_retry_attempts, default_blocked_request_retry_backoff_factor_seconds, \
    delay_refresh_token_retry_delay_seconds, default_user_agent, \
    vaccine_types, doses, payment_types, minimum_age_limits

logger = logging.getLogger(__name__)


def requests_retry_session(retries=None, backoff_factor=None, status_forcelist=(500, 502, 504)):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session


def send_request(action=None, payload=None, backoff_factor=default_request_retry_backoff_factor_seconds,
                 additional_headers=None,
                 blocked_request_backoff_factor=default_blocked_request_retry_backoff_factor_seconds,
                 timeout: int = default_request_timeout_seconds,
                 connection_error_retries: int = default_connection_error_retry_attempts,
                 client=None,
                 explicit_token_refresh_status_codes=None,
                 **kwargs):

    if explicit_token_refresh_status_codes:
        if not isinstance(explicit_token_refresh_status_codes, list):
            explicit_token_refresh_status_codes = [explicit_token_refresh_status_codes]
    else:
        explicit_token_refresh_status_codes = []

    attempted_connection_error_retries = 0

    method = endpoint_map[action]["METHOD"]
    endpoint = endpoint_map[action]["ENDPOINT"]

    endpoint_variables = re.findall("(?<=\\{)[^}]+", endpoint)
    if endpoint_variables:
        endpoint = endpoint.format(**kwargs)
        for kw in endpoint_variables:
            kwargs.pop(kw)

    headers = dict()
    base_headers = {'User-Agent': default_user_agent,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'}
    headers.update(base_headers)

    if additional_headers:
        headers.update(additional_headers)

    while True:

        if client:
            token = getattr(client, "token")

            if token:
                headers.update({"Authorization": "Bearer " + token})

        request = requests.Request(method=method, url=endpoint,
                                   headers=headers, params=kwargs,
                                   json=payload).prepare()

        logger.debug("Request Body :-\nMethod : {} , \nURL : {}, \nHeaders : {} , \nPayload : {}\n".format(
            request.method, request.url, request.headers, request.body))
        session = requests_retry_session(retries=connection_error_retries,
                                         backoff_factor=backoff_factor)
        response = session.send(request, timeout=timeout, allow_redirects=False)
        logger.debug("Response Body :-\nStatus Code : {} , \nHeaders : {} , \nBody : {}\n".format(
            response.status_code, response.headers, response.content))

        if response.status_code in [200, 201]:
            if client:
                client.auto_refresh_token_retries_attempted = 0
            return response

        logger.error("Error while performing '{}'. Status Code received :{}, Exception: {}"
                     "".format(action, response.status_code, response.content.decode("utf-8")))
        if ((response.status_code in [401]) or (response.status_code in
                                                explicit_token_refresh_status_codes)) \
                and (client and client.auto_refresh_token):

            while True:
                if client.auto_refresh_retries_count is not None:
                    # client.auto_refresh_retries_count as None signifies no limits for token refresh retry exists
                    if client.auto_refresh_retries_count > client.auto_refresh_token_retries_attempted:
                        client.auto_refresh_token_retries_attempted += 1
                    else:
                        raise Exception("Maximum auto refresh token attempts for the client :{} reached."
                                        "".format(client.auto_refresh_token_retries_attempted))
                try:
                    refresh_token(client=client)
                    break
                except Exception as e:
                    time.sleep(delay_refresh_token_retry_delay_seconds)

        elif response.status_code in [403]:
            if client.retry_blocked_request:
                if attempted_connection_error_retries < connection_error_retries:
                    logger.error("Request blocked !! Retrying request ..")
                    attempted_connection_error_retries += 1
                    time.sleep(blocked_request_backoff_factor * (2 ** (attempted_connection_error_retries - 1)))
                    continue
                else:
                    raise Exception("Exhausted request retries !!")
            else:
                raise Exception(response.content.decode("utf-8"))
        else:
            raise Exception(response.content.decode("utf-8"))


def get_applicable_sessions(client=None, pin_codes=None,
                            district_ids=None,
                            dates=None, days_range: int = None,
                            vaccine_type: str = None,
                            payment_type: str = None, age: int = None, dose: int =None):

    if payment_type in ["any", None]:
        payment_type = payment_types
    elif payment_type.lower() not in payment_types:
        return {}
    else:
        payment_type = [payment_type]

    if vaccine_type in ["any", None]:
        vaccine_type = vaccine_types
    elif vaccine_type.lower() not in vaccine_types:
        return {}
    else:
        vaccine_type = [vaccine_type]

    if age is [None]:
        age = minimum_age_limits
    elif age not in minimum_age_limits:
        return {}
    else:
        age = [age]

    if dose is None:
        dose = doses
    elif dose not in doses:
        return {}
    else:
        dose = [dose]

    centres = []
    d = set()
    if dates:
        if not isinstance(dates, list):
            d = {dates}
        else:
            d = set(dates)

    if isinstance(days_range, int):
        for i in range(0, days_range):
            date = datetime.datetime.now() + datetime.timedelta(days=i)
            d.add(datetime.datetime.strftime(date, "%d-%m-%Y"))

    for i in d:
        if district_ids:
            if not isinstance(district_ids, list):
                district_ids = [district_ids]

            for district_id in district_ids:
                for centre in client.check_slot_district_wise(district_id=district_id, date=i):
                    if centre not in centres:
                        centres.append(centre)
        if pin_codes:
            if not isinstance(pin_codes, list):
                pin_codes = [pin_codes]

            for pin_code in pin_codes:
                for centre in client.check_slot_pin_wise(pin_code=pin_code, date=i):
                    if centre not in centres:
                        centres.append(centre)

    filtered_sessions = dict()

    if centres:

        for centre in centres:
            if centre["fee_type"].lower() in payment_type:
                for session in centre["sessions"]:
                    if session["vaccine"].lower() in vaccine_type:
                        if session["available_capacity"] > 0:
                            for d in dose:
                                if session.get("available_capacity_dose{}".format(d)) > 0:
                                    if session.get("min_age_limit") in age:
                                        if not filtered_sessions.get(centre["center_id"]):
                                            filtered_sessions[centre["center_id"]] = \
                                                {
                                                  "name": centre["name"],
                                                  "address": centre["address"],
                                                  "state_name": centre["state_name"],
                                                  "district_name": centre["district_name"],
                                                  "block_name": centre["block_name"],
                                                  "pin_code": centre["pincode"],
                                                  "fee_type": centre["fee_type"],
                                                  "sessions": []
                                                }
                                        filtered_sessions[centre["center_id"]]["sessions"].append(session)

    return filtered_sessions


def get_captcha_input_manually(captcha=None, client=None, _initial_call=True, alert_method=None):
    # One can initialise a custom alerter method for alerting
    if _initial_call:
        if alert_method:
            alert_method()

    while True:
        file_path = os.path.join(tempfile.gettempdir(), str(datetime.datetime.now().timestamp())+"_captcha")
        with open(file_path+".svg", 'w') as f:
            f.write(captcha)

        drawing = svg2rlg(file_path+".svg")
        renderPM.drawToFile(drawing, file_path+".png", fmt="PNG")

        layout = [[sg.Image(file_path+".png")],
                  [sg.Text("Enter Captcha Below")],
                  [sg.Input()],
                  [sg.Button('Submit', bind_return_key=True)],
                  ]
        if client:
            layout[3] += [sg.Button('Refresh')]

        window = sg.Window('Enter Captcha', layout)
        event, values = window.read()
        if event == "Refresh":
            os.remove(file_path+".svg")
            os.remove(file_path + ".png")
            return get_captcha_input_manually(captcha=client.get_captcha(), client=client, _initial_call=False)
        else:
            window.close()
            os.remove(file_path+".svg")
            os.remove(file_path + ".png")
            if values:
                return values[1].strip()
            return


def get_otp_manually(client=None):
    return input("Enter OTP:")


def refresh_token(client=None):
    client.token = None
    client.taxation_id = None
    otp_retrieval_method = getattr(client, "otp_retrieval_method")
    if not otp_retrieval_method:
        otp_retrieval_method = get_otp_manually
    client.get_otp()
    otp = otp_retrieval_method(client=client)
    if not otp:
        raise Exception("Invalid OTP !!")
    try:
        client.validate_otp(otp=otp)
    except:
        raise Exception("Invalid OTP !!")
    return client
