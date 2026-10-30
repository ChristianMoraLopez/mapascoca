# Coca en Colombia por zonas

Mapa interactivo de las hectáreas de coca detectadas por el censo SIMCI (UNODC y Gobierno de Colombia), por municipio, de 2001 a 2024, agrupadas en cuatro zonas:

- **Norte:** Norte de Santander, Antioquia, Córdoba, Bolívar y norte del Chocó.
- **Sur:** Putumayo y Caquetá.
- **Pacífico:** Nariño.
- **Resto del país:** los demás departamentos, incluido el sur del Chocó.

La página es un solo archivo HTML: `dist/index.html` se abre directamente en el navegador.

## Reconstruir

```bash
npm install
python3 scripts/build.py
node scripts/shots.cjs   # capturas en screenshots/
```

`scripts/build.py` lee `data/raw/`, escribe `data/zonas.csv`, `data/processed/` y `dist/`, y valida las sumas contra el informe de UNODC. Detalles de fuentes, validación y corte del Chocó en [`data/README.md`](data/README.md).

## Estructura

- `data/raw/`: archivos originales sin modificar.
- `data/processed/`: series limpias, validación y geometría simplificada.
- `web/template.html`: la página; `build.py` le inyecta los datos.
- `dist/mapa-coca-colombia.html`: fragmento publicado como artefacto; `dist/index.html`: documento completo.
