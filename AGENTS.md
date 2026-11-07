# AGENTS.md — Instrucțiuni pentru AI (deer-outages)

Acest fișier descrie aplicația și convențiile de lucru în acest repository.
Citește-l înainte de orice modificare de cod.

## Despre proiect

Integrare Home Assistant (custom component, `custom_components/deer_outages`) care
afișează întreruperile de curent **planificate** și **incidentele** de la
**Distribuție Energie Electrică România (DEER)**, filtrate pe adresa utilizatorului.

- Citește feed-ul public DEER (`https://outages.distributie-energie.ro/api`), fără cont.
- Distribuită prin HACS (min. Home Assistant 2025.8.0).
- Proiect neoficial, neafiliat cu DEER.
- Localizare: **română, maghiară, engleză** (README trilingv, `texts.py`, `translations/`).

## Arhitectură

Fluxul datelor:

```
Feed public DEER → api.py (DeerApi, HTTP) → coordinator.py (DataUpdateCoordinator,
polling 30 min) → outages.py (parsing + filtrare pe adresă) → entități
```

| Fișier | Rol |
| --- | --- |
| `api.py` | Client `aiohttp`; endpoint-uri: `/scheduled/{regiune}/0/15`, `/incidents/{regiune}/0` |
| `feed.py` | `FeedCache` per regiune în `hass.data[DOMAIN]`: fetch paralel, 1 retry, fallback pe cache (`degraded`), TTL = `SCAN_INTERVAL` |
| `outages.py` | **Logică pură, fără obiecte Home Assistant** — de testat izolat: normalizare text (fără diacritice), aliasuri localități RO↔HU, parsing `Planned`/`Incident`, select pe stradă/localitate |
| `coordinator.py` | `DataUpdateCoordinator`: polling, detectare întreruperi noi, eveniment, storage, timer la limitele întreruperii |
| `config_flow.py` | UI configurare: județ (dropdown), localitate, străzi (opțional) + options flow (străzi) + `async_step_reconfigure` (întreaga adresă) |
| `diagnostics.py` | Download-diagnostics: intrare, regiune, stare feed, întreruperi, `seen_count` |
| `entity.py` | Clasa de bază pentru entități (device info, atribute comune) |
| `binary_sensor.py` | „Întrerupere acum" (`problem`) + „zonă afectată fără stradă" (`area_only`) |
| `sensor.py` | „Următoarea întrerupere" + „sfârșitul întreruperii curente" (timestamp) |
| `calendar.py` | Calendar cu toate întreruperile |
| `texts.py` | Texte notificări/calendar în funcție de limba HA |
| `const.py` | Constante: 18 județe → 3 regiuni (`TS`, `TN`, `MN`), intervale, evenimente |

## Entități expuse (per adresă configurată)

- `binary_sensor` — „întrerupere acum", `device_class=problem`, atribute `outages`, `message`
- `binary_sensor` — „zonă afectată" (`area_only`): pornit când DEER anunță doar o localitate/zonă întreagă
- `sensor` — „următoarea întrerupere", atribute `end`, `type`, `addresses`, `message`, `count`, `outages`
- `sensor` — „sfârșitul întreruperii curente", atribute `type`, `end_known`, `addresses`, `message`, `count`
- `calendar` — evenimente de întrerupere
- Eveniment HA `deer_outages_new_outage` pentru automatizări/notificări; `as_dict()` conține `start_utc`/`end_utc`

## Reguli de comportament importante

- **Nu reanunța la restart**: întreruperile deja anunțate sunt salvate în `.storage`
  (Store, `STORAGE_VERSION=1`, retenție 30 zile); primul run face doar baseline.
- **Zone întregi** (`ZONA PT 7`, `SAT ...`) → `area_only: true`, afișate preventiv.
- **Incidente fără oră de final** → se presupune 2 ore pentru afișare
  (`INCIDENT_DEFAULT_DURATION`), dar `end_known=False` rămâne „în desfășurare"
  cât timp incidentul e în feed (`_effective_end` în coordinator).
- **Reziliență feed**: dacă API-ul e indisponibil, se păstrează ultimele date până la
  3 ore (`MAX_DATA_AGE`), marcate `stale: true` (proprietatea `stale` a coordinatorului
  acoperă și update-urile `degraded`).
- **Orele din feed** sunt locale România fără offset → `FEED_TIME_ZONE = Europe/Bucharest`.
- **Diacriticele nu contează** la potrivire; localitățile se pot scrie RO sau HU.
- Localitatea configurată poate fi **comuna sau satul**: liniile `COMUNA, SAT, Strada`
  din feed se potrivesc cu ambele (`_split_planned`).
- Polling la 30 min (`SCAN_INTERVAL`); entitățile se reîmprospătează exact la
  începutul/sfârșitul unei întreruperi prin timer programat (`_schedule_boundary`).
- Un `async_unload_entry` oprește și timerul de graniță (`async_shutdown`).

## Testare

- `pytest` + `pytest-homeassistant-custom-component` (`pytest.ini`: `asyncio_mode=auto`).
- Teste: `tests/test_config_flow.py`, `tests/test_init.py`, `tests/test_outages.py`.
- Fixtures cu date reale din feed: `tests/fixtures/scheduled.json`, `incidents.json`.
- API-ul este mock-uit la nivel HTTP (`aioclient_mock`), dar logica de parsing și
  filtrare este testată pe date reale — **nu** cu `Mock()`/`patch()` pe obiecte.
- Atenție în teste: refresh-ul periodic al `DataUpdateCoordinator` e programat cu
  `loop.call_at` (timp monoton) și **nu** pornește la `freezer.tick`; folosește
  `await entry.runtime_data.async_refresh()` când testul are nevoie de un poll.
  Timer-ele de graniță (`async_track_point_in_utc_time`) în schimb pornesc la
  `async_fire_time_changed`.
- **Testele se rulează în Docker** (Linux, mediul nativ HA) — self-contained, de
  la rădăcina repo-ului:

  ```bash
  docker run --rm -v "$PWD:/work" -w /work python:3.13-slim sh -c \
    "apt-get update -qq && apt-get install -y -qq --no-install-recommends gcc libc6-dev && \
     pip install -q -r requirements_test.txt ruff && \
     ruff check custom_components tests && ruff format --check custom_components tests && \
     python -m pytest -q"
  ```

  (`gcc` e necesar doar pentru wheel-ul `lru-dict` pe py313; pe Windows PowerShell
  înlocuiește `$PWD` cu calea repo-ului. CI-ul GitHub rulează aceleași verificări
  pe `ubuntu-latest`.)

## Calitate

- `pyproject.toml`: ruff (`E`, `F`, `I`, `UP`, `B`, `RUF`), line-length 100.
- CI: `.github/workflows/ci.yml` — `ruff check` + `ruff format --check`,
  `hassfest`, `pytest` pe Python 3.13.

## Convenții de cod

- Python cu `from __future__ import annotations`; type hints peste tot.
- Logica de domeniu rămâne în `outages.py`, fără dependențe HA.
- Modificările de text UX trebuie reflectate în toate cele 3 limbi (`texts.py`,
  `translations/en.json`, `hu.json`, `ro.json`, `strings.json`).
- Versiunea se actualizează în `manifest.json`; User-Agent-ul clientului e
  `ha-deer-outages/{version}`.
