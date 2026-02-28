from F4TSCPI import F4TSCPI

f4t = F4TSCPI("192.168.0.100")
f4t.connect()
print("IDN:", f4t.idn())

mode = f4t.cascade_get_control(cas=1)   # :SOURce:CAScade1:CONTrol?
print("Cascade1 control mode:", mode)

enabled = (mode.strip().upper() != "OFF")
print("Cascade enabled?", enabled)
