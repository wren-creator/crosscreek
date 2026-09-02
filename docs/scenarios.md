# Cross Creek scenarios, instructor edition

Ten planted weaknesses in four groups. Trainees work from
`scenarios-trainee.md`, which is this file with the **Fix** line removed from
each entry. Every command below was run from the `attacker` container against
the running flat range.

Every entry uses this shape:

```
### N. <short title>
**Where:** <segment / host / port / protocol>
**Real-world parallel:** <incident, year>
**Vulnerability:** <mechanism>
**MITRE ATT&CK for ICS:** <technique IDs>
**Confirm / exploit with:** <tool + exact command>
**Physical consequence in the sim:** <what the process does>
**Fix:** <remediation + CISA CPG / ISA-62443 reference>
```

Get a shell on the attacker box first:

```bash
docker exec -it crosscreek-attacker bash
ls /opt/scripts
```

---

## Group A, exposure and access

### 1. Internet-exposed HMI with default credentials
**Where:** `hmi-water` 172.30.40.10:8080 (published `127.0.0.1:8071`), reachable from `edge-net` through the flat firewall
**Real-world parallel:** Municipal Water Authority of Aliquippa, PA, November 2023. Iran-linked CyberAv3ngers reached internet-exposed Unitronics Vision PLCs on TCP 20256 with the factory password `1111`.
**Vulnerability:** the operator HMI is routable from the hostile network and still carries the commissioning account `admin` / `admin`. The login page even says the factory default is active.
**MITRE ATT&CK for ICS:** T0883 Internet Accessible Device, T0812 Default Credentials, T0822 External Remote Services
**Confirm / exploit with:**
```bash
python3 /opt/scripts/recon.py sweep      # finds 172.30.40.10:8080 from the edge
python3 /opt/scripts/recon.py creds      # admin/admin -> ACCEPTED on both HMIs
```
Then browse `http://127.0.0.1:8071/`, log in `admin` / `admin`, and drive the plant from the Controls panel.
**Physical consequence in the sim:** full operator control from the internet: stop pumps, move the dose setpoint, open breakers.
**Fix:** the HMI has no business being routable from anywhere but the operator LAN. Put it behind the segmented firewall so `edge-net` cannot reach it (`./start.sh --segmented`), require a real per-operator account (`DEFAULT_CREDS=0`), and reach it remotely only through the DMZ jump host. CISA CPG 2.A (changing default passwords), 2.F (no exploitable internet-exposed services); ISA/IEC 62443 zone boundary between the enterprise/internet zone and the operations zone.

### 2. Unauthenticated remote access to the OT LAN
**Where:** `eng-ws` 172.30.20.20:5900
**Real-world parallel:** Oldsmar, FL, February 2021. An operator watched the mouse move on its own; the intruder came in over a remote-desktop tool that was reachable and unauthenticated, and raised the sodium hydroxide setpoint roughly a hundredfold.
**Vulnerability:** the engineering workstation answers a remote-desktop port with no authentication ("works from the office wifi", per `notes.txt`). Anyone who reaches the box owns the console that manages the PLCs.
**MITRE ATT&CK for ICS:** T0822 External Remote Services, T0886 Remote Services
**Confirm / exploit with:**
```bash
nc -v 172.30.20.20 5900        # banner: "no authentication configured"
```
**Physical consequence in the sim:** none directly; this is the foothold that makes scenario 3 possible.
**Fix:** no inbound remote access to an OT-adjacent host. Terminate remote sessions on a hardened DMZ jump host with MFA, and let it reach only what the engineer needs (`EXPOSE_REMOTE_ACCESS=0`; the segmented topology adds the `jumphost`). CISA CPG 2.H (phishing-resistant MFA), 2.W (no OT assets on the public internet).

