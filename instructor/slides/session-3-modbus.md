# Session 3 — Speaking the Machines' Language (Modbus)

## Slide 1: What Modbus is
- 1979. Request/response over TCP 502. Coils (bits) and registers (16-bit words).
- No auth, no session, no signing. Open port 502 = you are the HMI.
- FrostyGoop's Modbus part was function code 6. The same call the HMI makes every second.

## Slide 2: Enumerate
- `modbus_attack.py enum` — coils, discretes, holding, input registers
- Match to the HMI: coil 0 intake pump, coil 1 dist pump, HR0 dose setpoint x100, HR1 pressure target
- Derive the map from the HMI; full map is in `mapfile.py`

## Slide 3: Stop the distribution pump (scenario 4)
- Writing coil 1 = 0 fails: logic re-asserts it in 200 ms
- Lesson: a PLC with running logic fights you — attack what the logic *reads*
- `modbus_attack.py stop-dist` → HR1 = 5 psi → pump held off → header bleeds to 0

## Slide 4: Overdose the chlorine (scenario 5)
- `modbus_attack.py overdose 15` → HR0 = 1500
- Residual climbs to ~4 ppm then the interlock cuts dosing — **contained by PLC logic**
- This is the Oldsmar attack, and Oldsmar was caught. The dangerous version needs step 2.

## Slide 5: Blind the operator (scenario 6)
- HMI reads IR 0–4; sim writes the field block; PLC mirrors it
- Write the mirror faster than the sim → operator sees a healthy plant
- Stuxnet's operator-facing trick, in miniature

## Slide 6: What you should notice
- No credential, no exploit — and the only thing that saved water quality was an interlock an engineer coded
- The pressure loop had no interlock and fell over immediately
- Session 5 can't fix Modbus. It fixes everything around it.
