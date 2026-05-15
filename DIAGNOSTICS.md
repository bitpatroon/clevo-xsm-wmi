# Clevo X370SNx Keyboard Backlight — Diagnose & Vervolgstappen

## Huidige situatie (mei 2026)

### Wat werkt
- Module laadt correct, DMI-match op "X370SNx" ✓
- WMI GUIDs aanwezig in `/sys/bus/wmi/devices/` ✓
- `ec_write()` retourneert rc=0 (EC accepteert de bytes) ✓
- `acpi_evaluate_object(ECMD)` retourneert AE_OK na bugfix ✓

### Wat niet werkt
- Toetsenbord licht niet op via welk pad dan ook:
  - WMI-pad (0x67/0x68): geblokkeerd door `ECOK=0`
  - Direct `ec_write()` naar mailbox (0xF8-0xFC): EC reageert niet
  - Direct `acpi_evaluate_object(ECMD)`: aanroep slaagt maar LED blijft uit

### Kernvraag
**Is PSF0 bit 0 gezet op dit systeem?**

`ECOK` in de DSDT wordt alleen op 1 gezet als `PSF0 & 1 == 1`.  
`PSF0` staat op fysiek geheugenadres `0x33857018` (32-bit veld, OGNS OperationRegion).  
Als PSF0 bit 0 = 0, is de ACPI-LED-route structureel uitgeschakeld door de BIOS.

---

## Stap 1 — Windows: PSF0 lezen (meest kritisch)

PSF0 staat op fysiek adres `0x33857018`. Lees dit met **RWEverything**:

1. Download **RWEverything** (gratis): https://rweverything.com/
2. Open als Administrator
3. Ga naar: **Memory** tab → **Physical Memory**
4. Voer adres in: `33857018`
5. Lees de 4 bytes (little-endian 32-bit waarde)

**Interpretatie:**
- Bit 0 = 1 (waarde is oneven, bijv. `0x00000001`, `0x00000003`, ...):  
  ECOK kan worden gezet → ACPI-pad werkt in Windows → timing/init-probleem op Linux
- Bit 0 = 0 (waarde is even, bijv. `0x00000000`, `0x00000002`, ...):  
  ACPI-pad is uitgeschakeld → Windows gebruikt een ander mechanisme → andere aanpak nodig

**Noteer de volledige 32-bit waarde (PSF0).**

---

## Stap 2 — Windows: EC-registers scannen tijdens kleurwisseling

Gebruik **RWEverything** om EC-registers te lezen terwijl het toetsenbord van kleur wisselt:

1. Ga naar: **Embedded Controller** tab (of EC tab)
2. Maak een snapshot van alle 256 registers (0x00–0xFF) terwijl toetsenbord **blauw** is
3. Verander kleur in Control Center naar **rood**
4. Maak opnieuw een snapshot
5. Vergelijk: welke registers zijn veranderd?

**Let extra op:**
- Registers rond 0xF8–0xFD (onze FCMD/FDAT mailbox)
- Registers die R/G/B-waarden bevatten (255/0/0 voor rood = 0xFF/0x00/0x00)
- Registers die veranderen NA de kleurwissel maar niet daarvoor

---

## Stap 3 — Windows: WMI-trace (optioneel, meer detail)

Als RWEverything niet genoeg geeft, gebruik Windows ETW om WMI-calls te traceren:

```powershell
# In PowerShell als Administrator:
wevtutil sl Microsoft-Windows-WMI-Activity/Operational /e:true
# Verander kleur in Control Center
# Exporteer log:
wevtutil epl Microsoft-Windows-WMI-Activity/Operational C:\wmi_trace.evtx
```

Of gebruik **WMI Explorer** om te zien welke WMI-methodes worden aangeroepen.

---

## Vervolgstappen op Linux (afhankelijk van Windows-resultaat)

### Als PSF0 bit 0 = 1 (ACPI-pad zou moeten werken)

Het probleem is waarschijnlijk timing: `_REG` is al uitgevoerd voordat de module laadt,
en ECOK is op dat moment misschien al gezet. Check:

```bash
# Lees ECOK huidig via ACPI debugfs
sudo cat /sys/kernel/debug/acpi/EC0/ECOK 2>/dev/null || \
sudo cat /sys/kernel/debug/acpi/EC/ECOK 2>/dev/null
```

Als ECOK = 1: de WMI-aanroepen (`kb_full_color_ops`) zouden moeten werken.
Test dan met:
```bash
# Terug naar kb_full_color_ops in DMI-tabel, dan:
echo "red" | sudo tee /sys/devices/platform/clevo_xsm_wmi/kb_color
```

Als ECOK = 0 maar PSF0 bit 0 = 1: `_REG` opnieuw aanroepen via kernel module:
```c
// In kb_x370__init: force _REG(3,1) via acpi_evaluate_object
// zodat ECOK alsnog op 1 gezet wordt
```

### Als PSF0 bit 0 = 0 (ACPI-pad structureel uitgeschakeld)

Windows gebruikt een ander mechanisme. Mogelijkheden:

**A) Directe EC-registers (niet de mailbox)**  
De EC-registers die RWEverything laat zien zijn de sleutel.  
Implement in Linux met `ec_write()` naar die specifieke adressen.

**B) Ander WMI-interface**  
Misschien gebruikt Windows MethodId 0x65/0x66 i.p.v. 0x67/0x68.  
Of er is een aparte WMI-GUID voor de X370SNx.

**C) I2C/SPI keyboard controller**  
Sommige gaming-laptops hebben een aparte RGB-controller (bijv. ITE IT8297)  
die via I2C wordt aangestuurd. Check:
```bash
sudo i2cdetect -l
sudo i2cdetect -y 0  # (en 1, 2, ...)
```

---

## Huidige module-staat

De module staat nu op **ACPI ECMD-aanroep** (`x370_acpi_ecmd`):
- Roept `\_SB.PC00.LPCB.EC.ECMD` rechtstreeks aan
- Omzeilt ECOK-check in SCMD
- AE_OK wordt gerapporteerd maar LED reageert niet

```bash
# Laden en testen:
cd module && bash b.sh
echo "red" | sudo tee /sys/devices/platform/clevo_xsm_wmi/kb_color
sudo dmesg | grep X370 | tail -20
```

Verwachte dmesg als ECMD werkt: `st=0x0` voor alle aanroepen + LED licht op.

---

## Samenvatting prioriteiten

| Prioriteit | Actie | Wat het oplevert |
|---|---|---|
| **1** | Lees PSF0 @ 0x33857018 in Windows (RWEverything) | Root cause: ACPI-pad aan/uit? |
| **2** | EC-register snapshot voor/na kleurwisseling in Windows | Exacte registers die LED aansturen |
| **3** | Test huidige module (ECMD-aanroep) na laatste fix | Werkt ECMD-pad? |
| **4** | i2cdetect op Linux | Aparte RGB-controller? |
