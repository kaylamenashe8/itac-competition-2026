import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class User:
    role: str
    api_key: str
    email: str
    password: str


ORGANIZER = User(
    "organizer",
    os.environ["organizer_api_key"],
    os.environ["TEST_USER_EMAIL"],
    os.environ["TEST_USER_PASSWORD"],
)
FAN = User(
    "fan",
    os.environ["fan_api_key"],
    os.environ["TEST_USER_EMAIL"],
    os.environ["TEST_USER_PASSWORD"],
)
