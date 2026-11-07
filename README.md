# DEER áramszünetek – Home Assistant

[Magyar](#magyar) | [Română](#română) | [English](#english)

---

## Magyar

A **Distribuție Energie Electrică Romania (DEER)** tervezett áramszünetei és üzemzavarai a Home Assistantban, **a saját címedre szűrve**. Szól, ha holnap nem lesz áram az utcádban, a naptárban mutatja a leállásokat, és a leállás kezdetekor és végén pontosan vált.

Nem kell hozzá se fiók, se jelszó. A DEER nyilvános adatait olvassa, ugyanazt, amit a [DEER áramszünet-oldala](https://www.distributie-energie.ro/intreruperi-deer/) mutat.

**Megyék:** Alba, Bihar, Beszterce-Naszód, Brăila, Brassó, Buzău, Kolozs, Kovászna, Dâmbovița, Galați, Hargita, Máramaros, Maros, Prahova, Szilágy, Szatmár, Szeben, Vrancea.

### Telepítés

**HACS-szal (ajánlott)**

1. HACS → jobb felül a három pont → **Egyéni tárolók** (Custom repositories).
2. Tároló: `https://github.com/poemihai/deer-outages`, típus: **Integráció**.
3. Keresd meg a „DEER” integrációt, **Letöltés**, majd indítsd újra a Home Assistantot.

**Kézzel:** másold a `custom_components/deer_outages` mappát a Home Assistant `config/custom_components/` mappájába, és indítsd újra.

### Beállítás

**Beállítások → Eszközök és szolgáltatások → Integráció hozzáadása → DEER áramszünetek**

- **Megye**, **település**: a települést írhatod románul vagy magyarul is (`Târgu Secuiesc` vagy `Kézdivásárhely`, `Sfântu Gheorghe` vagy `Sepsiszentgyörgy`). Az ékezet és a kis- és nagybetű nem számít.
- **Utcák** (nem kötelező): vesszővel elválasztva, például `Gábor Áron, Ady Endre`. Üresen hagyva az egész település leállásait figyeli.

Több címet is felvehetsz (például a szüleidét). A címet (megye, település, utcák) később is módosíthatod a fogaskerék ikonnal (**Reconfigure**).

### Mit kapsz?

| Entitás | Mit mutat |
| --- | --- |
| `binary_sensor.…_aramszunet_most` | Be van kapcsolva, amíg leállás tart a címeden (tervezett vagy üzemzavar). Pontosan a kezdéskor és a befejezéskor vált. |
| `sensor.…_kovetkezo_aramszunet` | A következő (vagy a mostani) leállás kezdete. Tulajdonságai: `end`, `type`, `addresses`, `message` (kész szöveg értesítéshez), `count`, `outages`. |
| `sensor.…_aramszunet_vege` | A mostani (vagy a következő) leállás vége. Tulajdonságai: `type`, `end_known`, `addresses`, `message`, `count`. |
| `binary_sensor.…_korzet_erintett` | Be van kapcsolva, ha a DEER a mostani vagy következő leállásnál csak egy egész települést/körzetet jelölt meg (nem derül ki, hogy a te utcád benne van-e). |
| `calendar.…_aramszunetek` | Minden leállás eseményként, az érintett címekkel. |

Új leállásnál a Home Assistant egy `deer_outages_new_outage` eseményt küld. Az első lekérdezésnél és újraindítás után nem jelzi újra a már ismert leállásokat.

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

Az esemény adatai: `message`, `type` (`planned` / `incident`), `start`, `end`, `start_utc`, `end_utc`, `end_known`, `addresses`, `area_only`, `county`, `locality`, `streets`. A `start`/`end` romániai időben van, a `start_utc`/`end_utc` UTC-ben.

---

## Română

Întreruperile programate și incidentele **Distribuție Energie Electrică Romania (DEER)** în Home Assistant, **filtrate pentru adresa ta**: te anunță când mâine nu ai curent pe strada ta, arată întreruperile în calendar și comută exact la începutul și la sfârșitul unei întreruperi.

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

- **Județ**, **localitate**: poți scrie localitatea în română sau maghiară (`Târgu Secuiesc` sau `Kézdivásárhely`, `Sfântu Gheorghe` sau `Sepsiszentgyörgy`). Diacriticele și literele mari/mici nu contează.
- **Străzi** (opțional): separate prin virgulă, de exemplu `Gábor Áron, Ady Endre`. Dacă le lași goale, urmărești întreruperile din toată localitatea.

Poți adăuga mai multe adrese (de exemplu a părinților). Adresa completă (județ, localitate, străzi) se poate modifica ulterior din pictograma cu rotiță (**Reconfigure**).

### Ce primești?

| Entitate | Ce arată |
| --- | --- |
| `binary_sensor.…_intrerupere_acum` | Pornit cât timp există o întrerupere la adresa ta (programată sau incident). Comută exact la început și la sfârșit. |
| `sensor.…_urmatoarea_intrerupere` | Începutul următoarei (sau actualei) întreruperi. Atribute: `end`, `type`, `addresses`, `message`, `count`, `outages`. |
| `sensor.…_sfarsitul_intreruperii_curente` | Sfârșitul întreruperii curente (sau al următoarei). Atribute: `type`, `end_known`, `addresses`, `message`, `count`. |
| `binary_sensor.…_zona_afectata` | Pornit când DEER a anunțat doar o localitate/zonă întreagă la întreruperea curentă sau următoare (nu se știe dacă strada ta e inclusă). |
| `calendar.…_intreruperi_curent` | Toate întreruperile ca evenimente, cu adresele afectate. |

La o întrerupere nouă, Home Assistant trimite evenimentul `deer_outages_new_outage`. Întreruperile deja anunțate nu sunt re-anunțate la prima interogare sau după repornire.

**Bine de știut:**

- Dacă DEER anunță o întrerupere pentru un sat sau o zonă întreagă (ex. `ZONA PT 7`), nu se știe dacă strada ta e inclusă. Din precauție, este afișată mereu, cu `area_only: true`.
- Poți configura fie comuna, fie satul: întreruperile anunțate ca „Comuna, Satul, Strada” sunt găsite în ambele cazuri.
- Incidentele adesea nu au încă oră de final. Până o primești, se presupune 2 ore; cât timp incidentul rămâne în feed, senzorii îl arată ca în desfășurare.
- Reîmprospătare la 30 de minute. Dacă pagina DEER e indisponibilă, ultimele date bune sunt afișate până la 3 ore (`stale: true`).

### Exemplu de notificare

```yaml
alias: Notificare întrerupere curent
triggers:
  - trigger: event
    event_type: deer_outages_new_outage
actions:
  - action: notify.mobile_app_telefonul_meu
    data:
      title: ⚡ Întrerupere curent
      message: "{{ trigger.event.data.message }}"
```

Datele evenimentului: `message`, `type` (`planned` / `incident`), `start`, `end`, `start_utc`, `end_utc`, `end_known`, `addresses`, `area_only`, `county`, `locality`, `streets`. `start`/`end` sunt în ora României, `start_utc`/`end_utc` în UTC.

---

## English

Planned power outages and incidents of **Distribuție Energie Electrică Romania (DEER)** in Home Assistant, **filtered for your address**: it warns you when your street will have no power tomorrow, shows the outages in the calendar, and switches exactly when an outage starts and ends.

No account or password needed. It reads the public data shown on the [DEER outage page](https://www.distributie-energie.ro/intreruperi-deer/).

**Counties:** Alba, Bihor, Bistrița-Năsăud, Brăila, Brașov, Buzău, Cluj, Covasna, Dâmbovița, Galați, Harghita, Maramureș, Mureș, Prahova, Sălaj, Satu Mare, Sibiu, Vrancea.

### Installation

**With HACS (recommended)**

1. HACS → the three dots in the top right → **Custom repositories**.
2. Repository: `https://github.com/poemihai/deer-outages`, type: **Integration**.
3. Find the „DEER” integration, **Download**, then restart Home Assistant.

**Manually:** copy the `custom_components/deer_outages` folder into `config/custom_components/` of Home Assistant and restart.

### Configuration

**Settings → Devices & services → Add integration → DEER**

- **County**, **locality**: the locality can be typed in Romanian or Hungarian (`Târgu Secuiesc` or `Kézdivásárhely`, `Sfântu Gheorghe` or `Sepsiszentgyörgy`). Accents and letter case do not matter.
- **Streets** (optional): comma separated, for example `Gábor Áron, Ady Endre`. Leave empty to follow the whole locality.

You can add several addresses (for example your parents'). The whole address (county, locality, streets) can be changed later from the gear icon (**Reconfigure**).

### What you get

| Entity | What it shows |
| --- | --- |
| `binary_sensor.…_power_outage_now` | On while an outage is going on at your address (planned or incident). Switches exactly when it starts and ends. |
| `sensor.…_next_power_outage` | The start of the next (or the current) outage. Attributes: `end`, `type`, `addresses`, `message` (ready text for notifications), `count`, `outages`. |
| `sensor.…_current_outage_end` | The end of the current (or the next) outage. Attributes: `type`, `end_known`, `addresses`, `message`, `count`. |
| `binary_sensor.…_whole_area_affected` | On when DEER only named a whole locality or zone for the current or next outage (it is not known whether your street is included). |
| `calendar.…_power_outages` | All outages as events, with the affected addresses. |

On a new outage, Home Assistant fires a `deer_outages_new_outage` event. Outages that were already announced are not re-announced on the first fetch or after a restart.

**Good to know:**

- When DEER announces an outage for a whole village or zone (e.g. `ZONA PT 7`), it cannot be known whether your street is included. These are always shown, with `area_only: true`.
- You can configure either the commune or the village: outages written as „Commune, Village, Street” are found in both cases.
- Incidents often have no end time yet. Until one is given, 2 hours are assumed; while the incident stays in the feed, the sensors show it as ongoing.
- Refreshes every 30 minutes. If the DEER page is unreachable, the last good data is kept for up to 3 hours (`stale: true`).

### Notification example

```yaml
alias: Power outage notification
triggers:
  - trigger: event
    event_type: deer_outages_new_outage
actions:
  - action: notify.mobile_app_my_phone
    data:
      title: ⚡ Power outage
      message: "{{ trigger.event.data.message }}"
```

Event data: `message`, `type` (`planned` / `incident`), `start`, `end`, `start_utc`, `end_utc`, `end_known`, `addresses`, `area_only`, `county`, `locality`, `streets`. `start`/`end` are in Romanian time, `start_utc`/`end_utc` in UTC.

---

*Ez egy nem hivatalos, közösségi projekt, nincs kapcsolatban a Distribuție Energie Electrică Romania-val. / Proiect neoficial, neafiliat cu Distribuție Energie Electrică Romania. / Unofficial project, not affiliated with Distribuție Energie Electrică Romania.*

*A kód nagy részét Claude (Anthropic) segítségével írtuk. / Developed with the help of Claude (Anthropic).*
