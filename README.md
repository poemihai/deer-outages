# DEER power outages – Home Assistant
### ⚠️ Important Migration Notes (Breaking Changes)

If you have existing automations built on earlier versions of this integration, please take note of the following behavior changes:

1. **`current_outage_end` sensor behavior**:
   * **Previously:** This sensor only held a timestamp during an active outage (remaining `unknown` otherwise).
   * **Now:** It displays the end time of the active outage or, **if none is active, the end time of the next scheduled outage**. Automations that rely on this sensor changing from `unknown` to a valid date to detect an active outage will trigger prematurely as soon as a future outage is announced.
2. **Detecting an active outage**:
   * To trigger actions strictly when power goes out or comes back, use the dedicated **`binary_sensor.…_power_outage_now`** entity, which switches to `on` at the exact start time and back to `off` when the outage ends.
3. **New events for updates and cancellations**:
   * Alongside `deer_outages_new_outage`, the integration now fires **`deer_outages_updated`** (when an outage is rescheduled) and **`deer_outages_cancelled`** (when an outage is removed). Update your notification and preventive automations to listen to these events as well (e.g., to revert preventive actions if an outage is cancelled).

[Magyar](#magyar) | [Română](#română) | [English](#english)

---

## Magyar

A **Distribuție Energia Electrică Romania (DEER)** tervezett áramszünetei és üzemzavarai a Home Assistantban, **a saját címedre szűrve**. Szól, ha holnap nem lesz áram az utcádban, a naptárban mutatja a leállásokat, és a leállás kezdetekor és végén pontosan vált.

Nem kell hozzá se fiók, se jelszó. A DEER nyilvános adatait olvassa, ugyanazt, amit a [DEER áramszünet-oldala](https://www.distributie-energie.ro/intreruperi-deer/) mutat.

**Megyék:** Alba, Bihar, Beszterce-Naszód, Brăila, Brassó, Buzău, Kolozs, Kovászna, Dâmbovița, Galați, Hargita, Máramaros, Maros, Prahova, Szilágy, Szatmár, Szeben, Vrancea.

### Telepítés

**HACS-szal (ajánlott)**

1. HACS → jobb felül a három pont → **Egyéni tárolók** (Custom repositories).
2. Tároló: `https://github.com/poemihai/deer-outages`, típus: **Integráció**.
3. Keresd meg a „DEER” integrációt, **Letöltés**, majd indítsd újra a Home Assistantot.

**Kézzel:** másold a `custom_components/deer_outages` mappát a Home Assistant `config/custom_components/` mappájába, és indítsd újra.

### Beállítás

**Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása → DEER power outages**

- **Megye**, **település**: a települést írhatod románul vagy magyarul is (`Târgu Secuiesc` vagy `Kézdivásárhely`, `Sfântu Gheorghe` vagy `Sepsiszentgyörgy`). Az ékezet és a kis- és nagybetű nem számít.
- **Utcák** (nem kötelező): vesszővel elválasztva, például `Gábor Áron, Ady Endre`. Üresen hagyva az egész település leállásait figyeli.

Több címet is felvehetsz (például a szüleidét). A címet (megye, település, utcák) később is módosíthatod a fogaskerék ikonnal (**Reconfigure**).

### Mit kapsz?

| Entitás | Mit mutat |
| --- | --- |
| `binary_sensor.…_aramszunet_most` | Be van kapcsolva, amíg leállás tart a címeden (tervezett vagy üzemzavar). Pontosan a kezdéskor és a befejezéskor vált. |
| `sensor.…_kovetkezo_aramszunet` | A legközelebbi, szigorúan jövőbeni leállás kezdete. Tulajdonságai: `end`, `start_utc`, `end_utc`, `end_known`, `type`, `addresses`, `message`, `count`, `outages`. |
| `sensor.…_sfarsitul_intreruperii_curente` | Sfârșitul incidentului activ vagy, în lipsa acestuia, sfârșitul următoarei întreruperi. Atribute: `type`, `end_known`, `ongoing`, `reported_end`, `estimated_end`, `addresses`, `message`, `count`. |
| `binary_sensor.…_korzet_erintett` | Be van kapcsolva, ha a DEER a mostani vagy következő leállásnál csak egy egész települést/körzetet jelölt meg (nem derül ki, hogy a te utcád benne van-e). |
| `calendar.…_aramszunetek` | Minden leállás eseményként, az érintett címekkel. |

Új leállásnál a Home Assistant `deer_outages_new_outage`, megváltozott leállásnál `deer_outages_updated`, törölt vagy eltűnt leállásnál pedig `deer_outages_cancelled` eseményt küld. Az első lekérdezés és az újraindítás alapállapotot rögzít; a már ismert leállásokat nem jelzi újra.

**Jó tudni:**

- Ha a DEER egy egész falura vagy körzetre (pl. `ZONA PT 7`) jelent leállást, abból nem derül ki, hogy a te utcád benne van-e. Ezeket biztonságból mindig mutatja, és ilyenkor `area_only: true`.
- A települést beállíthatod községre vagy falura is: a „Község, Falu, Utca” formában bejelentett leállásokat mindkét esetben megtalálja.
- Az üzemzavaroknak gyakran nincs még befejezési ideje. Ilyenkor 2 órát feltételez, amíg a DEER meg nem adja; amíg az üzemzavar a feedben van, a szenzorok folyamatban lévőként mutatják.
- 30 percenként frissít. Ha a DEER oldala nem érhető el, legfeljebb 3 óráig az utolsó jó adatot mutatja (`stale: true`).

### Értesítés példa

```yaml
alias: Áramszünet értesítő
triggers:
  - trigger: event
    event_type: deer_outages_new_outage
actions:
  - action: notify.mobile_app_telefonom
    data:
      title: ⚡ Áramszünet
      message: "{{ trigger.event.data.message }}"
```

Az esemény adatai: `message`, `type` (`planned` / `incident`), `start`, `end`, `start_utc`, `end_utc`, `end_known`, `addresses`, `area_only`, `match_confidence` (`exact_street` / `whole_area` / `locality`), `previous` (updated/cancelled eseményeknél), `county`, `locality`, `streets`. A `start`/`end` romániai időben van, a `start_utc`/`end_utc` UTC-ben.

---

## Română

Întreruperile programate și incidentele **Distribuție Energie Electrică Romania (DEER)** în Home Assistant, **filtrate pentru adresa ta**: te anunță când nu ai curent pe strada ta, arată întreruperile în calendar exact la începutul și la sfârșitul unei întreruperi.

Nu e nevoie de cont sau parolă. Citește datele publice afișate pe [pagina de întreruperi DEER](https://www.distributie-energie.ro/intreruperi-deer/).

**Județe:** Alba, Bihor, Bistrița-Năsăud, Brăila, Brașov, Buzău, Cluj, Covasna, Dâmbovița, Galați, Harghita, Maramureș, Mureș, Prahova, Sălaj, Satu Mare, Sibiu, Vrancea.

### Instalare

**Cu HACS (recomandat)**

1. HACS → cele trei puncte din dreapta-sus → **Repozitorii personalizate** (Custom repositories).
2. Repozitoriu: `https://github.com/poemihai/deer-outages`, tip: **Integrare**.
3. Caută integrarea „DEER”, **Descarcă**, apoi repornește Home Assistant.

**Manual:** copiază folderul `custom_components/deer_outages` în `config/custom_components/` din Home Assistant și repornește.

### Configurare

**Setări → Dispozitive și servicii → Adaugă integrare → DEER**

- **Județ**, **localitate**: poți scrie localitatea în română sau maghiară (`Târgu Secuiesc` sau `Kézdivásárhely`, `Sfântu Gheorghe` sau `Sepsiszentgyörgy`). Diacriticele és literele mari/mici nu contează.
- **Străzi** (opțional): separate prin virgulă, de exemplu `Gábor Áron, Ady Endre`. Dacă le lași goale, urmărești întreruperile din toată localitatea.

Poți adăuga mai multe adrese (de exemplu a părinților). Adresa completă (județ, localitate, străzi) se poate modifica ulterior din pictograma cu rotiță (**Reconfigure**).

### Ce primești?

| Entitate | Ce arată |
| --- | --- |
| `binary_sensor.…_intrerupere_acum` | Pornit cât timp există o întrerupere la adresa ta (programată sau incident). Comută exact la începutul și sfârșitul unei întreruperi. |
| `sensor.…_urmatoarea_intrerupere` | Începutul următoarei întreruperi, strict în viitor. Atribute: `end`, `start_utc`, `end_utc`, `end_known`, `type`, `addresses`, `message`, `count`, `outages`. |
| `sensor.…_sfarsitul_intreruperii_curente` | Sfârșitul incidentului activ sau, în lipsa acestuia, sfârșitul următoarei întreruperi. Atribute: `type`, `end_known`, `ongoing`, `reported_end`, `estimated_end`, `addresses`, `message`, `count`. |
| `binary_sensor.…_zona_afectata` | Pornit dacă DEER a marcat o întreagă zonă/localitate pentru întrerupere (nu se știe dacă strada ta este inclusă). |
| `calendar.…_intreruperi` | Toate întreruperile ca evenimente, cu adresele afectate. |

La o nouă întrerupere, Home Assistant trimite un eveniment `deer_outages_new_outage`; pentru o întrerupere modificată, trimite `deer_outages_updated`; iar pentru o întrerupere anulată sau dispărută, trimite `deer_outages_cancelled`. Prima interogare și repornirea salvează starea inițială; întreruperile deja cunoscute nu sunt raportate din nou.

**De știut:**

- Dacă DEER raportează o întrerupere pentru o întreagă localitate (ex. `ZONA PT 7`), nu se știe dacă strada ta este inclusă. Acestea sunt întotdeauna afișate pentru precauție, având `area_only: true`.
- Poți seta localitatea ca și comună sau sat: întreruperile raportate în formatul „Comuna, Sat, Stradă” vor fi găsite în ambele cazuri.
- Incidentele nu au întotdeauna o oră de sfârșit definită. În acest caz, se presupune o durată de 2 ore, până când DEER furnizează informațiile; cât timp incidentul este prezent în feed, senzorii vor arăta că este în curs de desfășurare.
- Se actualizează la fiecare 30 de minute. Dacă pagina DEER nu este disponibilă, va afișa ultima dată bună timp de maximum 3 ore (`stale: true`).

### Exemplu de notificare

```yaml
alias: Notificare întrerupere curent
triggers:
  - trigger: event
    event_type: deer_outages_new_outage
actions:
  - action: notify.mobile_app_telefonom
    data:
      title: ⚡ Întrerupere curent
      message: "{{ trigger.event.data.message }}"
```

Datele evenimentului: `message`, `type` (`planned` / `incident`), `start`, `end`, `start_utc`, `end_utc`, `end_known`, `addresses`, `area_only`, `match_confidence` (`exact_street` / `whole_area` / `locality`), `previous` (pentru evenimente actualizate/anulate), `county`, `locality`, `streets`. `start`/`end` sunt în ora României, iar `start_utc`/`end_utc` sunt în UTC.

---

## English

The planned and unplanned power outages from **Distribuție Energie Electrică Romania (DEER)** in Home Assistant, **filtered to your address**: get notified when there is a power outage on your street, see the outages in the calendar, exactly at the start and end of an outage.

No account or password is needed. It reads the public data displayed on the [DEER outages page](https://www.distributie-energie.ro/intreruperi-deer/).

**Counties:** Alba, Bihor, Bistrița-Năsăud, Brăila, Brașov, Buzău, Cluj, Covasna, Dâmbovița, Galați, Harghita, Maramureș, Mureș, Prahova, Sălaj, Satu Mare, Sibiu, Vrancea.

### Installation

**With HACS (recommended)**

1. HACS → top right three dots → **Custom repositories**.
2. Repository: `https://github.com/poemihai/deer-outages`, type: **Integration**.
3. Find the "DEER" integration, **Download**, then restart Home Assistant.

**Manually:** copy the `custom_components/deer_outages` folder to the Home Assistant `config/custom_components/` folder, and restart.

### Configuration

**Settings → Devices & Services → Add Integration → DEER power outages**

- **County**, **locality**: you can write the locality in Romanian or Hungarian (`Târgu Secuiesc` or `Kézdivásárhely`, `Sfântu Gheorghe` or `Sepsiszentgyörgy`). Diacritics and uppercase/lowercase letters do not matter.
- **Streets** (optional): separated by commas, e.g. `Gábor Áron, Ady Endre`. If left empty, it monitors outages for the entire locality.

You can add multiple addresses (e.g. your parents'). The full address (county, locality, streets) can be modified later using the gear icon (**Reconfigure**).

### What do you get?

| Entity | What it shows |
| --- | --- |
| `binary_sensor.…_power_outage_now` | On as long as there is an outage at your address (planned or unplanned). Switches exactly at the start and end of an outage. |
| `sensor.…_next_power_outage` | The start of the next strictly future outage. Attributes: `end`, `start_utc`, `end_utc`, `end_known`, `type`, `addresses`, `message`, `count`, `outages`. |
| `sensor.…_current_outage_end` | The end of the active incident or, if none, the end of the next outage. Attributes: `type`, `end_known`, `ongoing`, `reported_end`, `estimated_end`, `addresses`, `message`, `count`. |
| `binary_sensor.…_area_affected` | On if DEER marked an entire area/locality for outage (it is not known if your street is included). |
| `calendar.…_power_outages` | All outages as events, with affected addresses. |

On a new outage, Home Assistant sends a `deer_outages_new_outage` event; on a changed outage, it sends `deer_outages_updated`; and on a cancelled or disappeared outage, it sends `deer_outages_cancelled`. The first query and the restart save the initial state; already known outages are not reported again.

**Good to know:**

- If DEER reports an outage for an entire locality (e.g. `ZONA PT 7`), it is not known if your street is included. These are always displayed for safety, with `area_only: true`.
- You can set the locality as a commune or village: outages reported in the format "Commune, Village, Street" will be found in both cases.
- Incidents often do not have an end time yet. In this case, a duration of 2 hours is assumed, until DEER provides the information; as long as the incident is present in the feed, the sensors will show it as ongoing.
- Updates every 30 minutes. If the DEER page is not reachable, it will show the last good data for up to 3 hours (`stale: true`).

### Notification example

```yaml
alias: Power outage notifier
triggers:
  - trigger: event
    event_type: deer_outages_new_outage
actions:
  - action: notify.mobile_app_telefonom
    data:
      title: ⚡ Power Outage
      message: "{{ trigger.event.data.message }}"
```

Event data: `message`, `type` (`planned` / `incident`), `start`, `end`, `start_utc`, `end_utc`, `end_known`, `addresses`, `area_only`, `match_confidence` (`exact_street` / `whole_area` / `locality`), `previous` (for updated/cancelled events), `county`, `locality`, `streets`. `start`/`end` are in Romanian time, and `start_utc`/`end_utc` are in UTC.
