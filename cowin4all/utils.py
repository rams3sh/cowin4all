from threading import Thread
from datetime import datetime, timedelta
from copy import deepcopy
import os
import tabulate

from settings import AUDIO_FILE_PLAYING_COMMAND, BOOKING_ALERT_AUDIO_PATH
from cowin4all_sdk.api import APIClient
from cowin4all_sdk.utils import refresh_token
from cowin4all_sdk.constants import vaccine_types, minimum_age_limits, payment_types


def play_sound(file_path):
    os.system(AUDIO_FILE_PLAYING_COMMAND.format(audio_file_path=file_path))


def booking_alert():
    siren = Thread(target=play_sound, args=[BOOKING_ALERT_AUDIO_PATH],
                   daemon=True)
    siren.start()


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
    except (AttributeError):
        header = ["S.No"] + [default_attribute_name or "Value"]
        rows = [[i+1, d] for i, d in zip(range(len(dict_list)), dict_list)]
    print("\n", tabulate.tabulate(rows, header, tablefmt="grid"))


def get_possible_age(year):
    return datetime.now().year - int(year)


def validate_selected_beneficiaries(beneficiaries):
    booking_age_limit = set()
    awaited_dose = set()
    vaccine = set()
    for b in beneficiaries:
        booking_age_limit.add(b["booking_age_limit"])
        awaited_dose.add(b["awaited_date"])
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


def select_beneficiaries(beneficiaries):
    display_table(beneficiaries)
    s_nos = input("Enter S.No(s) of the beneficiaries for slot booking (in case of multiple "
                  "beneficiaries use ',' to separate S.No(s) : ")
    s_nos = set([int(s.strip()) for s in s_nos.split(",")])
    try:
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
        selected_districts = [districts[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_districts = select_district(client=client, state_ids=state_ids)
    return selected_districts


def select_pin_code():
    message = "Enter pin code belonging to district(s) selected previously, in case you would want to narrow down your" \
              " location of vaccine, else just press enter. (in case of multiple " \
              "pin codes use ',' to separate them) : "
    selected_pin_codes = input(message)

    if selected_pin_codes:
        try:
            selected_pin_codes = [int(p.strip()) for p in selected_pin_codes]
        except (IndexError, ValueError):
            print("Invalid pin code(s) provided. Kindly re-enter the values !!")
            pin_codes = select_pin_code()

    return selected_pin_codes


def select_vaccine():
    display_table(vaccine_types, default_attribute_name="Vaccine Name")
    s_nos = input("Enter S.No(s) of the vaccine type(s) to be considered as option for booking (in case of multiple "
                  "vaccine types use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
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


def select_dates():
    dates = generate_date(days_range=4)
    display_table(dates, default_attribute_name="Date (dd-mm-yyyy)")
    s_nos = input("Enter S.No(s) of the date(s) to be considered as option for booking (in case of multiple "
                  "dates use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        selected_dates = [dates[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_dates = select_dates()

    return selected_dates


def select_payment_type():
    display_table(payment_types, default_attribute_name="Payment Type")
    s_nos = input("Enter S.No(s) of the payment type(s) to be considered as option for booking (in case of multiple "
                  "payment types use ',' to separate S.No(s) : ")
    try:
        s_nos = set([int(s.strip()) for s in s_nos.split(",")])
        selected_payment_types = [payment_types[s - 1] for s in s_nos]
    except (IndexError, ValueError):
        print("Invalid S.No(s) provided. Kindly re-enter the values !!")
        selected_payment_types = select_payment_type()

    return selected_payment_types


def get_booking_details():
    mobile_number = input("Enter mobile number : ")
    client = APIClient(mobile_no=mobile_number)
    refresh_token(client=client)
    retrieved_beneficiaries = client.get_beneficiaries()

    booking_details = {"mobile_number": mobile_number}

    beneficiaries = []

    if not retrieved_beneficiaries:
        print("No beneficiary is registered in the CoWIN site. Kindly register the beneficiaries directly through the "
              "CoWIN site and run cowin4all.")
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

        if b["dose1_date"] and b["dose2_date"]:
            vaccine = b["vaccine"].lower().strip()
            dose = "completed"
        elif not b["dose1_date"]:
            vaccine = None
            dose = 1
        else:
            vaccine = b["vaccine"].lower().strip()
            dose = 2

        if dose != "completed":
            beneficiaries.append({"id": b["beneficiary_reference_id"],
                                  "name": b["name"],
                                  "age": age,
                                  "booking_age_limit": booking_age_limit,
                                  "awaited_dose": dose,
                                  "vaccine": vaccine})
        if not beneficiaries:
            print("All beneficiaries have successfully completed their vaccination. "
                  "There is nothing further to be done !! ")
            return

        selected_beneficiaries = beneficiaries

        if len(beneficiaries) != 1:
            selected_beneficiaries = select_beneficiaries(beneficiaries)

        booking_details["beneficiaries"] = selected_beneficiaries

        if selected_beneficiaries[0]["awaited_dose"] == 2:
            booking_details["preferred_vaccine_types"] = selected_beneficiaries[0]["vaccine"]
        else:
            preferred_vaccine_types = select_vaccine()
            booking_details["preferred_vaccine_types"] = preferred_vaccine_types

    payment_type = select_payment_type()
    booking_details["payment_type"] = payment_type
    state_ids = [s["state_id"] for s in select_state(client=client)]
    districts = select_district(client=client, state_ids=state_ids)
    booking_details["district_ids"] = districts
    booking_details["pin_codes"] = select_pin_code()
    dates = select_dates()
    booking_details["dates"] = dates

    return booking_details


