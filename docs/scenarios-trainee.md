# Cross Creek scenarios, trainee edition

Eleven planted weaknesses in four groups. Scenario 11 is numbered last but is
where you start: it is the reconnaissance the rest assume. This is the trainee edition with the
**Fix** paragraph removed from each entry: work out the remediation yourself,
then check it against `scenarios.md`. Every command below was run from the
`attacker` container against the running flat range.

Each entry gives you where it lives, the real incident it mirrors, the
mechanism, the MITRE ATT&CK for ICS techniques, the command that proves it,
and the physical consequence in the simulation. The fix is yours to design.

Get a shell on the attacker box first:

```bash
docker exec -it crosscreek-attacker bash
ls /opt/scripts
```

---

## Recon methodology: don't assume the port

None of the three PLCs in this range sits on its IANA-assigned default port
(Modbus 502, S7comm 102, EtherNet/IP 44818; see `PLC_WATER_PORT` /
`PLC_POWER_PORT` / `PLC_DOSING_PORT` in `.env.example`). That's deliberate. A
real assessment can't assume the default either, and treating a hardcoded
ICS-port list as the whole recon phase is exactly the mistake that gets
written up as "three PLCs, no findings."

**Standard methodology, in order:**
1. **Full port discovery.** `nmap -Pn -sS -p- --min-rate 2000 <host>` (the
   attacker container carries `NET_RAW` for the SYN scan; without it, `-sT`
   works the same way, just slower), or `python3 /opt/scripts/recon.py nmap`,
   which runs this against every host DNS handed you. A default `nmap` run
   only checks the top 1000 ports and will miss all three field protocols
   here.
