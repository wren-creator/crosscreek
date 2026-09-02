# Cross Creek scenarios, trainee edition

> Stub. This is `scenarios.md` with the **Fix** line removed from each entry:
> work out the remediation yourself, then check it against the instructor
> edition. Generated alongside the instructor edition as each scenario is
> proven against the running range.

The ten planted weaknesses, in four groups:

**Group A, exposure and access**
1. Internet-exposed HMI with default credentials (Aliquippa, 2023)
2. Unauthenticated remote access to the OT LAN (Oldsmar, 2021)
3. Engineering workstation as a pivot

**Group B, protocol abuse (Modbus)**
4. Unauthenticated coil write stops the distribution pump (FrostyGoop, 2024)
5. Holding-register setpoint tampering, chlorine overdose (Oldsmar)
6. False-data injection / HMI blinding (Stuxnet-style)

**Group C, vendor dialects**
7. S7comm stop-CPU / mode change on the substation RTU
8. CIP tag write and unauthenticated logic push to the dosing controller

**Group D, impact and persistence**
9. Modified ladder logic holds the intake pump on
10. Wiper-style HMI config clobber (reversible, cleaned by `./reset.sh`)

For each: find where it lives, confirm it, trigger the physical consequence in
the simulation, then design and test the fix. Session by session, the *Cross
Creek 101* syllabus walks you through it.
