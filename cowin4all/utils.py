from datetime import datetime, timedelta
from copy import deepcopy
from jsonschema.exceptions import ValidationError
# import multiprocessing
# import os
import re
import tabulate
import jsonschema
import sys
import subprocess

from cowin4all.settings import BOOKING_MODES, VACCINATION_DOSE_DATES  # , AUDIO_FILE_PLAYING_COMMAND, BOOKING_ALERT_AUDIO_PATH,
from cowin4all.cowin4all_sdk.api import APIClient
from cowin4all.cowin4all_sdk.constants import vaccine_types, minimum_age_limits, payment_types, doses


# def play_sound(file_path):
#     os.system(AUDIO_FILE_PLAYING_COMMAND.format(audio_file_path=file_path))
#
#
# def booking_alert():
#     p = multiprocessing.Process(target=play_sound, args=(BOOKING_ALERT_AUDIO_PATH, ), daemon=True)
#     p.start()


# Take from bombardier-gif's code base and modified it for multiple data type support
def display_table(dict_list, exclude_keys=None, default_attribute_name=None):
    temp_dict = deepcopy(dict_list)

    if exclude_keys:
        if not isinstance(exclude_keys, list):
            exclude_keys = [exclude_keys]

        for element in temp_dict:
            for key in exclude_keys:
                if element.get(key):
                    element.pop(key)

    try:
        header = ["S.No"] + [key.title().replace("_", " ") for key in temp_dict[0].keys()]
        rows = [[idx + 1] + list(x.values()) for idx, x in enumerate(temp_dict)]
    except (AttributeError, TypeError):
        header = ["S.No"] + [default_attribute_name or "Value"]
        rows = [[i+1, d] for i, d in zip(range(len(dict_list)), dict_list)]
    print("\n", tabulate.tabulate(rows, header, tablefmt="grid"))


def get_timestamp():
    return str(datetime.now().timestamp())


def get_possible_age(year):
    return datetime.now().year - int(year)


def validate_selected_beneficiaries(beneficiaries):
    booking_age_limit = set()
    awaited_dose = set()
    vaccine = set()
    for b in beneficiaries:
        booking_age_limit.add(b["booking_age_limit"])
        awaited_dose.add(b["awaited_dose"])
        vaccine.add(b["vaccine"])

    if len(booking_age_limit) > 2:
        raise ValueError("Encountered attempted booking for beneficiaries falling under different booking age limit "
                         "category. Please ensure in a given booking, all "
                         "beneficiaries' booking age limit category are same !!")
    if len(awaited_dose) > 2:
        raise ValueError("Encountered attempted booking for beneficiaries with different vaccine dose status. "
                         "Please ensure in a given booking, all "
                         "beneficiaries' vaccine dose status are same !!")
    if len(vaccine) > 2:
        raise ValueError("Encountered attempted booking for beneficiaries vaccinated with different vaccines. "
                         "Please ensure in a given booking, all "
                         "beneficiaries' vaccine type is same !!")


def validate_serial_no(snos: (int, list) = None):

    if not isinstance(snos, set):
        snos = {snos}

    for sno in snos:
        int(sno)
        if sno <= 0:
            raise ValueError("Invalid S.No(s) provided. Kindly re-enter the values !!")


