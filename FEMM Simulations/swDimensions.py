import datetime
import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import math
import os

from objects import Coil
from objects import Projectile

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
# dataFileName = "60uH_Dimensions"
dataFileName = 'R0.1 Dimensions'
# coil params
inductance = 60  # coil inductance [uH]
wireDiameter = 1.06  # coil wire diameter [mm]
wireResistivity = 20.9 / 1000  # coil wire resistance per length [ohm/m]
wireResistance = 0.1  # resistance in [ohm]
# circuit params
circuitResistance = 0.15  # [ohm]
# projectile position (front) [cm]
pos_start = -2
pos_stop = 8
pos_step = 1
# projectile length [cm]
len_start = 4
len_stop = 4
len_step = 1
# projectile radius [cm] (also changes the inner radius of the coil)
rad_start = 0.45
rad_stop = 0.45
rad_step = 0.16

def main():
    coil = Coil([[0.32, 3], [3.32, 3], [3.32, 2], [0.32, 2]])
    projectile = Projectile([[0, 0], [0.32, 0], [0.32, -1], [0, -1]])
    # set up FEMM stuff
    femm.openfemm()
    femm.opendocument(filename + ".fem")
    femm.mi_saveas("temp.fem")
    femm.mi_seteditmode("group")

    # set up data capture
    DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
    dataDir = 'Data\\DimensionSweep ' + DateTime
    os.makedirs(dataDir, exist_ok=True)
    workbook = xl.Workbook(dataDir + '\\' + dataFileName + ".xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, 'Position [cm]')

    # Calculate required iterations
    pos_iter = np.arange(pos_start, pos_stop+0.001, pos_step)
    len_iter = np.arange(len_start, len_stop+0.001, len_step)
    rad_iter = np.arange(rad_start, rad_stop+0.001, rad_step)

    z = [[[0 for p in range(len(pos_iter))] for r in range(len(rad_iter))] for l in range(len(len_iter))]
    f = [[[0 for p in range(len(pos_iter))] for r in range(len(rad_iter))] for l in range(len(len_iter))]
    for l in range(len(len_iter)):
        print("Length Iteration: " + str(l))

        for r in range(len(rad_iter)):
            # set projectile and coil geometry
            projectile.setDimensions(rad_iter[r], len_iter[l])

            # outerRad, exactLayers, numLayers, wireLength, wireResistance, numTurns, L = coil.fixedInductance(projectile.getRadius(), projectile.getLength(), inductance, wireDiameter / 10, wireResistivity)
            outerRad, exactLayers, numLayers, R, wireLength, numTurns, L = coil.fixedResistance(projectile.getRadius(), projectile.getLength(), wireResistance, wireDiameter / 10, wireResistivity)

            coil.setDimensions(projectile.getRadius(), outerRad, projectile.getLength())
            # set coil turns and approximate current
            coilCurrent = 50 / (R + circuitResistance)
            femm.mi_setcurrent('Coil', coilCurrent)
            femm.mi_selectgroup(15)
            femm.mi_setblockprop('18 AWG', 1, 0, 'Coil', 0, 15, numTurns)
            femm.mi_movetranslate(0, 0)  # solves a bug where group 15 doesn't deselect until a movetranslate

            worksheet.write(0, (l*len(rad_iter)+r) + 1, 'len = ' + str(round(projectile.getLength() * 10)) + ' mm rad = ' + str(round(projectile.getRadius() * 10)) + ' mm Force [N]')

            print("Radius Iteration:", r, "\tLayers:", numLayers, "\t Turns:", numTurns, '\tCoil Length:', round(projectile.getLength(), 6), '[cm]', '\tCurrent:', round(coilCurrent, 6), '[A]\tIR:', round(projectile.getRadius(), 6), '[cm]', '\tOR:', round(outerRad, 6), '[cm]', '\tWire Length:', wireLength, '[m]', '\tWire Resistance:' + str(round(R,4)) + '[ohm]', '\tInductance', L, '[uH]')

            for p in range(len(pos_iter)):
                femm.mi_analyze()
                femm.mi_loadsolution()
                x, y = projectile.getXY()
                femm.mo_selectblock(x, y)  # select projectile block
                fz = femm.mo_blockintegral(19)  # calculate force applied to projectile
                z[l][r][p] = pos_iter[p]
                f[l][r][p] = fz

                # data capture out
                worksheet.write(p + 1, 0, z[l][r][p])
                worksheet.write(p + 1, (l*len(rad_iter)+r) + 1, f[l][r][p])

                projectile.moveZ(pos_step)  # move projectile forward by pos_step cm

            projectile.moveZ(-len(pos_iter)*pos_step)  # move projectile back to start

    femm.closefemm()
    workbook.close()

if __name__ == "__main__":
    main()
    # print(calculateProperties(0.0045, 0.032, 40, 0.00106))


