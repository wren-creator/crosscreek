(*
   crosscreek_water_v1  -  Cross Creek water plant control
   Target: soft PLC, scan 200 ms
   This listing mirrors logic/golden_water.py. The runtime executes the Python
   view; this is the operator-readable copy shown in the runtime UI.
*)

PROGRAM main
  VAR
    raw_level      : REAL;   (* %  from LT-101 *)
    treated_level  : REAL;   (* %  from LT-201 *)
    chlorine_ppm   : REAL;   (* ppm from AIT-301 *)
    header_psi     : REAL;   (* psi from PT-401 *)
    flow_gpm       : REAL;   (* gpm from FT-302 *)

    level_low_sp   : REAL := 35.0;
    level_high_sp  : REAL := 85.0;
    press_target   : REAL := 60.0;
    safe_max_ppm   : REAL := 4.0;

    intake_pump    : BOOL;   (* P-101 *)
    dist_pump      : BOOL;   (* P-401 *)
    dose_enable    : BOOL;   (* MP-301 metering pump *)
    bypass_ilk     : BOOL;   (* operator interlock bypass *)
  END_VAR

  (* --- raw water intake, hysteresis --- *)
  IF raw_level <= level_low_sp THEN
    intake_pump := TRUE;
  ELSIF raw_level >= level_high_sp THEN
    intake_pump := FALSE;
  END_IF;

  (* high-level interlock: hard stop unless bypassed *)
  IF (raw_level >= 98.0) AND (NOT bypass_ilk) THEN
    intake_pump := FALSE;
  END_IF;

  (* --- chlorine dosing --- *)
  dose_enable := flow_gpm > 1.0;
  IF chlorine_ppm >= safe_max_ppm THEN
    dose_enable := FALSE;
  END_IF;

  (* --- distribution header pressure --- *)
  IF header_psi < (press_target - 3.0) THEN
    dist_pump := TRUE;
  ELSIF header_psi > (press_target + 3.0) THEN
    dist_pump := FALSE;
  END_IF;

  IF treated_level < 10.0 THEN
    dist_pump := FALSE;
  END_IF;

END_PROGRAM
