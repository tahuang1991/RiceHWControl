# The software control for Tenney T2C temperature cycling chamber from TPS company, and the control unit of chamber is WATLOW F4T. 


This softwares use Standard Commands for Programmable Instruments (SCPI) via Ethernet to control F4T, which controls the temperature of the chamber.  

* F4TSCPI.py: define the class F4TSCPI to setup communication with F4T, and control/readout F4T. e.g. get_pv() is to read processing temperature (= current chamber temperature), get_sp() is to read setting temperature, set_sp() is to set the setting temperature.
* TPS_thermal_test.py: test code to run a thermal cycle using F4TSCPI class and log the data for every 5min:
  * step1: set the temperature ramp rate to 1 C/min
  * step2: ramp to 50C
  * step3: hold at 50C for 40min
  * step4: ramp to -35C
  * step5: hold at -35C for 40min
  * step6: ramp to room temperature, 20C.

## Relevant Docs
The relevant docs can be found under doc/. 

The WATLOW F4T: https://www.watlow.com/resources-and-support/technical-library/user-manuals?keyw=F4