def select_beneficiaries(beneficiaries):
    display_table(beneficiaries)
    s_nos = input("Enter S.No(s) of the beneficiaries in order of priority for slot booking (in case of multiple "
                  "beneficiaries use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        validate_serial_no(s_nos)
        selected_beneficiaries = [beneficiaries[s - 1] for s in s_nos]
        validate_selected_beneficiaries(selected_beneficiaries)
    except IndexError:
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_beneficiaries = select_beneficiaries(beneficiaries)
    except ValueError as e:
        print(e)
        selected_beneficiaries = select_beneficiaries(beneficiaries)

    return selected_beneficiaries


def select_state(client=None):
    states = client.list_states()
    display_table(states, exclude_keys=["state_id"])
    s_nos = input("Enter S.No(s) of the state(s) to be considered as option for booking (in case of multiple "
                  "states use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        validate_serial_no(s_nos)
        selected_states = [states[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_states = select_state(client=client)

    return selected_states


def select_district(client=None, state_ids=None):
    districts = []
    for st_id in state_ids:
        districts += client.list_districts(state_id=st_id)

    display_table(districts, exclude_keys=["district_id"])
    s_nos = input("Enter S.No(s) of the district(s) to be considered as option for booking (in case of multiple "
                  "districts use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        validate_serial_no(s_nos)
        selected_districts = [districts[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_districts = select_district(client=client, state_ids=state_ids)
    return selected_districts


def select_pin_code():
    message = "\n\nEnter pin code belonging to district(s) selected previously, in case you would want to narrow " \
              "down your location of vaccine, else just press enter. (in case of multiple " \
              "pin codes use ',' to separate them) : "
    selected_pin_codes = input(message)

    if selected_pin_codes:
        try:
            selected_pin_codes = list(set([int(p.strip()) for p in selected_pin_codes.split(",")]))
        except (IndexError, ValueError):
            print("Invalid pin code(s) provided. Kindly re-enter the values !!")
            selected_pin_codes = select_pin_code()
    else:
        selected_pin_codes = []
    return selected_pin_codes


def select_vaccine():
    display_table(vaccine_types, default_attribute_name="Vaccine Name")
    s_nos = input("Enter S.No(s) of the vaccine type(s) to be considered as option for booking (in case of multiple "
                  "vaccine types use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        validate_serial_no(s_nos)
        selected_vaccine_options = [vaccine_types[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_vaccine_options = select_vaccine()

    return selected_vaccine_options


def generate_date(days_range=None):
    dates = []
    for i in range(days_range):
        dates.append((datetime.now() + timedelta(days=i)).strftime("%d-%m-%Y"))
    return dates


def select_dates(beneficiaries=None):
    dates = generate_date(days_range=4)
    display_table(dates, default_attribute_name="Date (dd-mm-yyyy)")
    s_nos = input("Enter S.No(s) of the date(s) to be considered as option for booking (in case of multiple "
                  "dates use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        validate_serial_no(s_nos)
        selected_dates = [dates[s - 1] for s in s_nos]
        validate_dose_booking_date(beneficiaries=beneficiaries, booking_dates=selected_dates)
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_dates = select_dates(beneficiaries=beneficiaries)
    except Exception as e:
        print(e)
        response = select_yes_or_no(message="Do you want to re-consider the dates ?")
        if response == "n":
            return
        else:
            return select_dates(beneficiaries=beneficiaries)

    return selected_dates


def select_payment_type():
    display_table(payment_types, default_attribute_name="Payment Type")
    s_nos = input("Enter S.No(s) of the payment type(s) to be considered as option for booking (in case of multiple "
                  "payment types use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        validate_serial_no(s_nos)
        selected_payment_types = [payment_types[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_payment_types = select_payment_type()

    return selected_payment_types


def select_booking_mode():
    display_table(BOOKING_MODES)
    s_no = input("Enter S.No of the booking mode to be considered while booking (choose only one): ")
    try:
        s_no = int(s_no)
        validate_serial_no(snos=s_no)
        selected_booking_mode = BOOKING_MODES[s_no-1]
    except (IndexError, ValueError, TypeError):
        print("Invalid S.No provided. Kindly re-enter the values !!")
        selected_booking_mode = select_booking_mode()

    return selected_booking_mode


def confirm_booking_details(booking_details):
    print("\n", "-"*10, "\n")
    print("CONFIRMATION")
    print("\n", "-"*10, "\n")
    print("\nPlease read through the details to be considered for the vaccine booking below and confirm before we can "
          "proceed with automated booking !!.\n")

    print("\nList of beneficiaries :- ", "\n")
    display_table(booking_details["beneficiaries"])

    print("\nList of vaccine preference :- ", "\n")
    display_table(booking_details["preferred_vaccine_types"], default_attribute_name="Vaccine Preference")

    print("\nList of district preference :- ", "\n")
    display_table(booking_details["district_ids"], exclude_keys="district_id")

    if booking_details["pin_codes"]:
        print("\nList of pin code preference. "
              "\n\n PLEASE ENSURE THAT YOU ARE CONFIDENT ABOUT EXISTENCE OF THESE PINCODES. COWIN4ALL CANNOT VERIFY "
              "THESE !!  ", "\n")
        display_table(booking_details["pin_codes"])

    print("\nList of date preference :- ", "\n")
    display_table(booking_details["dates"], default_attribute_name="Preferred Dates")

    print("\nList of payment preference :- ", "\n")
    display_table(booking_details["payment_types"], default_attribute_name="Preferred Payment")

    print("\nBooking mode preference :- ", "\n")
    display_table([booking_details["booking_mode"]])

    confirmation = select_yes_or_no(message="Confirm")

    return confirmation


def select_yes_or_no(message=None):
    try:
        confirmation = input("{} (type 'y' for Yes and 'n' for No) : ".format(message))
        confirmation = confirmation.strip().lower()
        if confirmation not in ["y", "n"]:
            raise ValueError()
    except (IndexError, ValueError):
        print("Invalid value provided. Kindly re-enter the values !!")
        confirmation = select_yes_or_no(message=message)
    return confirmation


def get_mobile_no():
    mobile = input("Enter mobile number : ")
    try:
        if not re.fullmatch("[0-9]{10}", mobile):
            raise ValueError()
    except Exception as e:
        print("Invalid mobile number provided. Kindly re-enter the number !!")
        mobile = get_mobile_no()
    return mobile


def validate_booking_details(booking_details=None):
    schema = {
        "definitions": {
            "BookingDetails": {
                "type": "object",
                "additionalProperties": False,
                "minProperties": 1,
                "properties": {
                    "mobile_number": {
                        "type": "string",
                        "pattern": "^[0-9]{10}$"
                    },
                    "beneficiaries": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/Beneficiary"
                        }
                    },
                    "preferred_vaccine_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": vaccine_types
                        },
                        "minItems": 1,
                        "uniqueItems": True
                    },
                    "payment_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": payment_types
                        },
                        "minItems": 1,
                        "uniqueItems": True
                    },
                    "district_ids": {
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/DistrictID"
                        }
                    },
                    "pin_codes": {
                        "type": "array", "items": {"type": "integer"}
                    },
                    "dates": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "pattern": "^[0-9]{2}\\-[0-9]{2}\\-2021$"
                        },
                        "minItems": 1,
                        "uniqueItems": True

                    },
                    "booking_mode": {
                        "$ref": "#/definitions/BookingMode"
                    }
                },
                "required": [
                    "beneficiaries",
                    "booking_mode",
                    "dates",
                    "district_ids",
                    "mobile_number",
                    "payment_types",
                    "pin_codes",
                    "preferred_vaccine_types"
                ],
                "title": "BookingDetails"
            },
            "Beneficiary": {
                "type": "object",
                "additionalProperties": False,
                "minProperties": 1,
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "name": {
                        "type": "string"
                    },
                    "age": {
                        "type": "integer",
                        "minimum": min(minimum_age_limits)
                    },
                    "booking_age_limit": {
                        "type": "integer",
                        "enum": minimum_age_limits
                    },
                    "awaited_dose": {
                        "type": "integer",
                        "enum": doses
                    },
                    "last_dose_date": {
                        "oneOf": [
                            {
                                "type": ["string"],
                            },
                            {
                                "type": "null"
                            }
                        ]
                    },
                    "vaccine": {
                        "oneOf": [
                                {
                                    "type": ["string"],
                                    "enum": vaccine_types
                                },
                            {
                                "type": "null"
                            }
                        ]
                    }
                },
                "required": [
                    "age",
                    "awaited_dose",
                    "booking_age_limit",
                    "last_dose_date",
                    "id",
                    "name",
                    "vaccine"
                ],
                "title": "Beneficiary"
            },
            "BookingMode": {
                "type": "object",
                "additionalProperties": False,
                "minProperties": 1,
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": [mode["mode"] for mode in BOOKING_MODES]
                    },
                    "remarks": {
                        "type": "string"
                    }
                },
                "required": [
                    "mode",
                    "remarks"
                ],
                "title": "BookingMode"
            },
            "DistrictID": {
                "type": "object",
                "additionalProperties": False,
                "minProperties": 1,
                "properties": {
                    "district_id": {
                        "type": "integer"
                    },
                    "district_name": {
                        "type": "string"
                    }
                },
                "required": [
                    "district_id",
                    "district_name"
                ],
                "title": "DistrictID"
            }
        },
        "$ref": "#/definitions/BookingDetails"
    }

    jsonschema.validate(schema=schema, instance=booking_details)
    validate_dose_booking_date(beneficiaries=booking_details["beneficiaries"],
                               booking_dates=booking_details["dates"])


def validate_dose_booking_date(beneficiaries=None, booking_dates=None):
    error = ""
    for beneficiary in beneficiaries:
        if beneficiary.get("awaited_dose") > 1:
            invalid_dates = []
            dose = beneficiary.get("awaited_dose")
            vaccine = beneficiary.get("vaccine")
            last_dose_date = datetime.strptime(beneficiary.get["last_dose_date"], "%d-%m-%Y")
            dose_gap = VACCINATION_DOSE_DATES[vaccine]["dose{}_date".format(dose)]
            name = beneficiary.get("name")
            for date in booking_dates:
                date = datetime.strptime(date, "%d-%m-%Y")
                if (date - last_dose_date).days < dose_gap:
                    invalid_dates.append(date)

            valid_date = datetime.strftime(last_dose_date + timedelta(days=dose_gap), "%d-%m-%Y")
            if invalid_dates:
                error += "Beneficiary '{beneficiary}' has taken dose {dose} of {vaccine} vaccine and it is mandatory " \
                         "to wait for {days} days before next  dosage. The following dates : {dates} are not valid " \
                         "for the given beneficiary. \n Valid dates for the beneficiary is any day post " \
                         "{valid_date}\n\n" \
                         "".format(beneficiary=name, dose=dose-1,
                                   vaccine=vaccine, days=dose_gap, dates=invalid_dates, valid_date=valid_date)

    if error:
        error += "Please change the booking dates and try again!! "
        raise Exception(error)


def get_booking_details(client=None, booking_details=None):

    if not booking_details:

        if not client:
            mobile_number = get_mobile_no()
            client = APIClient(mobile_no=mobile_number)

        booking_details = {"mobile_number": client.mobile}

        retrieved_beneficiaries = client.get_beneficiaries()

        beneficiaries = []

        if not retrieved_beneficiaries:
            print("No beneficiary is registered in the CoWIN site. Kindly register the beneficiaries directly through "
                  "the CoWIN site and run cowin4all.")
            return

        print("\nCollecting initial details ... !!\n")
        for b in retrieved_beneficiaries:
            age = get_possible_age(b["birth_year"])
            dose = None
            vaccine = None
            booking_age_limit = None

            if age in minimum_age_limits:
                # This is required, since age is calculated only based on the year that is provided from CoWIn.
                # Hence it is not possible to determine the exact age if it falls in the border range of
                # both categories. Hence the below ask.
                age = input("Please type the actual age of beneficiary '{}' : ".format(b["name"]))

            if age >= 45:
                booking_age_limit = 45
            elif 18 <= age <= 44:
                booking_age_limit = 18
            else:
                print("Beneficiary '{}' is not eligible to be vaccinated as on date. Skipping the beneficiary."
                      "".format(b["name"]))
                continue

            last_dose_date = None
            if b["dose1_date"] and b["dose2_date"]:
                vaccine = b["vaccine"].lower().strip()
                dose = "completed"
                last_dose_date = b["dose2_date"]
            elif not b["dose1_date"]:
                vaccine = None
                dose = 1
            else:
                vaccine = b["vaccine"].lower().strip()
                dose = 2
                last_dose_date = b["dose1_date"]

            if dose != "completed":
                beneficiaries.append({"id": b["beneficiary_reference_id"],
                                      "name": b["name"],
                                      "age": age,
                                      "booking_age_limit": booking_age_limit,
                                      "awaited_dose": dose,
                                      "last_dose_date": last_dose_date,
                                      "vaccine": vaccine})

        if not beneficiaries:
            print("All beneficiaries have successfully completed their vaccination. "
                  "There is nothing further to be done !! ")
            return

        selected_beneficiaries = beneficiaries

        # if there is only one beneficiary selection of beneficiary is required
        if len(beneficiaries) != 1:
            selected_beneficiaries = select_beneficiaries(beneficiaries)

        booking_details["beneficiaries"] = selected_beneficiaries

        if selected_beneficiaries[0]["awaited_dose"] == 2:
            booking_details["preferred_vaccine_types"] = [selected_beneficiaries[0]["vaccine"]]
        else:
            preferred_vaccine_types = select_vaccine()
            booking_details["preferred_vaccine_types"] = preferred_vaccine_types

        payment_type = select_payment_type()
        booking_details["payment_types"] = payment_type
        state_ids = [s["state_id"] for s in select_state(client=client)]
        districts = select_district(client=client, state_ids=state_ids)
        booking_details["district_ids"] = districts
        booking_details["pin_codes"] = select_pin_code()

        dates = select_dates(beneficiaries=booking_details["beneficiaries"])

        if not dates:
            print("Sure !! Exiting !! ")
            return {}

        booking_details["dates"] = dates

        booking_mode = select_booking_mode()
        booking_details["booking_mode"] = booking_mode

    try:
        validate_booking_details(booking_details=booking_details)
        confirmation = confirm_booking_details(booking_details=booking_details)
        if confirmation == "n":
            response = select_yes_or_no(message="Do you want to re-enter the booking details ?")
            if response == "n":
                print("Sure !! Exiting !! ")
                return {}
            else:
                booking_details = get_booking_details(client=client)
    except ValidationError as e:
        print("There was some error in the previously generated booking information. Error : {}".format(e))
        response = select_yes_or_no(message="Do you want to re-enter the booking details ?")
        if response == "n":
            print("Sure !! Exiting !! ")
            return {}
        else:
            booking_details = get_booking_details(client=client)

    return booking_details


def get_platform():
    platform = sys.platform
    if platform in ('win32', 'cygwin'):
        return 'windows'
    elif platform == 'darwin':
        return 'macosx'
    elif platform.startswith('linux'):
        path = str(subprocess.check_output('which python3', shell=True))
        if "com.termux" in path:
            return "android"
        else:
            return "linux"
    elif platform.startswith('freebsd'):
        return 'linux'
    return 'unknown'


