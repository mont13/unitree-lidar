# Scans — statické a merge výstupy

Sem ukládají pomocné direct/fallback nástroje své lokální výstupy:

```text
latest_usb_scan*.pcd
latest_room_merged*.pcd
latest_room_merged*.transform.txt
room_merged_*.png
...
```

Soubory v této složce jsou **generované lokálně** a přes `.gitignore` se necommitují.
Slouží hlavně jako pracovní prostor pro:

- `scan_serial_direct.py`
- `merge_scans_simple.py`
- `merge_three_known_poses.py`