### 3. Engineering workstation as a pivot
**Where:** `eng-ws` 172.30.20.20:8080, sharing `/opt/projects`
**Vulnerability:** the workstation serves its project directory over plain HTTP, including `notes.txt`, which lists every controller address, the OpenPLC web login, and the "no station password" state of the RTU.
**MITRE ATT&CK for ICS:** T0818 Engineering Workstation Compromise, T0887 Wireless Sniffing (n/a here), T0864 Transient Cyber Asset
**Confirm / exploit with:**
```bash
python3 /opt/scripts/recon.py engws       # dumps notes.txt and water_plc.st
```
**Physical consequence in the sim:** none directly; hands the attacker the credentials and the golden program used in scenarios 8 and 9.
**Fix:** project files and credentials do not sit on an open share. Use a version-controlled project store with access control, keep secrets out of notes files, and network-isolate the engineering workstation (Levels 3/3.5). CISA CPG 2.L (secure credential storage), 2.Q (data at rest); ISA/IEC 62443 asset inventory and least privilege.

---

## Group B, protocol abuse (Modbus/TCP against plc-water)

### 4. Unauthenticated coil / register write stops distribution
**Where:** `plc-water` 172.30.40.20:502
**Real-world parallel:** FrostyGoop, Lviv, Ukraine, January 2024. Malware sent plain Modbus/TCP commands to ENCO controllers and knocked out heat to about 600 apartment buildings for two days.
**Vulnerability:** Modbus/TCP has no authentication, no session, and no integrity check. Any host that can open port 502 can read and write every coil and register.
**MITRE ATT&CK for ICS:** T0855 Unauthorized Command Message, T0836 Modify Parameter, T0831 Manipulation of Control
**Confirm / exploit with:**
```bash
python3 /opt/scripts/modbus_attack.py enum         # read everything
python3 /opt/scripts/modbus_attack.py stop-dist    # HR1 (pressure target) -> 5 psi
```
**Physical consequence in the sim:** the control loop now holds the high-service pump off. Header pressure (PT-401) bleeds from 60 psi toward zero at about 1 psi/s; the `press_low` alarm latches within a minute. The town loses pressure.
**Fix:** Modbus cannot defend itself, so wrap it. Put the PLC on a segment the enterprise and internet cannot route to; allow port 502 only from the HMI and the historian (nftables conduit and the PLC-side `HMI_ALLOWLIST`, both in the segmented topology); validate commanded setpoints in the PLC program against a safe range. CISA CPG 2.F, 5.A (network segmentation); ISA/IEC 62443 conduit filtering.

### 5. Holding-register setpoint tampering, chlorine overdose
**Where:** `plc-water` 172.30.40.20:502, holding register 0 (dose setpoint, ppm x100)
**Real-world parallel:** Oldsmar again: the setpoint change itself was the attack.
**Vulnerability:** the chlorine dose setpoint is a writable holding register with no range check on the write.
**MITRE ATT&CK for ICS:** T0836 Modify Parameter
**Confirm / exploit with:**
```bash
python3 /opt/scripts/modbus_attack.py overdose 15     # write HR0 = 1500
```
**Physical consequence in the sim:** the residual (AIT-301) chases the setpoint upward. It reaches ~4 ppm, at which point the golden program's overdose interlock cuts the metering pump and the residual falls back. The `overdose` alarm flags on the HMI. On its own this attack is contained by the PLC logic; reaching the tap needs scenario 9.
**Fix:** range-check the setpoint in the PLC program (the segmented build clamps HR0 to a safe maximum when `MODBUS_WRITE_OPEN=0`), keep the write off-limits to non-HMI sources, and alarm on out-of-band setpoint changes at the historian. CISA CPG 2.F; ISA/IEC 62443 defensive coding.

