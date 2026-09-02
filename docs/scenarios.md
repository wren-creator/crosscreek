# Cross Creek scenarios, instructor edition

> Stub. Each entry is filled in and its commands verified against the running
> range as the matching service image lands. Trainees work from
> `scenarios-trainee.md`, which is this file with the **Fix** line removed.

Every entry uses this shape:

```
### N. <short title>
**Where:** <segment / host / port / protocol>
**Real-world parallel:** <incident, year>
**Vulnerability:** <mechanism>
**MITRE ATT&CK for ICS:** <technique IDs>
**Confirm / exploit with:** <tool + exact command, hardcoded to lab addresses>
**Physical consequence in the sim:** <what the process does>
**Fix:** <remediation + CISA CPG / ISA-62443 reference>
```

---

## Group A, exposure and access

### 1. Internet-exposed HMI with default credentials
**Where:** `hmi-water`, reachable from `edge-net` via the flat firewall, `:8081`
**Real-world parallel:** Municipal Water Authority of Aliquippa, PA, November 2023 (CyberAv3ngers / Unitronics Vision PLCs, TCP 20256, default password `1111`)
**Vulnerability:** _TBD_
**MITRE ATT&CK for ICS:** T0883 (Internet Accessible Device), T0812 (Default Credentials)
**Confirm / exploit with:** _TBD_
**Physical consequence in the sim:** _TBD_
**Fix:** _TBD_

### 2. Unauthenticated remote access to the OT LAN
**Where:** `eng-ws`, enterprise net
**Real-world parallel:** Oldsmar, FL water treatment, February 2021 (remote desktop into the SCADA HMI)
**MITRE ATT&CK for ICS:** T0822 (External Remote Services), T0886 (Remote Services)
_rest TBD_

### 3. Engineering workstation as a pivot
**Where:** `eng-ws`, holds PLC project files and credentials
**MITRE ATT&CK for ICS:** T0818 (Engineering Workstation Compromise), T0866 (Exploitation of Remote Services)
_rest TBD_

## Group B, protocol abuse (Modbus)

### 4. Unauthenticated coil write stops the distribution pump
**Where:** `plc-water` `:502`
**Real-world parallel:** FrostyGoop, Lviv, Ukraine, January 2024 (raw Modbus/TCP to ENCO controllers)
**MITRE ATT&CK for ICS:** T0855 (Unauthorized Command Message), T0836 (Modify Parameter)
_rest TBD_

### 5. Holding-register setpoint tampering, chlorine overdose
**Where:** `plc-water` `:502` (dosing setpoint mirrored from `plc-dosing`)
**Real-world parallel:** Oldsmar (sodium hydroxide setpoint raised ~100x)
**MITRE ATT&CK for ICS:** T0836 (Modify Parameter)
_rest TBD_

### 6. False-data injection / HMI blinding
**Where:** between `process-sim`, `plc-water`, and `hmi-water`
**Real-world parallel:** Stuxnet (record-and-replay of process values to the operator)
**MITRE ATT&CK for ICS:** T0856 (Spoof Reporting Message), T0832 (Manipulation of View)
_rest TBD_

## Group C, vendor dialects

### 7. S7comm stop-CPU / mode change on the substation RTU
**Where:** `plc-power` `:102`
**MITRE ATT&CK for ICS:** T0816 (Device Restart/Shutdown), T0858 (Change Operating Mode)
_rest TBD_

### 8. CIP tag write and unauthenticated logic push to the dosing controller
**Where:** `plc-dosing` `:44818`
**MITRE ATT&CK for ICS:** T0843 (Program Download), T0889 (Modify Program)
**Honest scope note:** a true Studio 5000 download cannot be emulated without
Rockwell tooling. The container runs an unauthenticated "logic update" service
that swaps its tag logic when `ENIP_ALLOW_LOGIC_DOWNLOAD=1`. It teaches the
concept and the detection, not the exact wire format.
_rest TBD_

## Group D, impact and persistence

### 9. Modified ladder logic holds the intake pump on
**Where:** `plc-water` OpenPLC runtime UI `:8091`
**MITRE ATT&CK for ICS:** T0889 (Modify Program), T0831 (Manipulation of Control)
_rest TBD_

### 10. Wiper-style HMI config clobber
**Where:** `hmi-water`
**Real-world parallel:** CyberAv3ngers IOControl / wiper activity against OT
**MITRE ATT&CK for ICS:** T0809 (Data Destruction), T0881 (Service Stop)
**Reversible:** cleaned by `./reset.sh`.
_rest TBD_

---

## Framework mapping

Filled in with the per-scenario detail: MITRE ATT&CK for ICS technique IDs
(above), CISA Cross-Sector Cybersecurity Performance Goals for each fix, the
CISA/EPA/AWWA "Top Cyber Actions for Securing Water Systems" items, and the
ISA/IEC 62443 zone-and-conduit rationale for the segmented topology.
