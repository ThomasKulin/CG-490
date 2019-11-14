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
from Scripting.objects import LTSpice

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
testType = 'inductance'
# testType = 'resistance'
dataFileName = "swInductanceVsTime" if testType == 'inductance' else 'swResistanceVsTime'
# coil params
length = 4  # coil length [cm]
r_inner = 0.45  # coil inner radius [cm]
wireDiameter = 1.06  # coil wire diameter [mm]
wireResistivity = 20.9 / 1000  # coil wire resistance per length [ohm/m]
# circuit params
circuitResistance = 0.15  # [ohm]
# projectile params
pos_start = -0.5  # [cm]
pos_end = 6
# time [s]
time_start = 0
time_stop = 5e-2
time_step = 5e-5
# coil inductance [uH] , changes R_outer
ind_start = 20
ind_stop = 140
ind_step = 20
# coil resistance [ohm] , changes R_outer
res_start = 0.01
res_stop = 0.1
res_step = 0.01

def main():
    coil = Coil([[0.32, 3], [3.32, 3], [3.32, 2], [0.32, 2]])
    projectile = Projectile([[0, 0], [0.32, 0], [0.32, -1], [0, -1]])


    # set up FEMM stuff
    femm.openfemm()
    femm.opendocument('..\\'+ filename + ".fem")
    femm.mi_saveas('..\\'+"temp.fem")
    femm.mi_seteditmode("group")

    # set up data capture
    DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
    dataDir = '..\\'+'Data\\TimeRLSweep ' + DateTime
    os.makedirs(dataDir, exist_ok=True)
    workbook = xl.Workbook(dataDir + '\\' + dataFileName + ".xlsx")
    # worksheet = None
    # Calculate required iterations
    time_iter = np.arange(time_start, time_stop + 1e-7, time_step)
    var_iter = []
    if testType == 'resistance':
        var_iter = np.arange(res_start, res_stop + 1e-7, res_step)
    elif testType == 'inductance':
        var_iter = np.arange(ind_start, ind_stop + 1e-7, ind_step)
    else:
        exit()

    z = [[coil.getTriggerPosition()/100 for p in range(len(time_iter))] for r in range(len(var_iter))]  # z position
    f = [[0 for p in range(len(time_iter))] for r in range(len(var_iter))]  # force
    a = [[0 for r in range(len(time_iter))] for l in range(len(var_iter))]  # acceleration
    v = [[0 for r in range(len(time_iter))] for l in range(len(var_iter))]  # velocity
    I = [[0 for r in range(len(time_iter))] for l in range(len(var_iter))]  # coil current
    stage = 0
    for r in range(len(var_iter)):
        # set projectile and coil geometry
        projectile.setDimensions(r_inner, length)

        if testType == 'resistance':
            outerRad, exactLayers, numLayers, R, wireLength, numTurns, L = coil.fixedResistance(r_inner, length, var_iter[r], wireDiameter / 10, wireResistivity)
            worksheet = initializeSheet(workbook, 'R' + str(var_iter[r]))
        else:
            outerRad, exactLayers, numLayers, wireLength, R, numTurns, L = coil.fixedInductance(r_inner, length, var_iter[r], wireDiameter / 10, wireResistivity)
            worksheet = initializeSheet(workbook, 'L' + str(var_iter[r]))

        coil.setDimensions(r_inner, outerRad, length)
        # set coil turns and approximate current
        on_data, off_data = coil.calculateCoilResponse( L/1e6, R)
        peakCurrent = (max(on_data[1]))
        print("Variable Iteration:", r, "\tLayers:", numLayers, "\t Turns:", numTurns, '\tCoil Length:', round(projectile.getLength(), 6), '[cm]', '\tCurrent:', round(peakCurrent, 6), '[A]\tIR:', round(projectile.getRadius(), 6), '[cm]', '\tOR:', round(outerRad, 6), '[cm]', '\tWire Length:', wireLength, '[m]', '\tWire Resistance:' + str(round(R,4)) + '[ohm]', '\tInductance', L, '[uH]')

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