### 6. False-data injection / HMI blinding
**Where:** the path between `process-sim`, `plc-water` and `hmi-water`
**Real-world parallel:** Stuxnet recorded normal process values and replayed them to operators while the centrifuges were driven to failure.
**Vulnerability:** the HMI trusts whatever the input registers say. A host on the OT network can hold the mirror registers at a nominal value while the process runs away, or feed the operator a frozen picture.
**MITRE ATT&CK for ICS:** T0856 Spoof Reporting Message, T0832 Manipulation of View, T0815 Denial of View
**Confirm / exploit with:** from the attacker box, repeatedly write the input-register mirror (IR 0-4) or the field-I/O block (HR 10-14) to hold nominal values while running scenario 4 or 5. A tight `pymodbus` loop is the whole exploit.
**Physical consequence in the sim:** the HMI shows a healthy plant while pressure collapses or chlorine climbs. The operator has no reason to act.
**Fix:** cross-check. Compare the HMI's values against an independent read (the historian, a second sensor path), alarm on divergence, and rate-limit / alarm on implausible jumps in the PLC program. The segmented HMI adds a plausibility check that flags a value that moved faster than physics allows. CISA CPG 3.A (log collection and detection); ISA/IEC 62443 integrity monitoring.

---

## Group C, vendor dialects

### 7. S7comm stop-CPU and breaker trip on the substation RTU
**Where:** `plc-power` 172.30.40.22:102
**Real-world parallel:** the stop-CPU and mode-change primitives are a documented class against S7-300/400-era devices; Industroyer/CRASHOVERRIDE used protocol-native commands to operate breakers on the Ukrainian grid in 2016.
**Vulnerability:** the RTU accepts S7 PLC-control functions (stop, start, mode) and data-block writes with no station password.
**MITRE ATT&CK for ICS:** T0816 Device Restart/Shutdown, T0858 Change Operating Mode, T0855 Unauthorized Command Message, T0879 Damage to Property
**Confirm / exploit with:**
```bash
python3 /opt/scripts/s7_attack.py read
python3 /opt/scripts/s7_attack.py trip feeder     # open 52-F: island the bus
python3 /opt/scripts/s7_attack.py trip load       # open 52-L: shed the load
python3 /opt/scripts/s7_attack.py stop            # halt the RTU CPU
```
**Physical consequence in the sim:** opening the feeder breaker islands the bus; with the load shed the generation/load imbalance ramps the frequency up past 53 Hz and the excursion alarm latches. `stop` freezes the RTU: operators keep their screen but lose control, and the sim holds the last outputs.
**Fix:** set a station password / access-protection level on the controller (`S7_NO_PASSWORD=0` makes the RTU refuse unauthenticated stop and breaker-open and re-assert RUN), keep S7comm reachable only from the HMI and historian, and put the RTU in a protected zone. CISA CPG 2.A, 2.F; ISA/IEC 62443 SL-1 authentication on control commands.

### 8. CIP tag write and unauthenticated logic push to the dosing controller
**Where:** `plc-dosing` 172.30.40.21:44818 (EtherNet/IP) and :8080 (logic-update service)
**Real-world parallel:** Rockwell logic-download abuse; the CyberAv3ngers "IOControl" tooling manipulating OT devices in 2023-2024.
**Vulnerability:** CIP tag writes are unauthenticated, and the controller is left in REMOTE with a program-download path that takes no credential.
**MITRE ATT&CK for ICS:** T0843 Program Download, T0889 Modify Program, T0836 Modify Parameter
**Confirm / exploit with:**
```bash
python3 /opt/scripts/cip_attack.py read
python3 /opt/scripts/cip_attack.py set 15         # write DoseSetpoint (contained by the interlock)
python3 /opt/scripts/cip_attack.py logic-push     # POST the unauthenticated download
```
**Physical consequence in the sim:** the tag write drives the metering rate up, but the downstream overdose interlock still catches it near 4 ppm. The logic push sets `LogicForced`: the metering pump pins at 100%, the interlock is bypassed, and the residual runs to about 20 ppm with no ceiling. `LogicRev` increments.
**Honest scope note:** a real Studio 5000 download cannot be emulated without Rockwell tooling. The container runs an unauthenticated logic-update service that swaps its tag logic; it teaches the concept and the detection, not the wire format.
**Fix:** put the controller keyswitch in RUN (`ENIP_ALLOW_LOGIC_DOWNLOAD=0` disables the download service and drops the controller out of REMOTE), require authentication for program changes, alarm on any `LogicRev` change at the historian, and restrict :44818 to the HMI. CISA CPG 2.F, 1.E (change management); ISA/IEC 62443 SL-1/SL-2 on program download.

