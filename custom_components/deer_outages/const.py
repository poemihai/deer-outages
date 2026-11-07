"""Constants for the DEER power outages integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "deer_outages"

API_BASE: Final = "https://outages.distributie-energie.ro/api"
REQUEST_TIMEOUT_SECONDS: Final = 20
SCAN_INTERVAL: Final = timedelta(minutes=30)
# Sensors keep showing the last good data through an outage up to this age.
MAX_DATA_AGE: Final = timedelta(hours=3)
# The feed gives local Romanian times without an offset.
FEED_TIME_ZONE: Final = "Europe/Bucharest"
# Incidents often have no end time yet; assume this long until they get one.
INCIDENT_DEFAULT_DURATION: Final = timedelta(hours=2)
# An incident without an end time stays "ongoing" this long past the poll,
# so the sensors do not turn off between two fetches while it is in the feed.
INCIDENT_ONGOING_EXTENSION: Final = SCAN_INTERVAL

CONF_COUNTY: Final = "county"
CONF_LOCALITY: Final = "locality"
CONF_STREETS: Final = "streets"

EVENT_NEW_OUTAGE: Final = "deer_outages_new_outage"

STORAGE_VERSION: Final = 1
SEEN_RETENTION_DAYS: Final = 30

# County as written in the feed -> (region code, display name).
COUNTIES: Final = {
    "Alba": ("TS", "Alba"),
    "Brasov": ("TS", "Brașov"),
    "Covasna": ("TS", "Covasna"),
    "Harghita": ("TS", "Harghita"),
    "Mures": ("TS", "Mureș"),
    "Sibiu": ("TS", "Sibiu"),
    "Bihor": ("TN", "Bihor"),
    "Bistrita-Nasaud": ("TN", "Bistrița-Năsăud"),
    "Cluj": ("TN", "Cluj"),
    "Maramures": ("TN", "Maramureș"),
    "Satu Mare": ("TN", "Satu Mare"),
    "Salaj": ("TN", "Sălaj"),
    "Braila": ("MN", "Brăila"),
    "Buzau": ("MN", "Buzău"),
    "Dambovita": ("MN", "Dâmbovița"),
    "Galati": ("MN", "Galați"),
    "Prahova": ("MN", "Prahova"),
    "Vrancea": ("MN", "Vrancea"),
}
