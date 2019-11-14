from objects import LTSpice
import matplotlib.pyplot as plt

asc_filepath = "..\\SPICE Dependencies\\offTime.asc"
raw_filepath = "..\\SPICE Dependencies\\offTime.raw"
exe_path = "C:\\Program Files\\LTC\\LTspiceXVII\\XVIIx64.exe"
spice = LTSpice(asc_filepath, raw_filepath, exe_path)

spice.set_param('I_COIL', 100)
spice.simulate()

time = spice.getTime()
V_out = spice.getData('V(Vo)')
I_L1 = spice.getData('I(L1)')

plt.plot(time, V_out)
plt.plot(time, I_L1)
plt.show()

