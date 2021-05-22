import os

COWIN4ALL_APP_ROOT_DIRECTORY = os.path.dirname(__file__)
COWIN4ALL_SERVICE_PORT = 8081
POLL_TIME_RANGE = (15.0, 20.0)
LOG_FORMAT = "%(asctime)s — [Module Name: %(name)s] — [PID: %(process)d] — [Thread : %(threadName)s] —  %(levelname)s" \
             " — [Method and Line  No: %(funcName)s:%(lineno)d] — %(message)s"

BOOKING_INFORMATION_FILE = "booking_information.json"
AUTO_TOKEN_REFRESH_ATTEMPTS = 3
AUDIO_FILE_PLAYING_COMMAND = "vlc --intf dummy --play-and-exit {audio_file_path}"

BOOKING_ALERT_AUDIO_PATH = os.path.join("audio", "Siren-SoundBible.com-1094437108.mp3")
OTP_ALERT_AUDIO_PATH = os.path.join("audio", "refresh_OTP.mp3")


BOOKING_MODES = [{"mode": "all", "remarks": "Book only if slots are available for all selected beneficiaries"},
                 {"mode": "first_available",
                  "remarks": "Book for beneficiaries based on WHEREVER slot is available first. "}]
