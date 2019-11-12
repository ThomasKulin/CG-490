import datetime
import femm
import xlsxwriter as xl
import numpy as np
import os

from Scripting.objects import Coil
from Scripting.objects import Projectile

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
dataFileName = "32mm_rad_vs_ind"
# coil params
ind_start = 10  # coil inductance [uH]
ind_stop = 100
ind_step = 10
wireDiameter = 1.06  # coil wire diameter [mm]
wireResistivity = 20.9 / 1000  # coil wire resistance per length [ohm/m]
# circuit params
circuitResistance = 0.15  # [ohm]

# projectile position (front) [cm]
pos_start = -2
pos_stop = 8
pos_step = 1
# projectile radius [cm] (also changes the inner radius of the coil)
rad_start = 0.45
rad_stop = 0.45
rad_step = 0.16
length = 3.2  # projectile length [cm]

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
    dataDir = 'Data\\InductanceSweep ' + DateTime
    os.makedirs(dataDir, exist_ok=True)
    workbook = xl.Workbook(dataDir + '\\' + dataFileName + ".xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, 'Position [cm]')

    # Calculate required iterations
    pos_iter = np.arange(pos_start, pos_stop+0.001, pos_step)
    ind_iter = np.arange(ind_start, ind_stop + 0.001, ind_step)
    rad_iter = np.arange(rad_start, rad_stop+0.001, rad_step)

    z = [[[0 for p in range(len(pos_iter))] for r in range(len(rad_iter))] for l in range(len(ind_iter))]
    f = [[[0 for p in range(len(pos_iter))] for r in range(len(rad_iter))] for l in range(len(ind_iter))]
    for l in range(len(ind_iter)):
        print("Inductance Iteration: " + str(l))

        for r in range(len(rad_iter)):
            # set projectile and coil geometry
            projectile.setDimensions(rad_iter[r], length)
            outerRad, exactLayers, numLayers, wireLength, wireResistance, numTurns, L = coil.fixedInductance(projectile.getRadius(), projectile.getLength(), ind_iter[l], wireDiameter / 10, wireResistivity)
            coil.setDimensions(projectile.getRadius(), outerRad, projectile.getLength())
            # set coil turns and approximate current
            coilCurrent = 50 / (wireResistance + circuitResistance)
            femm.mi_setcurrent('Coil', coilCurrent)
            femm.mi_selectgroup(15)
            femm.mi_setblockprop('18 AWG', 1, 0, 'Coil', 0, 15, numTurns)
            femm.mi_movetranslate(0, 0)  # solves a bug where group 15 doesn't deselect until a movetranslate

            worksheet.write(0, (l*len(rad_iter)+r) + 1, 'ind = ' + str(round(ind_iter[l], 6)) + ' uH rad = ' + str(round(projectile.getRadius() * 10, 6)) + ' mm Force [N]')

            print("Radius Iteration:", r, "\tLayers:", numLayers, "\t Turns:", numTurns, '\tCoil Inductance:', round(ind_iter[l], 6), '[uH]', '\tCurrent:', round(coilCurrent, 6), '[A]\tIR:', round(projectile.getRadius(), 6), '[cm]', '\tOR:', round(outerRad, 6), '[cm]', '\tWire Length:', wireLength, '[m]', '\tWire Resistance:', wireResistance, '[ohm]', )

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