2. **Service, name, model and version, where nmap can get it for free.**
   Point nmap's vendor NSE scripts at whatever came back open: `nmap -Pn -sV
   --script modbus-discover,s7-info,enip-info -p<port> <host>`. Each script
   speaks enough of its protocol's own identification exchange to pull
   device type, model, serial number and firmware/revision, and `recon.py
   nmap` runs this stage automatically against whatever step 1 found. **The
   catch:** all three scripts key off the protocol's textbook port (or a
   service name nmap already recognised), so on a moved port like these they
   often print nothing, `-sV` just reports `unknown`. That's not a dead end,
   it's the reason step 3 exists.
3. **Register / tag enumeration confirms it either way.** `python3
   /opt/scripts/recon.py registers` talks the actual protocol, no generic
   scanner heuristics involved, and dumps `plc-water`'s coils, discrete
   inputs, holding and input registers, `plc-power`'s raw DB1 bytes, and
   `plc-dosing`'s known CIP tags. Modbus and S7 addressing is numeric and
   carries no data dictionary, so this is a genuine blind walk;
   matching the raw values to `3P401`, `HR_COND_LIMIT_US` and so on is
   scenario-specific and comes from cross-referencing the HMI or the
   engineering workstation's project files (scenario 3).

Every scenario below still gives the exact `host:port` to attack once you have
found it; those numbers now reflect where the range actually put them, not
the protocol's textbook default.

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
**Fix:** _work this out, then check the instructor edition._

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
**Fix:** _work this out, then check the instructor edition._

### 3. Engineering workstation as a pivot
**Where:** `eng-ws` 172.30.20.20:8080, sharing `/opt/projects`
**Vulnerability:** the workstation serves its project directory over plain HTTP, including `notes.txt`, which lists every controller address, the OpenPLC web login, and the "no station password" state of the RTU.
**MITRE ATT&CK for ICS:** T0818 Engineering Workstation Compromise, T0887 Wireless Sniffing (n/a here), T0864 Transient Cyber Asset
**Confirm / exploit with:**
```bash
python3 /opt/scripts/recon.py engws       # dumps notes.txt and water_plc.st
```
**Physical consequence in the sim:** none directly; hands the attacker the credentials and the golden program used in scenarios 8 and 9.
**Fix:** _work this out, then check the instructor edition._

### 11. Estate discovery via an open DNS zone transfer
**Where:** `dns` 172.30.10.53, the utility's authoritative name server for `crosscreek-water.lab` and `crosscreek-power.lab`. It sits on `edge-net` with the attacker box, so there is no firewall in the path.
**Numbered last, run first.** This is the reconnaissance the other ten scenarios assume you have already done.
**Vulnerability:** the name server answers for the internal estate, every HMI, PLC and the engineering workstation, and allows a zone transfer to any client. One query returns the whole asset inventory by function, with addresses. The reverse zone maps the OT `/24` too.
**MITRE ATT&CK for ICS:** T0888 Remote System Information Discovery, T0846 Remote System Discovery; (enterprise) T1590.002 Gather Victim Network Information: DNS
**Confirm / exploit with:**
```bash
python3 /opt/scripts/recon.py dns                 # AXFR both zones + a reverse sweep
dig axfr @172.30.10.53 crosscreek-water.lab
dig axfr @172.30.10.53 crosscreek-power.lab
nmap -Pn -sL 172.30.40.0/24                       # names from reverse DNS, no packets to the hosts
nmap -Pn -sT -p 22,8080 crosscreek-water.lab crosscreek-power.lab   # the field protocols aren't in this list on purpose, see above
```
The transfer also shows both "separate" utilities resolving `eng-ws` and `historian` to the same boxes.
**Physical consequence in the sim:** none directly. It turns a blind `/16` sweep into a handful of targeted connections and lowers the attacker's noise.
**Fix:** _work this out, then check the instructor edition._

---

## Group B, protocol abuse (Modbus/TCP against plc-water, the RO plant)

### 4. Unauthenticated write stops the DI distribution loop
**Where:** `plc-water` 172.30.40.20:10502, coil 4 (3P401 loop circulation pump)
**Real-world parallel:** FrostyGoop, Lviv, Ukraine, January 2024. Malware sent plain Modbus/TCP commands to ENCO controllers and knocked out heat to about 600 apartment buildings for two days.
**Vulnerability:** Modbus/TCP has no authentication, no session, and no integrity check. Any host that can open the Modbus port (10502 here, not the IANA default 502) can read and write every coil and register.
**MITRE ATT&CK for ICS:** T0855 Unauthorized Command Message, T0831 Manipulation of Control, T0813 Denial of Control
**Confirm / exploit with:**
```bash
python3 /opt/scripts/modbus_attack.py enum         # read everything
python3 /opt/scripts/modbus_attack.py stop-loop    # 3P401 -> HAND, then STOP
```
**Physical consequence in the sim:** the DI loop circulation pump stops. Loop pressure (3PITC401) bleeds from 3.8 bar toward zero at about 1.5 bar/s; `DI_LOOP_PRESS_LOW` latches within a couple of seconds. The point-of-use (the "point of use") loses supply.
**Fix:** _work this out, then check the instructor edition._

### 5. Setpoint tampering: raise the release conductivity limit
**Where:** `plc-water` 172.30.40.20:10502, holding register 5 (`HR_COND_LIMIT_US`, x100)
**Real-world parallel:** Oldsmar, February 2021: the setpoint change itself was the attack (the sodium hydroxide setpoint went from ~100 to ~11,100 ppm).
**Vulnerability:** the conductivity limit that gates "Release to Consumers" (release to the consumers) is a writable holding register with no range check.
**MITRE ATT&CK for ICS:** T0836 Modify Parameter, T0806 Brute Force I/O (n/a), T0839 Module Firmware (n/a)
**Confirm / exploit with:**
```bash
python3 /opt/scripts/modbus_attack.py raise-limit 5.0    # HR5 -> 500 (5.00 uS/cm)
python3 /opt/scripts/modbus_attack.py starve-antiscalant # foul the membranes to make it matter
```
**Physical consequence in the sim:** on its own the raised limit changes nothing visible. Combined with the antiscalant starve, the RO membranes foul (1QAH301 climbs 12 -> 50 uS/cm over ~30 s, then 2QAH401 follows past 2 uS/cm), but because the limit is now 5.0, `DI_COND_HIGH_RO2` never trips and Release stays true. Off-spec DI water is released. Without the raised limit, the interlock catches the degradation and holds Release off, this attack is contained by the PLC logic.
**Fix:** _work this out, then check the instructor edition._

### 6. False-data injection / HMI blinding
**Where:** the path between `process-sim`, `plc-water` and `hmi-water`
**Real-world parallel:** Stuxnet recorded normal process values and replayed them to operators while the centrifuges were driven to failure.
**Vulnerability:** the HMI trusts whatever the input registers say. A host on the OT network can hold the mirror registers at a nominal value while the process runs away, or feed the operator a frozen picture.
**MITRE ATT&CK for ICS:** T0856 Spoof Reporting Message, T0832 Manipulation of View, T0815 Denial of View
**Confirm / exploit with:** from the attacker box, repeatedly write the input-register mirror (IR 0-15) or the field-I/O block (HR 10-22) to hold nominal values while running scenario 4 or 5. A tight `pymodbus` loop is the whole exploit.
**Physical consequence in the sim:** the HMI shows RO2 conductivity at 0.5 uS/cm and Release green while the loop is actually circulating off-spec water. The operator has no reason to act.
**Fix:** _work this out, then check the instructor edition._

---

## Group C, vendor dialects

### 7. S7comm stop-CPU and breaker trip on the substation RTU
**Where:** `plc-power` 172.30.40.22:10102
**Real-world parallel:** the stop-CPU and mode-change primitives are a documented class against S7-family devices; Industroyer/CRASHOVERRIDE used protocol-native commands to operate breakers on the Ukrainian grid in 2016.
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
**Fix:** _work this out, then check the instructor edition._

### 8. CIP tag write and unauthenticated logic push to the NaOH dosing controller
**Where:** `plc-dosing` 172.30.40.21:54818 (EtherNet/IP) and :8080 (logic-update service). `plc-dosing` is the Allen-Bradley-style controller for the RO inter-pass NaOH (caustic) dosing, tags `DoseSetpoint`, `DoseRate`, `LogicRev`, `LogicForced`.
**Real-world parallel:** Rockwell logic-download abuse; the CyberAv3ngers "IOControl" tooling manipulating OT devices in 2023-2024.
**Vulnerability:** CIP tag writes are unauthenticated, and the controller is left in REMOTE with a program-download path that takes no credential.
**MITRE ATT&CK for ICS:** T0843 Program Download, T0889 Modify Program, T0836 Modify Parameter
**Confirm / exploit with:**
```bash
python3 /opt/scripts/cip_attack.py read
python3 /opt/scripts/cip_attack.py set 15         # write DoseSetpoint (contained by the interlock)
python3 /opt/scripts/cip_attack.py logic-push     # POST the unauthenticated download
```
**Physical consequence in the sim:** the tag write drives the NaOH metering rate up; the caustic overdose pushes RO2 conductivity (2QAH401) past 2 uS/cm, but the release interlock catches it and holds Release off. The logic push sets `LogicForced`: the metering pump pins at 100% and the pushed program also drives the loop return conductivity up sharply (contaminant term), so `DI_COND_HIGH_LOOP` latches, Release is firmly blocked, and the DI loop is circulating off-spec water. `LogicRev` increments. Getting that water *released* still needs scenario 5 (raise the limit) or scenario 9 (remove the interlock).
**Honest scope note:** a real Studio 5000 download cannot be emulated without Rockwell tooling. The container runs an unauthenticated logic-update service that swaps its tag logic; it teaches the concept and the detection, not the wire format.
**Fix:** _work this out, then check the instructor edition._

---

## Group D, impact and persistence

### 9. Modified control program removes the release interlock
**Where:** `plc-water` OpenPLC runtime UI, 172.30.40.20:8080 (published `127.0.0.1:8073`)
**Real-world parallel:** the general class of control-logic modification; the operator-facing half of Stuxnet.
**Vulnerability:** the runtime accepts a program upload while the keyswitch is in REMOTE, with only the factory `openplc` / `openplc` login. The uploaded program becomes the running control logic.
**MITRE ATT&CK for ICS:** T0889 Modify Program, T0843 Program Download, T0831 Manipulation of Control, T0832 Manipulation of View
**Confirm / exploit with:**
```bash
python3 /opt/scripts/push_logic_water.py          # upload a program that forces Release true and drops the RO2 hard-safety
```
**Physical consequence in the sim:** the running program is now `crosscreek_ro_v1_PATCHED`. "Release to Consumers" is forced true regardless of conductivity or UV, and the RO2 hard-safety no longer stops pass 2 on grossly off-spec permeate. Chain it with scenario 5 or 8 to degrade the water and it flows to the consumers with nothing left to stop it. On its own it is a latent failure: the safety is gone but nothing bad is happening yet.
**Fix:** _work this out, then check the instructor edition._

### 10. Wiper-style HMI config clobber
**Where:** `hmi-water`
**Real-world parallel:** CyberAv3ngers "IOControl" and wiper activity against OT assets, 2023-2024.
**Vulnerability:** the HMI's configuration and session state are writable by an authenticated (default-credential) user with no backup or integrity control.
**MITRE ATT&CK for ICS:** T0809 Data Destruction, T0881 Service Stop, T0828 Loss of Productivity and Revenue
**Confirm / exploit with:** authenticate to the HMI with `admin` / `admin` and overwrite its configuration (or clear its state). Reversible.
**Physical consequence in the sim:** the operator loses the screen; the plant keeps running blind on the PLC logic.
**Fix:** _work this out, then check the instructor edition._

---

## Framework mapping

| Scenario | MITRE ATT&CK for ICS | CISA CPG | ISA/IEC 62443 |
|---|---|---|---|
| 1 Internet-exposed HMI | T0883, T0812, T0822 | 2.A, 2.F, 2.W | zone boundary, SL-1 auth |
| 2 Unauth remote access | T0822, T0886 | 2.H, 2.W | secure remote access |
| 3 Eng-ws pivot | T0818, T0864 | 2.L, 2.Q | asset inventory, least privilege |
| 4 Stop the DI loop pump (Modbus) | T0855, T0831, T0813 | 2.F, 5.A | conduit filtering |
| 5 Raise the release limit (Modbus) | T0836 | 2.F | defensive coding |
| 6 HMI blinding | T0856, T0832, T0815 | 3.A | integrity monitoring |
| 7 S7 stop-CPU / breaker | T0816, T0858, T0855, T0879 | 2.A, 2.F | SL-1 command auth |
| 8 CIP write / logic push | T0843, T0889, T0836 | 2.F, 1.E | SL-1/2 program download |
| 9 Remove the release interlock (program swap) | T0889, T0843, T0831 | 1.E, 2.A, 7.A | application integrity |
| 10 HMI wiper | T0809, T0881, T0828 | 7.A, 5.A | backup and recovery |

The defended controls line up with the CISA / EPA / AWWA "Top Cyber Actions
for Securing Water Systems" fact sheet: inventory OT assets, reduce internet
exposure, change default passwords, segment IT from OT, and back up
OT systems. `./start.sh --segmented` turns all of them on at once.
