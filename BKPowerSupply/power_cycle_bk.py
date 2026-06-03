import sys, os, time
# Add the directory to the beginning of sys.path (higher priority)
#bkmodule_dir = os.path.expanduser('~/Documents/RiceHWControl/BKPowerSupply/')
#sys.path.insert(0, bkmodule_dir)

import serial
from BKPowerSupply import PSUConfig, BKPowerSupply
from  BK1697B import BK1697B

def power_cycle_bk1697b(power_cycle = True, voltage=9.0, current=5.0, verbose = True):
    psu = BK1697B('/dev/ttyACM0')

    print("Device:", psu.get_idn())
    #print("SCPI version:", psu.get_version())

    psu.set_voltage(voltage) #V
    psu.set_current(current) #A
    sleep_time = 2
    print("Voltage setting:", psu.get_voltage_setting())
    print("Current limit setting:", psu.get_current_setting())
    out_status = psu.get_output_state()
    print("output status: ", "ON" if out_status else "OFF")

    if not out_status:
        psu.turnon_output()
        time.sleep(sleep_time)
        if verbose:
            print("Output enabled")
    elif power_cycle:
       psu.turnoff_output()
       time.sleep(sleep_time)
       psu.turnon_output()
       time.sleep(sleep_time)
       if verbose:
           print("power cycle completed")

    if verbose: 
        print(f"BK1697B Measured voltage: {psu.measure_voltage()} V")
        print(f"BK1697B Measured current: {psu.measure_current()} A")
        print(f"BK1697B Measured power: {psu.measure_power()} W")
    
    measured_current = psu.measure_current()
    measured_voltage = psu.measure_voltage()
    measured_power = psu.measure_power()
    if abs(measured_current*measured_voltage-measured_power) > 0.5:
        print("Power measurement discrepancy detected!")

    return psu


def power_cycle_bk9410(channel = 0, power_cycle = True, voltage=9.0, current=6.0, ipstr = "192.168.0.40", verbose = True):
    # Configure PSU settings here
    config = PSUConfig()
    config.protocol = "IP" # "IP" for Ethernet, "Serial" for USB
    config.IP = ipstr
    #config.COM = "/dev/ttyACM0"

    psu = BKPowerSupply(config)
    PSUChannel = channel # Set the channel you want to use here!

    # These are no longer necessary, since the PSU will print on its own during startup
    #print("Device:", psu.get_idn())
    #print("SCPI version:", psu.get_version())

    psu.set_voltage(voltage, PSUChannel) #V
    psu.set_current(current, PSUChannel) #A
    sleep_time = 2
    if verbose:
        print(f"Ch={PSUChannel} Voltage setting: {psu.get_voltage(PSUChannel)} V")
        print(f"Ch={PSUChannel} Current limit setting: {psu.get_current(PSUChannel)} A")

    out_status = psu.get_channel_state(PSUChannel)
    if verbose:
        #print(f"Ch={PSUChannel} output status {out_status}")
        print(f"Ch={PSUChannel} output status: ", "ON" if out_status else "OFF")

    if not out_status:
        psu.enable_channel(PSUChannel)
        time.sleep(sleep_time)
        if verbose:
            print("Output enabled")
    elif power_cycle:
       psu.disable_channel(PSUChannel)
       time.sleep(sleep_time)
       psu.enable_channel(PSUChannel)
       time.sleep(sleep_time)
       if verbose:
           print("power cycle completed")

    if verbose: 
        print(f"Ch={PSUChannel} BKPS Measured voltage: {psu.measure_voltage(PSUChannel)} V")
        print(f"Ch={PSUChannel} BKPS Measured current: {psu.measure_current(PSUChannel)} A")
        print(f"Ch={PSUChannel} BKPS Measured power: {psu.measure_power(PSUChannel)} W")
        
    measured_current = psu.measure_current(PSUChannel)
    measured_voltage = psu.measure_voltage(PSUChannel)
    measured_power = psu.measure_power(PSUChannel)
    if abs(measured_current*measured_voltage-measured_power) > 0.5:
        print("Power measurement discrepancy detected!")
    return psu

#if __name__ == '__main__':