---

## Group D, impact and persistence

### 9. Modified ladder logic holds the intake pump on
**Where:** `plc-water` OpenPLC runtime UI, 172.30.40.20:8080 (published `127.0.0.1:8073`)
**Real-world parallel:** the general class of control-logic modification; the operator-facing half of Stuxnet.
**Vulnerability:** the runtime accepts a program upload while the keyswitch is in REMOTE, with only the factory `openplc` / `openplc` login. The uploaded program becomes the running control logic.
**MITRE ATT&CK for ICS:** T0889 Modify Program, T0843 Program Download, T0831 Manipulation of Control, T0832 Manipulation of View
**Confirm / exploit with:**
```bash
python3 /opt/scripts/push_logic_water.py          # upload a control program with the 98% interlock removed
```
**Physical consequence in the sim:** with the high-level interlock gone the intake pump stays on past the high setpoint; the raw tank (LT-101) climbs to 100% and overflows. Combined with scenario 8 there is nothing left to stop a chlorine overdose reaching the distribution main.
**Fix:** physical keyswitch in RUN so downloads are refused (`MODBUS_WRITE_OPEN=0` locks the keyswitch in this build), authentication and change control on the runtime, offline signed backups of the golden program, and file-integrity / `LogicRev` alarming. `./reset.sh` reloads the golden program and is the recovery drill. CISA CPG 1.E, 2.A, 7.A (system backups); ISA/IEC 62443 application integrity.

### 10. Wiper-style HMI config clobber
**Where:** `hmi-water`
**Real-world parallel:** CyberAv3ngers "IOControl" and wiper activity against OT assets, 2023-2024.
**Vulnerability:** the HMI's configuration and session state are writable by an authenticated (default-credential) user with no backup or integrity control.
**MITRE ATT&CK for ICS:** T0809 Data Destruction, T0881 Service Stop, T0828 Loss of Productivity and Revenue
**Confirm / exploit with:** authenticate to the HMI with `admin` / `admin` and overwrite its configuration (or clear its state). Reversible.
**Physical consequence in the sim:** the operator loses the screen; the plant keeps running blind on the PLC logic.
**Fix:** back up HMI configuration, restrict administrative functions to named accounts, and keep a known-good image for fast rebuild. `./reset.sh` restores it. CISA CPG 7.A, 5.A; ISA/IEC 62443 backup and recovery.

---

## Framework mapping

| Scenario | MITRE ATT&CK for ICS | CISA CPG | ISA/IEC 62443 |
|---|---|---|---|
| 1 Internet-exposed HMI | T0883, T0812, T0822 | 2.A, 2.F, 2.W | zone boundary, SL-1 auth |
| 2 Unauth remote access | T0822, T0886 | 2.H, 2.W | secure remote access |
| 3 Eng-ws pivot | T0818, T0864 | 2.L, 2.Q | asset inventory, least privilege |
| 4 Modbus write | T0855, T0836, T0831 | 2.F, 5.A | conduit filtering |
| 5 Setpoint tamper | T0836 | 2.F | defensive coding |
| 6 HMI blinding | T0856, T0832, T0815 | 3.A | integrity monitoring |
| 7 S7 stop-CPU / breaker | T0816, T0858, T0855, T0879 | 2.A, 2.F | SL-1 command auth |
| 8 CIP write / logic push | T0843, T0889, T0836 | 2.F, 1.E | SL-1/2 program download |
| 9 Ladder logic swap | T0889, T0843, T0831 | 1.E, 2.A, 7.A | application integrity |
| 10 HMI wiper | T0809, T0881, T0828 | 7.A, 5.A | backup and recovery |

The defended controls line up with the CISA / EPA / AWWA "Top Cyber Actions
for Securing Water Systems" fact sheet: inventory OT assets, reduce internet
exposure, change default passwords, segment IT from OT, and back up
OT systems. `./start.sh --segmented` turns all of them on at once.
