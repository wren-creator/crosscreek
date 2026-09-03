(*
   crosscreek_ro_v1  -  Cross Creek RO demineralisation plant
   Target: soft PLC, scan 200 ms
   This listing mirrors logic/golden_water.py. The runtime executes the Python
   view; this is the operator-readable copy shown in the runtime UI.

   Areas:  1xxx feed / pretreatment   2xxx RO   3xxx DI loop
*)

PROGRAM main
  VAR
    (* --- process values (from process-sim via HR 10..22) --- *)
    feed_flow      : REAL;   (* m3/h  1FQIAHL101 *)
    feed_press     : REAL;   (* bar   1PT105 *)
    ro1_cond       : REAL;   (* uS/cm 1QAH301 *)
    ro2_cond       : REAL;   (* uS/cm 2QAH401 *)
    ro2_press      : REAL;   (* bar   2PT301 *)
    di_tank        : REAL;   (* %     3B401 *)
    loop_press     : REAL;   (* bar   3PITC401 *)
    loop_ret_cond  : REAL;   (* uS/cm loop return *)
    uv_intensity   : REAL;   (* %     3UV401 *)
    antisc_tank    : REAL;   (* % *)

    (* --- setpoints --- *)
    loop_press_sp  : REAL := 3.80;
    tank_lo_sp     : REAL := 40.0;
    tank_hi_sp     : REAL := 85.0;
    cond_limit     : REAL := 2.00;    (* release limit, 2QAH401 *)
    cond_hard      : REAL := 10.0;    (* hard-stop pass 2 *)
    uv_min         : REAL := 70.0;

    (* --- outputs --- *)
    seq_ro         : BOOL;
    seq_loop       : BOOL;
    seq_cip        : BOOL;
    p101_antisc    : BOOL;   (* 1P101 *)
    p102_feed      : BOOL;   (* 1P102 *)
    p301_ro1       : BOOL;   (* 2P301 *)
    p302_ro2       : BOOL;   (* 2P302 *)
    p401_loop      : BOOL;   (* 3P401 *)
    uv401          : BOOL;   (* 3UV401 *)
    freigabe       : BOOL;   (* release to consumers *)
    bypass_ilk     : BOOL;   (* operator release-interlock bypass *)
  END_VAR

  (* --- RO makeup on DI tank level --- *)
  IF di_tank <= tank_lo_sp THEN
    seq_ro := TRUE;
  ELSIF di_tank >= tank_hi_sp THEN
    seq_ro := FALSE;
  END_IF;
  IF seq_cip THEN seq_ro := FALSE; END_IF;

  (* --- feed / pretreatment --- *)
  p102_feed   := seq_ro AND (NOT seq_cip);
  p101_antisc := p102_feed AND (antisc_tank > 2.0);

  (* --- RO passes --- *)
  p301_ro1 := p102_feed AND (feed_press > 1.0);
  p302_ro2 := p301_ro1 AND (ro1_cond < 50.0);
  IF (ro2_cond > cond_hard) AND (NOT bypass_ilk) THEN
    p302_ro2 := FALSE;
  END_IF;

  (* --- DI loop --- *)
  seq_loop  := TRUE;
  p401_loop := seq_loop;
  uv401     := seq_loop;

  (* --- release interlock: Freigabe an Mischerei --- *)
  freigabe := ( (ro2_cond <= cond_limit)
            AND (loop_ret_cond <= cond_limit)
            AND (uv_intensity >= uv_min)
            AND (di_tank > 10.0) )
            OR bypass_ilk;

END_PROGRAM
