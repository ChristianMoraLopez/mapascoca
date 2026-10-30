# Datos

## Fuentes (en `raw/`, sin modificar)

| Archivo | Fuente |
|---|---|
| `minjusticia_deteccion_coca_municipal_2001_2024.csv` | «Detección de cultivos de coca (hectáreas)», Ministerio de Justicia y del Derecho – Observatorio de Drogas de Colombia, con base en el censo SIMCI (UNODC y Gobierno de Colombia). [datos.gov.co, conjunto `acs4-3wgp`](https://www.datos.gov.co/d/acs4-3wgp), descargado el 30 de octubre de 2026 (última actualización del conjunto: 8 de julio de 2026). |
| `minjusticia_deteccion_coca_metadata.json` | Metadatos del mismo conjunto (API de datos.gov.co). |
| `UNODC_Monitoreo_Cultivos_Coca_2024.pdf` | UNODC-SIMCI, *Monitoreo de territorios con presencia de cultivos de coca 2024*, Bogotá, junio de 2026. [Enlace](https://www.unodc.org/rocol/uploads/documents/2026/InformeCC2024/Monitoreo_de_Cultivos_de_Coca_2024.pdf). Se usa para validar. |
| `mgn2018_municipios.geo.json` | Marco Geoestadístico Nacional 2018 del DANE (1.122 municipios y áreas no municipalizadas), en la versión simplificada del paquete npm [`@john-guerra/geo-colombia`](https://www.npmjs.com/package/@john-guerra/geo-colombia) 0.1.0 (licencia MIT, `LICENSE-geo-colombia.txt`). |

El sitio odc.gov.co no respondía desde el entorno de trabajo; datos.gov.co publica el mismo conjunto del Observatorio.

## Procesados (en `processed/`, generados por `scripts/build.py`)

- `coca_municipal_2001_2024.csv`: hectáreas por municipio y año, código DIVIPOLA de 5 dígitos, zona asignada. Celda vacía en el original = 0 (sin coca detectada).
- `coca_departamental_2001_2024.csv` y `coca_zonas_2001_2024.csv`: sumas.
- `validacion.csv`: contraste con las cifras publicadas por UNODC.
- `municipios.topo.json`: geometría simplificada (mapshaper 0.7.71, Visvalingam ponderado al 12 %, 223 KB).

`../zonas.csv` asigna una zona a cada uno de los 1.122 municipios del MGN.

## Validación

- **Total nacional 2010–2024:** la suma municipal coincide con las etiquetas de la Figura 4 del informe 2024 (p. 33 del PDF) en todos los años; diferencia máxima 0,4 ha (redondeo de decimales).
- **Regiones UNODC 2023 y 2024** (resumen de resultados, p. 11 del PDF): las ocho regiones coinciden con diferencias de 1 ha o menos.
- **2001:** el archivo municipal suma 136.918,08 ha; UNODC publicó 144.807 ha (comunicado de prensa de marzo de 2003). Faltan 7.888,92 ha que el archivo no asigna a ningún municipio. Se muestra la suma municipal y la página lo advierte en ese año.
- **2002:** 102.071 ha, coherente con las «102.000 ha» redondeadas del mismo comunicado.
- **2003–2009:** no se encontró en esta revisión una tabla oficial de esos años para contrastar cifra por cifra.

## Corte del Chocó

Por subregiones del departamento.

- **Norte (zona Norte):** Darién (Acandí, Unguía, Riosucio, Carmen del Darién), Atrato (Quibdó, Atrato, Bagadó, Bojayá, El Carmen de Atrato, Lloró, Medio Atrato, Río Quito) y Pacífico Norte (Bahía Solano, Juradó, Nuquí).
- **Sur (zona Resto del país):** San Juan (Istmina, Condoto, El Cantón del San Pablo, Cértegui, Medio San Juan, Nóvita, Río Iró, San José del Palmar, Sipí, Tadó, Unión Panamericana) y Pacífico Sur (Alto Baudó, Medio Baudó, Bajo Baudó, El Litoral del San Juan).

Belén de Bajirá (creado después de 2018) no existe en el MGN 2018 ni en el archivo de coca; su territorio queda dentro de Riosucio y Carmen del Darién, ambos en el norte.
