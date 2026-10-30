#!/usr/bin/env python3
"""Construye los datos del mapa de coca a partir de los archivos crudos.

Entradas (data/raw/, sin modificar):
  - minjusticia_deteccion_coca_municipal_2001_2024.csv  (datos.gov.co, acs4-3wgp)
  - mgn2018_municipios.geo.json                         (DANE MGN 2018 vía @john-guerra/geo-colombia)

Salidas:
  - data/zonas.csv                                      código DIVIPOLA -> zona, para los 1.122 municipios
  - data/processed/coca_municipal_2001_2024.csv         serie limpia por municipio
  - data/processed/coca_departamental_2001_2024.csv
  - data/processed/coca_zonas_2001_2024.csv
  - data/processed/validacion.csv                       contraste con las cifras publicadas por UNODC
  - data/processed/municipios.topo.json                 geometría simplificada
  - dist/mapa-coca-colombia.html                        página autocontenida (web/template.html + datos)

Uso: python3 scripts/build.py   (requiere `npm install` para mapshaper)
"""

import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
YEARS = list(range(2001, 2025))

COCA_CSV = RAW / "minjusticia_deteccion_coca_municipal_2001_2024.csv"
GEO_JSON = RAW / "mgn2018_municipios.geo.json"

# --- Zonas -----------------------------------------------------------------

ZONES = ["norte", "sur", "pacifico", "resto"]
ZONE_NAMES = {"norte": "Norte", "sur": "Sur", "pacifico": "Pacífico", "resto": "Resto del país"}

ZONE_BY_DEPT = {
    "54": "norte",  # Norte de Santander
    "05": "norte",  # Antioquia
    "23": "norte",  # Córdoba
    "13": "norte",  # Bolívar
    "86": "sur",    # Putumayo
    "18": "sur",    # Caquetá
    "52": "pacifico",  # Nariño
}

# Chocó se divide por subregiones (DANE / Plan de Desarrollo del Chocó):
# norte = Darién, Atrato y Pacífico Norte; sur = San Juan y Pacífico Sur (Baudó y Litoral del San Juan).
CHOCO_NORTE = {
    # Darién
    "27006": "Darién", "27800": "Darién", "27615": "Darién", "27150": "Darién",
    # Atrato
    "27001": "Atrato", "27050": "Atrato", "27073": "Atrato", "27099": "Atrato", "27245": "Atrato",
    "27413": "Atrato", "27425": "Atrato", "27600": "Atrato",
    # Pacífico Norte
    "27075": "Pacífico Norte", "27372": "Pacífico Norte", "27495": "Pacífico Norte",
}
CHOCO_SUR = {
    # Pacífico Sur (Baudó y litoral)
    "27025": "Pacífico Sur", "27077": "Pacífico Sur", "27430": "Pacífico Sur", "27250": "Pacífico Sur",
    # San Juan
    "27361": "San Juan", "27205": "San Juan", "27135": "San Juan", "27160": "San Juan", "27450": "San Juan",
    "27491": "San Juan", "27580": "San Juan", "27660": "San Juan", "27745": "San Juan", "27787": "San Juan",
    "27810": "San Juan",
}

DEPT_NAMES = {
    "05": "Antioquia", "08": "Atlántico", "11": "Bogotá, D.C.", "13": "Bolívar", "15": "Boyacá",
    "17": "Caldas", "18": "Caquetá", "19": "Cauca", "20": "Cesar", "23": "Córdoba",
    "25": "Cundinamarca", "27": "Chocó", "41": "Huila", "44": "La Guajira", "47": "Magdalena",
    "50": "Meta", "52": "Nariño", "54": "Norte de Santander", "63": "Quindío", "66": "Risaralda",
    "68": "Santander", "70": "Sucre", "73": "Tolima", "76": "Valle del Cauca", "81": "Arauca",
    "85": "Casanare", "86": "Putumayo", "88": "San Andrés, Providencia y Santa Catalina",
    "91": "Amazonas", "94": "Guainía", "95": "Guaviare", "97": "Vaupés", "99": "Vichada",
}

# --- Cifras publicadas por UNODC para validar -------------------------------

