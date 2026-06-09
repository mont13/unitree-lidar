# Scans — continuous movement

Sem se ukládají pohybové sekvence jako složky krátkých PCD framů:

```text
seq_YYYYMMDD_HHMMSS/
  000000.pcd
  000001.pcd
  ...
  index.csv
  meta.txt
```

Aktuální poslední sekvence má symlink:

```text
latest_sequence
```

Tyto soubory jsou vstup pro:

```bash
../build_map.sh
```
