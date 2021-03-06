import datetime
import femm
import xlsxwriter as xl
import numpy as np
import os

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter

from Scripting.objects import Coil
from Scripting.objects import Projectile
from Scripting.objects import Iron

# TEST PARAMS --- Units in cm
filename = "swIronThickness"
dataFileName = "swIronVsTime"
# coil params
length = 4  # coil length [cm]
r_inner = 0.45  # coil inner radius [cm]
wireDiameter = 1.06  # coil wire diameter [mm]
wireResistivity = 20.9 / 1000  # coil wire resistance per length [ohm/m]
inductance = 100
# circuit params
circuitResistance = 0.15  # [ohm]
# projectile params
pos_start = -0.5  # [cm]
pos_end = 6
v_start = 15  # starting velocity in [m/s]
# time [s]
time_start = 0
time_stop = 5e-2
time_step = 5e-5
# iron thickness in [cm]
iron_start = 0.1
iron_stop = 0.5
iron_step = 0.1


def main():
    coil = Coil([[0.32, 3], [3.32, 3], [3.32, 2], [0.32, 2]])
    iron = Iron([[0.32, 3.1], [3.42, 3.1], [3.42, 1.9], [0.32, 1.9]])
    projectile = Projectile([[0, 0], [0.32, 0], [0.32, -1], [0, -1]])


    # set up FEMM stuff
    femm.openfemm()
    femm.opendocument('..\\'+ filename + ".fem")
    femm.mi_saveas('..\\'+"temp.fem")
    femm.mi_seteditmode("group")

    # set up data capture
    DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
    dataDir = '..\\'+'Data\\TimeIronSweep ' + DateTime
    os.makedirs(dataDir, exist_ok=True)
    workbook = xl.Workbook(dataDir + '\\' + dataFileName + ".xlsx")
    # worksheet = None
    # Calculate required iterations
    time_iter = np.arange(time_start, time_stop + 1e-7, time_step)
    var_iter = np.arange(iron_start, iron_stop + 1e-7, iron_step)

    z = [[coil.getTriggerPosition()/100 for p in range(len(time_iter))] for r in range(len(var_iter))]  # z position
    f = [[0 for p in range(len(time_iter))] for r in range(len(var_iter))]  # force
    a = [[0 for r in range(len(time_iter))] for l in range(len(var_iter))]  # acceleration
    v = [[v_start for r in range(len(time_iter))] for l in range(len(var_iter))]  # velocity
    I = [[0 for r in range(len(time_iter))] for l in range(len(var_iter))]  # coil current
    stage = 0
    for r in range(len(var_iter)):
        # set projectile and coil geometry
        projectile.setDimensions(r_inner, length)

        outerRad, exactLayers, numLayers, wireLength, R, numTurns, L = coil.fixedInductance(r_inner, length, inductance, wireDiameter / 10, wireResistivity)
        iron.setDimensions(r_inner, outerRad+5, length+5)
        coil.setDimensions(r_inner, outerRad, length)
        washer_thickness = wrap_thickness = var_iter[r]
        iron.setThickness(washer_thickness, wrap_thickness, coil, includeWrap=False)
        # set coil turns and approximate current
        on_data, off_data = coil.calculateCoilResponse( L/1e6, R)
        peakCurrent = (max(on_data[1]))
        print("Variable Iteration:", r, "\tIron Thickness:", round(var_iter[r], 4), "\tLayers:", numLayers, "\t Turns:", numTurns, '\tCoil Length:', round(projectile.getLength(), 6), '[cm]', '\tCurrent:', round(peakCurrent, 6), '[A]\tIR:', round(projectile.getRadius(), 6), '[cm]', '\tOR:', round(outerRad, 6), '[cm]', '\tWire Length:', wireLength, '[m]', '\tWire Resistance:' + str(round(R,4)) + '[ohm]', '\tInductance', L, '[uH]')
        worksheet = initializeSheet(workbook, str(var_iter[r]*10)+" mm")
        coilOn = True
        offTime = 0
        projectile.setPosition(coil.getTriggerPosition())  # set start pos
        for i in range(1, len(time_iter)):# start at 1 because initial conditions are zero and I want that to be reflected in data
            if coilOn:
                I[r][i] = calculateCurrent(on_data, time_iter[i])
            else:
                I[r][i] = calculateCurrent(off_data, time_iter[i]-offTime)

            coil.setCoilCurrent(I[r][i])

            femm.mi_analyze()
            femm.mi_loadsolution()
            x, y = projectile.getXY()
            femm.mo_selectblock(x, y)  # select projectile block
            f[r][i] = femm.mo_blockintegral(19)  # calculate force applied to projectile

            # calculate kinematics stuffs
            a[r][i] = f[r][i] / projectile.getMass()
            v[r][i] = v[r][i - 1] + a[r][i] * time_step
            z[r][i] = z[r][i - 1] + v[r][i] * time_step

            worksheet.write(i, 0, round(time_iter[i], 6))
            worksheet.write(i, 1, stage + 1)
            worksheet.write(i, 2, round(z[r][i], 6))
            worksheet.write(i, 3, round(z[r][i], 6))
            worksheet.write(i, 4, round(v[r][i], 6))
            worksheet.write(i, 5, round(a[r][i], 6))
            worksheet.write(i, 6, round(f[r][i], 6))
            worksheet.write(i, 7, round(I[r][i], 6))
            print("Iteration # " + str(i) + '\tTime = ' + str(round(time_iter[i], 6)) + '\tz = ' + str(
                round(z[r][i], 6)) + '\tv = ' + str(round(v[r][i], 6)) + '\ta = ' + str(round(a[r][i], 6)) + '\tI = ' + str(round(I[r][i], 6)))

            if projectile.getPosition() - projectile.getLength() > coil.getTriggerPosition() and coilOn:
                coilOn = False
                offTime = time_iter[i]
            if not coilOn and I[r][i] < 1e-3:
                break;
            projectile.moveZ(v[r][i]*time_step * 100)  # move projectile forward by pos_step cm
        projectile.setPosition(coil.getTriggerPosition())  # set start pos

    femm.closefemm()
    workbook.close()
    # save data
    np.save(dataDir + '\\z.npy', z)
    np.save(dataDir + '\\f.npy', f)
    np.save(dataDir + '\\a.npy', a)
    np.save(dataDir + '\\v.npy', v)
    np.save(dataDir + '\\I.npy', I)
    np.save(dataDir + '\\var.npy', var_iter)


def initializeSheet(workbook, name):
    worksheet = workbook.add_worksheet(name=name)
    worksheet.write(0, 0, 'Time [s]')
    worksheet.write(0, 1, 'Stage #')
    worksheet.write(0, 2, 'Position wrt. Stage [cm]')
    worksheet.write(0, 3, 'Position [cm]')
    worksheet.write(0, 4, 'Velocity [m/s]')
    worksheet.write(0, 5, 'Acceleration [m/s^2]')
    worksheet.write(0, 6, 'Force [N]')
    worksheet.write(0, 7, 'Current [A]')

    return worksheet


def calculateCurrent(coilResponse, instantaneous_time):
    time = list(coilResponse[0])
    current = list(coilResponse[1])
    voltage = list(coilResponse[2])
    nearest_time = min(time, key=lambda x: abs(x - instantaneous_time))
    index = time.index(nearest_time)
    return current[index]


if __name__ == "__main__":
    main()