REPORT = "UNODC-SIMCI, Monitoreo de territorios con presencia de cultivos de coca 2024 (junio 2026)"
NATIONAL_PUBLISHED = {  # Figura 4, p. 33 del PDF (etiquetas exactas, hectáreas)
    2010: 61811, 2011: 63765, 2012: 47788, 2013: 48189, 2014: 69132, 2015: 96085, 2016: 146140,
    2017: 171495, 2018: 169018, 2019: 154476, 2020: 142784, 2021: 204257, 2022: 230028,
    2023: 252572, 2024: 261386,
}
NATIONAL_PUBLISHED_OTHER = {  # comunicado UNODC, 14 de marzo de 2003
    2001: (144807, "UNODC, comunicado de prensa de marzo de 2003"),
    2002: (102000, "UNODC, comunicado de prensa de marzo de 2003 (cifra redondeada)"),
}
UNODC_REGIONS = {  # Resumen de resultados, p. 11 del PDF
    "Pacífico": (["52", "19", "76", "27"], 107078, 121612),
    "Putumayo – Caquetá": (["86", "18"], 56933, 49190),
    "Catatumbo": (["54", "20"], 43867, 48739),
    "Central": (["05", "23", "13", "68", "15", "17"], 37063, 34348),
    "Meta – Guaviare": (["50", "95"], 7164, 7138),
    "Orinoquía": (["99", "81"], 343, 253),
    "Amazonía": (["91", "94", "97"], 122, 103),
    "Sierra Nevada": (["47", "44"], 2, 3),
}


def zone_for(code: str) -> str:
    if code in CHOCO_NORTE:
        return "norte"
    if code in CHOCO_SUR:
        return "resto"
    return ZONE_BY_DEPT.get(code[:2], "resto")


def subregion_for(code: str) -> str:
    return CHOCO_NORTE.get(code) or CHOCO_SUR.get(code) or ""


def num(value: str) -> float:
    value = value.strip()
    return float(value) if value else 0.0


def read_coca():
    with COCA_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    coca = {}
    for r in rows:
        code = r["CODMPIO"].strip().zfill(5)
        if code in coca:
            sys.exit(f"Código duplicado en el CSV: {code}")
        coca[code] = {
            "name_raw": r["MUNICIPIO"].strip(),
            "series": [round(num(r[str(y)]), 2) for y in YEARS],
        }
    return coca


def read_geo():
    geo = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    munis = {}
    for f in geo["features"]:
        p = f["properties"]
        munis[p["MPIO_CDPMP"]] = {"name": p["MPIO_CNMBR"], "dept": p["DPTO_CCDGO"], "area_km2": p["AREA"] / 1e6}
    return munis


def title_case(name: str) -> str:
    small = {"de", "del", "la", "las", "los", "el", "y", "en"}
    words = name.lower().split()
    out = [w if (i and w in small) else w[:1].upper() + w[1:] for i, w in enumerate(words)]
    return " ".join(out).replace("D.c.", "D.C.")


