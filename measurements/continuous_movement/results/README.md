# Results — continuous movement maps

Sem se ukládají složené mapy z pohybových sekvencí.

Očekávané soubory po `../build_map.sh`:

```text
continuous_map_YYYYMMDD_HHMMSS.pcd
continuous_map_YYYYMMDD_HHMMSS.png
latest_map.pcd
latest_map.png
```

`latest_map.png` je nejrychlejší kontrola výsledku. `latest_map.pcd` se otevírá přes:

```bash
../../view.sh results/latest_map.pcd
```
