# run_thermal_test.py
import time
import csv
from datetime import datetime
from f4t_scpi import F4T

def read_tps_pv_sp(f4t, retries=5, retry_delay=1):
    for attempt in range(1, retries + 1):
        try:
            f4t.connect()
            return f4t.get_pv(1), f4t.get_sp(1)
        except Exception as exc:
            #print(f"TPS read attempt {attempt}/{retries} failed: {exc}")
            try:
                f4t.close()
            except Exception:
                pass
            if attempt == retries:
                print(f"TPS read attempt {attempt}/{retries} failed: {exc}")
                raise
            time.sleep(retry_delay)

def log_row(writer, pv,sp, phase):
    ts = datetime.now().isoformat(timespec="seconds")
    #pv = f4t.get_pv(1)
    #sp = f4t.get_sp(1)
    #pv,sp = read_tps_pv_sp(f4t)
    writer.writerow([ts, phase, pv, sp])


def ramp_minutes(writer, f4t, target_temp, sample_min=5):

    f4t.connect()
    f4t.set_cp(target_temp, 1)
    current_pv, current_sp = read_tps_pv_sp(f4t)
    print(f"Ramping to target temp {target_temp}C. Current PV: {current_pv}C at time {datetime.now().isoformat(timespec='seconds')}")
    phase = f"RAMP_TO_{target_temp}C"
    ilog = 0
    next_sample = 0.0
    while abs(current_pv - target_temp) > 0.5:
        now = time.time()
        current_pv, current_sp = read_tps_pv_sp(f4t)
        if now >= next_sample:
            #print(f"Current PV: {current_pv}C, waiting to reach target temp {target_temp}C")
            log_row(writer, current_pv, current_sp, phase)
            next_sample = now + sample_min * 60
            ilog += 1
            if ilog %10 == 0:
                print(f"Still ramping to target temp {target_temp}C. Current PV: {current_pv}C; logged {ilog} times so far.")
        time.sleep(10)
    print(f"Reached target temp {target_temp}C. Current PV: {current_pv}C at time {datetime.now().isoformat(timespec='seconds')}")
    f4t.close()


def hold_minutes(writer, f4t, target_temp, minutes, sample_min=5):

    print(f"Reached target temp {target_temp}C. Starting hold time of {minutes} minutes at {datetime.now().isoformat(timespec='seconds')}")
    phase = f"HOLDING_AT_{target_temp}C"
    end = time.time() + minutes * 60
    next_sample = 0
    ilog = 0
    while time.time() < end:
        now = time.time()
        if now >= next_sample:
            current_pv, current_sp = read_tps_pv_sp(f4t)
            log_row(writer, current_pv, current_sp, phase)
            next_sample = now + sample_min * 60
            ilog += 1
            if ilog %10 == 0:
                print(f"Still holding at target temp {target_temp}C. Current PV: {current_pv}C; logged {ilog} times so far.")
        time.sleep(10)


def run_test():
    with F4T("192.168.0.100") as f4t:
        print("Connected:", f4t.idn())

        # configure ramp behavior
        f4t.set_ramp_scale_minutes(1)
        f4t.set_ramp_action_setpoint(1)
        f4t.set_ramp_rate(2.0, 1)  # 1 °C/min

        with open("thermal_log.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "phase", "temp_pv", "temp_sp"])

            # ramp to 50
            ramp_minutes(w, f4t, 50, 5)

            # hold for 40min
            hold_minutes(w, f4t, 50, 40, 5)

            # ramp to -35
            ramp_minutes(w, f4t, -35.0, 5)

            # hold for 40min
            hold_minutes(w, f4t, -35.0, 40, 5)

            # ramp to room temp 20
            ramp_minutes(w, f4t, 20.0, 5)

    print("Test finished → thermal_log.csv")


if __name__ == "__main__":
    run_test()
