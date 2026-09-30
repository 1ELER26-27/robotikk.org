"""Generate draft profiles for KY-series Arduino modules we don't own yet.

Reads data/arduino_modules_data/modules.json (private reference data, not in git)
and writes data/arduino_modules_data/genererte-profiler/<slug>/index.md + copies
images, with antall: 0. Output stays under data/ (gitignored) because the images
are scraped from a third-party site with unclear reuse rights — never copy this
output into content/moduler/ (public, git-tracked) without resolving that first.

Modules already curated by hand (KY-001, KY-004) are skipped. Re-run any time new
modules are added to modules.json — existing generated bundles are overwritten.

Usage: python3 scripts/generate_arduino_modules.py
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "arduino_modules_data"
OUTPUT_DIR = DATA_DIR / "genererte-profiler"

# Moduler som allerede finnes som håndlagde sider.
SKIP_MODULE_IDS = {"KY-001", "KY-004"}

# Norsk metadata per modul. Ikke i JSON-kilden, kuratert manuelt.
MODULE_META: dict[str, dict] = {
    "KY-002": dict(tittel="vibrasjonssensor", kategori="Bevegelse", underkategori="Vibrasjon", modultype="Sensor",
                   funksjon="Registrerer vibrasjon eller støt som digital input.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang", sok=["vibrasjon", "støt", "vibration", "shock"]),
    "KY-003": dict(tittel="hallsensor (digital)", kategori="Magnetisk", underkategori="Digital bryter", modultype="Sensor",
                   funksjon="Registrerer nærliggende magnetfelt som digital på/av-brikke (Hall-effekt).", spenning="4,5–24 V (5 V typisk)",
                   grensesnitt="Digital utgang", sok=["hall", "magnet", "magnetisk bryter"]),
    "KY-005": dict(tittel="IR-sender", kategori="Kommunikasjon", underkategori="Infrarødt", modultype="Sender",
                   funksjon="Sender infrarøde signaler, f.eks. til fjernkontrollprotokoller.", spenning="3,3–5 V",
                   grensesnitt="Digital/PWM-styrt IR-signal", sok=["infrarød", "ir", "fjernkontroll"]),
    "KY-006": dict(tittel="passiv summer", kategori="Lyd", underkategori="Passiv summer", modultype="Aktuator",
                   funksjon="Piezosummer som trenger en styrt firkantbølge for å lage lyd i ulike frekvenser.", spenning="1,5–15 V (5 V typisk)",
                   grensesnitt="PWM-styrt lydsignal", sok=["summer", "lyd", "buzzer", "tone"]),
    "KY-008": dict(tittel="lasermodul", kategori="Lys", underkategori="Laser", modultype="Aktuator",
                   funksjon="Sender ut en synlig rød laserstråle når den får strøm.", spenning="5 V",
                   grensesnitt="Digital på/av", sok=["laser", "lys"]),
    "KY-009": dict(tittel="RGB LED (SMD)", kategori="Lys", underkategori="RGB LED", modultype="Aktuator",
                   funksjon="Overflatemontert RGB-LED som styres med tre separate fargekanaler.", spenning="3,3–5 V",
                   grensesnitt="3× PWM-kanaler (R/G/B)", sok=["led", "rgb", "farge"]),
    "KY-010": dict(tittel="fotoavbryter", kategori="Bevegelse", underkategori="Fotoavbryter", modultype="Sensor",
                   funksjon="Registrerer når noe bryter en infrarød lysstråle mellom sender og mottaker.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang", sok=["fotoavbryter", "photo interrupter", "teller"]),
    "KY-011": dict(tittel="tofarget LED 5 mm", kategori="Lys", underkategori="Tofarget LED", modultype="Aktuator",
                   funksjon="LED med to farger (rød/grønn) i samme hus, styrt digitalt.", spenning="Se dokumentasjon",
                   grensesnitt="2× digital/PWM (rød/grønn)", sok=["led", "tofarget", "rød grønn"]),
    "KY-012": dict(tittel="aktiv summer", kategori="Lyd", underkategori="Aktiv summer", modultype="Aktuator",
                   funksjon="Piezosummer med innebygd oscillator som lager lyd direkte fra en digital på/av-puls.", spenning="3,3–5,5 V",
                   grensesnitt="Digital på/av", sok=["summer", "aktiv buzzer", "lyd"]),
    "KY-013": dict(tittel="analog temperatursensor", kategori="Temperatur", underkategori="Analog NTC", modultype="Sensor",
                   funksjon="Måler temperatur analogt med en NTC-termistor.", spenning="3,3–5 V",
                   grensesnitt="Analog utgang", sok=["temperatur", "ntc", "analog"]),
    "KY-015": dict(tittel="temperatur- og fuktsensor (DHT11)", kategori="Temperatur", underkategori="Temperatur og fuktighet", modultype="Sensor",
                   funksjon="Måler både temperatur og luftfuktighet digitalt med DHT11.", spenning="3,3–5,5 V",
                   grensesnitt="Digital 1-Wire (enkeltpinne-protokoll)", sok=["temperatur", "fuktighet", "dht11", "humidity"]),
    "KY-016": dict(tittel="RGB LED 5 mm", kategori="Lys", underkategori="RGB LED", modultype="Aktuator",
                   funksjon="RGB-LED i 5 mm hus for enkel fargestyring med tre kanaler.", spenning="3,3–5 V",
                   grensesnitt="3× PWM-kanaler (R/G/B)", sok=["led", "rgb", "farge"]),
    "KY-017": dict(tittel="kvikksølv-vippebryter", kategori="Bevegelse", underkategori="Vippebryter", modultype="Sensor",
                   funksjon="Registrerer vipping/helning med en forseglet kvikksølvbryter.", spenning="3,3–5,5 V",
                   grensesnitt="Digital utgang", sok=["vipping", "tilt", "kvikksølv"]),
    "KY-018": dict(tittel="fotomotstand (LDR)", kategori="Miljø", underkategori="Lysnivå", modultype="Sensor",
                   funksjon="Måler omgivelseslys analogt med en fotomotstand (LDR).", spenning="3,3–5 V",
                   grensesnitt="Analog utgang", sok=["lys", "fotomotstand", "ldr", "lysstyrke"]),
    "KY-019": dict(tittel="5V relémodul", kategori="Utgang", underkategori="Relé", modultype="Aktuator",
                   funksjon="Kobler en strømkrets av/på med et relé, styrt fra et digitalt signal.", spenning="5 V (styresignal ned til 3,3 V)",
                   grensesnitt="Digital inngang (styrer relé)", sok=["relé", "relay", "bryter høyeffekt"]),
    "KY-020": dict(tittel="vippebryter (metallkule)", kategori="Bevegelse", underkategori="Vippebryter", modultype="Sensor",
                   funksjon="Registrerer vipping med en metallkule som lukker kretsen ved helning.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang", sok=["vipping", "tilt switch"]),
    "KY-021": dict(tittel="mini reed-bryter", kategori="Magnetisk", underkategori="Reed-bryter", modultype="Sensor",
                   funksjon="Liten reed-bryter som slår av/på digitalt når en magnet er i nærheten.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang", sok=["reed", "magnet", "reed switch"]),
    "KY-022": dict(tittel="IR-mottaker", kategori="Kommunikasjon", underkategori="Infrarødt", modultype="Sensor",
                   funksjon="Mottar infrarøde signaler, f.eks. fra en fjernkontroll.", spenning="2,7–5,5 V",
                   grensesnitt="Digital utgang (IR-mottak)", sok=["infrarød", "ir mottaker", "fjernkontroll"]),
    "KY-023": dict(tittel="joystick (dobbel akse)", kategori="Input", underkategori="Joystick", modultype="Sensor",
                   funksjon="Analog joystick med X/Y-akser og en trykknapp (Z).", spenning="3,3–5 V",
                   grensesnitt="2× analog (X/Y) + digital (knapp)", sok=["joystick", "styrespak"]),
    "KY-024": dict(tittel="lineær hallsensor", kategori="Magnetisk", underkategori="Analog/digital", modultype="Sensor",
                   funksjon="Måler styrken på et magnetfelt analogt, med digital terskelutgang i tillegg.", spenning="2,7–6,5 V",
                   grensesnitt="Analog + digital utgang", sok=["hall", "magnetfelt", "analog"]),
    "KY-025": dict(tittel="reed-bryter (analog/digital)", kategori="Magnetisk", underkategori="Reed-bryter", modultype="Sensor",
                   funksjon="Reed-bryter med både analog og digital utgang og justerbar følsomhet.", spenning="3,3–5 V",
                   grensesnitt="Analog + digital utgang", sok=["reed", "magnet", "analog digital"]),
    "KY-026": dict(tittel="flammesensor", kategori="Miljø", underkategori="Flamme", modultype="Sensor",
                   funksjon="Registrerer infrarødt lys fra flammer for enkel branndeteksjon.", spenning="3,3–5,5 V",
                   grensesnitt="Analog + digital utgang", sok=["flamme", "brann", "ir sensor", "flame"]),
    "KY-027": dict(tittel="magisk lyskopp", kategori="Lys", underkategori="Vippestyrt lys", modultype="Aktuator/sensor",
                   funksjon="To koblede kort med kvikksølvbryter og LED, brukes parvis til lystriks/prosjekter.", spenning="3,3–5,5 V",
                   grensesnitt="Digital utgang + LED-styring", sok=["magic light cup", "lys", "vippe"]),
    "KY-028": dict(tittel="digital temperatursensor (terskel)", kategori="Temperatur", underkategori="Digital terskel", modultype="Sensor",
                   funksjon="Måler temperatur med justerbar digital terskel og analog utgang.", spenning="3,3–5,5 V",
                   grensesnitt="Analog + digital utgang", sok=["temperatur", "ntc", "digital"]),
    "KY-029": dict(tittel="tofarget LED 3 mm", kategori="Lys", underkategori="Tofarget LED", modultype="Aktuator",
                   funksjon="Liten tofarget LED (rød/grønn) i 3 mm hus.", spenning="Se dokumentasjon",
                   grensesnitt="2× digital/PWM (rød/grønn)", sok=["led", "tofarget", "rød grønn"]),
    "KY-031": dict(tittel="bankesensor", kategori="Bevegelse", underkategori="Vibrasjon", modultype="Sensor",
                   funksjon="Registrerer banking eller støt med en fjærbasert bryter.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang", sok=["bank", "støt", "knock sensor"]),
    "KY-032": dict(tittel="IR-hinderdeteksjon", kategori="Bevegelse", underkategori="Avstand/hinder", modultype="Sensor",
                   funksjon="Reflektiv IR-sensor som registrerer hindringer på kort avstand, med justerbar rekkevidde.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang (justerbar rekkevidde)", sok=["hinder", "avstand", "obstacle", "ir"]),
    "KY-033": dict(tittel="linjefølgersensor", kategori="Bevegelse", underkategori="Linjefølging", modultype="Sensor",
                   funksjon="Reflektiv IR-sensor til linjefølgende roboter, skiller mørke/lyse overflater.", spenning="3,3–5 V",
                   grensesnitt="Digital utgang (justerbar terskel)", sok=["linjefølger", "line tracking", "ir"]),
    "KY-034": dict(tittel="7-fargers blinkende LED", kategori="Lys", underkategori="Selvblinkende LED", modultype="Aktuator",
                   funksjon="LED som automatisk bytter mellom 7 farger uten ekstra styring.", spenning="3–5 V",
                   grensesnitt="Digital på/av (fast fargesekvens)", sok=["led", "farger", "blinkende"]),
    "KY-035": dict(tittel="analog hallsensor", kategori="Magnetisk", underkategori="Analog", modultype="Sensor",
                   funksjon="Måler styrken på et magnetfelt med en ren analog utgang.", spenning="2,7–6 V",
                   grensesnitt="Analog utgang", sok=["hall", "magnetfelt", "analog"]),
    "KY-036": dict(tittel="metallberøringssensor", kategori="Input", underkategori="Berøring", modultype="Sensor",
                   funksjon="Registrerer berøring på en metallflate eller -tråd, med justerbar følsomhet.", spenning="3,3–5,5 V",
                   grensesnitt="Analog + digital utgang", sok=["berøring", "touch", "metall"]),
    "KY-037": dict(tittel="lydsensor", kategori="Lyd", underkategori="Lydnivå", modultype="Sensor",
                   funksjon="Registrerer lydnivå med mikrofon, både som analog og digital utgang.", spenning="3,3–5,5 V",
                   grensesnitt="Analog + digital utgang", sok=["lyd", "mikrofon", "sound sensor"]),
}

KOMPATIBILITET = ["Arduino 5 V", "ESP32 3,3 V (sjekk nivå på signalet)"]

DRAFT_NOTICE = (
    "*Dette er en foreløpig profil generert fra ekstern referansedata "
    "(arduinomodules.info). Antall er satt til 0 fordi vi ikke eier denne "
    "modulen ennå — oppdater `antall` og `hylle` i frontmatter når den er anskaffet.*"
)


def slugify(text: str) -> str:
    text = text.lower()
    text = text.replace("æ", "ae").replace("ø", "o").replace("å", "a")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-+", "-", text)


def extra_identifiers(specifications: dict) -> list[str]:
    for key, value in specifications.items():
        if re.search(r"known as|sold as|alternate part number|alias", key, re.IGNORECASE):
            return [part.strip() for part in re.split(r"[,/]", value) if part.strip()]
    return []


def clean_english_alias(name: str, module_id: str) -> str:
    name = name.split("—")[0].split("–")[0]
    name = name.replace(module_id, "")
    name = re.sub(r"^Arduino\s+", "", name.strip())
    name = re.sub(r"\s+", " ", name).strip()
    return name.lower()


def yaml_quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def yaml_list(values: list[str], indent: str = "  ") -> str:
    if not values:
        return " []"
    return "\n" + "\n".join(f"{indent}- {yaml_quote(v)}" for v in values)


def build_frontmatter(entry: dict, meta: dict, slug: str, primary_image: str) -> str:
    module_id = entry["module_id"]
    title = f"{module_id} {meta['tittel']}"
    identifikatorer = [module_id, *extra_identifiers(entry["specifications"])]
    aliaser = [clean_english_alias(entry["name"], module_id)]
    lines = [
        "---",
        f"title: {yaml_quote(title)}",
        'type: "moduler"',
        f"bilde: {yaml_quote(primary_image)}",
        f"identifikatorer:{yaml_list(identifikatorer)}",
        f"aliaser:{yaml_list(aliaser)}",
        f"kategori: {yaml_quote(meta['kategori'])}",
        f"underkategori: {yaml_quote(meta['underkategori'])}",
        f"modultype: {yaml_quote(meta['modultype'])}",
        f"funksjon: {yaml_quote(meta['funksjon'])}",
        f"spenning: {yaml_quote(meta['spenning'])}",
        f"grensesnitt: {yaml_quote(meta['grensesnitt'])}",
        f"kompatibilitet:{yaml_list(KOMPATIBILITET)}",
        'hylle: ""',
        "antall: 0",
        f"sok:{yaml_list(meta['sok'])}",
        "lenker:",
        '  - navn: "Arduino Modules"',
        f"    url: {yaml_quote(entry['url'])}",
        "---",
        "",
        meta["funksjon"],
        "",
        DRAFT_NOTICE,
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    modules = json.loads((DATA_DIR / "modules.json").read_text(encoding="utf-8"))
    generated = []
    for entry in modules:
        module_id = entry["module_id"]
        if module_id in SKIP_MODULE_IDS:
            continue
        meta = MODULE_META.get(module_id)
        if meta is None:
            print(f"Hopper over {module_id}: mangler norsk metadata i MODULE_META")
            continue

        slug = f"{module_id.lower()}-{slugify(meta['tittel'])}"
        target_dir = OUTPUT_DIR / slug
        target_dir.mkdir(parents=True, exist_ok=True)

        for image in entry["all_images"]:
            source = DATA_DIR / "images" / image["filename"]
            if source.exists():
                shutil.copyfile(source, target_dir / image["filename"])
            else:
                print(f"Advarsel: mangler bildefil {source}")

        (target_dir / "index.md").write_text(
            build_frontmatter(entry, meta, slug, entry["primary_image"]), encoding="utf-8"
        )
        generated.append(slug)

    print(f"Genererte {len(generated)} modulprofiler i {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
