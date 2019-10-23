import datetime
import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import os

# TEST PARAMS --- Units in cm
# filename = "7mmCoil_192T_156A"
# filename = "3.2mmCoil_100T_246A"
filename = "14mmDia"

current = 246
sensorPos = 0.005

pos_start = -0.02  # starting position of front of projectile in meters
mass = 0.018  # mass of projectile in Kg
# length = 0.07  # projectile length in meters
length = 0.032

time_step = 1e-4  # time increments to use
time_stop = 5e-2  # time to stop simulation
maxStages = 9


# set up FEMM stuff
femm.openfemm()
femm.opendocument(filename + ".fem")
femm.mi_saveas("temp_time.fem")
femm.mi_seteditmode("group")

# set up data capture
DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
dataDir = 'Data\\TimeSweep ' + DateTime
os.makedirs(dataDir, exist_ok=True)
workbook = xl.Workbook(dataDir + '\\' + filename + ".xlsx")
worksheet = workbook.add_worksheet()

worksheet.write(0, 8, 'Mass [Kg]')
worksheet.write(1, 8, mass)

worksheet.write(0, 0, 'Time [s]')
worksheet.write(0, 1, 'Stage #')
worksheet.write(0, 2, 'Position wrt. Stage [cm]')
worksheet.write(0, 3, 'Position [cm]')
worksheet.write(0, 4, 'Velocity [m/s]')
worksheet.write(0, 5, 'Acceleration [m/s^2]')
worksheet.write(0, 6, 'Force [N]')

# variable set up
time_list = list(np.arange(0.0, time_stop, time_step))
z = [pos_start for i in range(len(time_list))]  # position at end of timestep [m]
z_tot = [pos_start for i in range(len(time_list))]  # position at end of timestep [m]
v = [0 for i in range(len(time_list))]  # velocity at end of timestep [m/s]
a = [0 for i in range(len(time_list))]  # Acceleration [m/s^2]
f = [0 for i in range(len(time_list))]  # Force in z-direction [N/Kg]
stage = 0  # lets us pass the projectile through the coil multiple times

for i in range(1, len(time_list)):  # start at 1 because initial conditions are zero and I want that to be reflected in data
    # worksheet.write(0, i + 1, str(round((iron_start + i * iron_step)*10)) + ' mm Force [N]')

    femm.mi_analyze()
    femm.mi_loadsolution()
    femm.mo_groupselectblock(1)  # select group 1 (projectile)
    fz = femm.mo_blockintegral(19)  # calculate force applied to projectile
    f[i] = fz

    # calculate kinematics stuffs
    a[i] = f[i]/mass
    v[i] = v[i-1] + a[i]*time_step
    z[i] = z[i-1] + v[i]*time_step
    z_tot[i] = z_tot[i-1] + v[i]*time_step

    if z[i] - length > -sensorPos:
        femm.mi_setcurrent('Coil', 0)  # set coil current to 0 when back of projectile passes -0.5cm (light sensor location)
    if z[i] > length + sensorPos:
        # loop the projectile through identical coil
        femm.mi_setcurrent('Coil', current)  # set current back to 156 A
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(0, -(z[i] + sensorPos)*100)
        z[i] = -0.005
        stage += 1

    # move projectile forward
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, v[i]*time_step * 100)  # convert to cm

    worksheet.write(i, 0, round(time_list[i], 6))
    worksheet.write(i, 1, stage+1)
    worksheet.write(i, 2, round(z[i], 6))
    worksheet.write(i, 3, round(z_tot[i], 6))
    worksheet.write(i, 4, round(v[i], 6))
    worksheet.write(i, 5, round(a[i], 6))
    worksheet.write(i, 6, round(f[i], 6))
    print("Iteration # " + str(i) + '\tTime = ' + str(round(time_list[i], 6)) + '\tz = ' + str(
        round(z[i], 6)) + '\tv = ' + str(round(v[i], 6)) + '\ta = ' + str(round(a[i], 6)))

    if stage >= maxStages:
        break

plt.plot(time_list,f)
plt.show()
plt.plot(time_list,a)
plt.show()
plt.plot(time_list,v)
plt.show()
plt.plot(time_list,z)
plt.show()
femm.closefemm()
workbook.close()