def write_csv(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    coca = read_coca()
    munis = read_geo()

    missing = sorted(set(coca) - set(munis))
    if missing:
        sys.exit(f"Municipios con coca sin geometría: {missing}")

    choco = {c for c, m in munis.items() if m["dept"] == "27"}
    if choco != set(CHOCO_NORTE) | set(CHOCO_SUR):
        sys.exit(f"El corte del Chocó no cubre exactamente sus municipios: {sorted(choco ^ (set(CHOCO_NORTE) | set(CHOCO_SUR)))}")

    # zonas.csv para todos los municipios del MGN
    zone_rows = []
    for code in sorted(munis):
        m = munis[code]
        zone_rows.append([code, title_case(m["name"]), DEPT_NAMES[m["dept"]], zone_for(code), subregion_for(code)])
    write_csv(ROOT / "data" / "zonas.csv", ["codmpio", "municipio", "departamento", "zona", "subregion_choco"], zone_rows)

    # Serie municipal limpia
    muni_rows = []
    for code in sorted(coca):
        m = munis[code]
        muni_rows.append([code, m["dept"], DEPT_NAMES[m["dept"]], title_case(m["name"]), zone_for(code)] + coca[code]["series"])
    write_csv(OUT / "coca_municipal_2001_2024.csv",
              ["codmpio", "coddepto", "departamento", "municipio", "zona"] + [str(y) for y in YEARS], muni_rows)

    # Agregados
    dept_tot = defaultdict(lambda: [0.0] * len(YEARS))
    zone_tot = defaultdict(lambda: [0.0] * len(YEARS))
    national = [0.0] * len(YEARS)
    for code, c in coca.items():
        d = munis[code]["dept"]
        z = zone_for(code)
        for i, v in enumerate(c["series"]):
            dept_tot[d][i] += v
            zone_tot[z][i] += v
            national[i] += v
    write_csv(OUT / "coca_departamental_2001_2024.csv", ["coddepto", "departamento"] + [str(y) for y in YEARS],
              [[d, DEPT_NAMES[d]] + [round(v, 2) for v in s] for d, s in sorted(dept_tot.items())])
    write_csv(OUT / "coca_zonas_2001_2024.csv", ["zona", "nombre"] + [str(y) for y in YEARS],
              [[z, ZONE_NAMES[z]] + [round(v, 2) for v in zone_tot[z]] for z in ZONES]
              + [["total", "Total nacional"] + [round(v, 2) for v in national]])

    # Validación
    val = []
    for y, ref in NATIONAL_PUBLISHED.items():
        got = national[YEARS.index(y)]
        val.append(["nacional", str(y), round(got, 2), ref, round(got - ref, 2), REPORT + ", Figura 4"])
    for y, (ref, src) in NATIONAL_PUBLISHED_OTHER.items():
        got = national[YEARS.index(y)]
        val.append(["nacional", str(y), round(got, 2), ref, round(got - ref, 2), src])
    for reg, (depts, r23, r24) in UNODC_REGIONS.items():
        for y, ref in ((2023, r23), (2024, r24)):
            got = sum(dept_tot[d][YEARS.index(y)] for d in depts)
            val.append([f"región {reg}", str(y), round(got, 2), ref, round(got - ref, 2), REPORT + ", resumen de resultados"])
    write_csv(OUT / "validacion.csv", ["nivel", "año", "suma_datos_ha", "cifra_publicada_ha", "diferencia_ha", "fuente"], val)
    print("Validación (diferencias mayores a 1 ha):")
    for row in val:
        if abs(row[4]) > 1:
            print("  ", row)

    # Geometría: simplificada, con código, nombre y departamento
    topo = OUT / "municipios.topo.json"
    subprocess.run([
        "npx", "--no-install", "mapshaper", str(GEO_JSON),
        "-each", "c=MPIO_CDPMP, d=DPTO_CCDGO",
        "-filter-fields", "c,d",
        "-simplify", "weighted", "12%", "keep-shapes",
        "-clean",
        "-rename-layers", "municipios",
        "-o", str(topo), "format=topojson", "quantization=1e5", "force",
    ], check=True, cwd=ROOT)
    print(f"TopoJSON: {topo.stat().st_size / 1024:.0f} KB")

    # Datos para la página
    payload = {
        "years": YEARS,
        "zones": [{"id": z, "name": ZONE_NAMES[z]} for z in ZONES],
        "depts": DEPT_NAMES,
        "munis": {
            code: {
                "n": title_case(m["name"]),
                "d": m["dept"],
                "z": zone_for(code),
                "a": round(m["area_km2"], 2),
                **({"s": coca[code]["series"]} if code in coca else {}),
            }
            for code, m in munis.items()
        },
        "chocoSplit": {
            "norte": sorted((title_case(munis[c]["name"]), s) for c, s in CHOCO_NORTE.items()),
            "sur": sorted((title_case(munis[c]["name"]), s) for c, s in CHOCO_SUR.items()),
        },
        "validation": {"maxAbsDiff2010_2024": max(abs(r[4]) for r in val if r[0] == "nacional" and int(r[1]) >= 2010)},
    }
    template = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    html = (template
            .replace("/*__DATA__*/null", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            .replace("/*__TOPO__*/null", topo.read_text(encoding="utf-8")))
    dist = ROOT / "dist" / "mapa-coca-colombia.html"
    dist.parent.mkdir(exist_ok=True)
    dist.write_text(html, encoding="utf-8")
    print(f"Página: {dist.relative_to(ROOT)} ({dist.stat().st_size / 1024:.0f} KB)")

    # Versión con documento completo para abrir localmente o servir como sitio estático
    standalone = ROOT / "dist" / "index.html"
    standalone.write_text(
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'
        + html + "</body></html>", encoding="utf-8")


if __name__ == "__main__":
    main()
