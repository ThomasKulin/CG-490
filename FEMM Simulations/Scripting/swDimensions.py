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

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
# dataFileName = "L40 Dimensions"
dataFileName = 'R0.1 Dimensions'
# coil params
inductance = 40  # coil inductance [uH]
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
len_start = 3
len_stop = 7
len_step = 1
# projectile radius [cm] (also changes the inner radius of the coil)
rad_start = 0.2
rad_stop = 1
rad_step = 0.2

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
    forcesheet = workbook.add_worksheet('Force vs. Position')
    indsheet = workbook.add_worksheet('Coil vs. Inductance')
    forcesheet.write(0, 0, 'Position [cm]')
    indsheet.write(0, 0, 'Coil Geometry')
    indsheet.write(0, 1, 'Inductance [uH]')

    # Calculate required iterations
    pos_iter = np.arange(pos_start, pos_stop+0.001, pos_step)
    len_iter = np.arange(len_start, len_stop+0.001, len_step)
    rad_iter = np.arange(rad_start, rad_stop+0.001, rad_step)

    z = [[[0 for p in range(len(pos_iter))] for r in range(len(rad_iter))] for l in range(len(len_iter))]  # z position
    f = [[[0 for p in range(len(pos_iter))] for r in range(len(rad_iter))] for l in range(len(len_iter))]  # force
    w = [[0 for r in range(len(rad_iter))] for l in range(len(len_iter))]  # sum of total positive work
    v = [[0 for r in range(len(rad_iter))] for l in range(len(len_iter))]  # resulting velocity from work calc
    for l in range(len(len_iter)):
        print("Length Iteration: " + str(l))

        for r in range(len(rad_iter)):
            # set projectile and coil geometry
            projectile.setDimensions(rad_iter[r], len_iter[l])

            # outerRad, exactLayers, numLayers, wireLength, R, numTurns, L = coil.fixedInductance(projectile.getRadius(), projectile.getLength(), inductance, wireDiameter / 10, wireResistivity)
            outerRad, exactLayers, numLayers, R, wireLength, numTurns, L = coil.fixedResistance(projectile.getRadius(), projectile.getLength(), wireResistance, wireDiameter / 10, wireResistivity)

            coil.setDimensions(projectile.getRadius(), outerRad, projectile.getLength())
            # set coil turns and approximate current
            coilCurrent = 50 / (R + circuitResistance)
            femm.mi_setcurrent('Coil', coilCurrent)
            femm.mi_selectgroup(15)
            femm.mi_setblockprop('18 AWG', 1, 0, 'Coil', 0, 15, numTurns)
            femm.mi_movetranslate(0, 0)  # solves a bug where group 15 doesn't deselect until a movetranslate

            forcesheet.write(0, (l*len(rad_iter)+r) + 1, 'len = ' + str(round(projectile.getLength() * 10)) + ' mm rad = ' + str(round(projectile.getRadius() * 10)) + ' mm Force [N]')
            indsheet.write((l*len(rad_iter)+r) + 1, 0, 'len = ' + str(round(projectile.getLength() * 10)) + ' mm rad = ' + str(round(projectile.getRadius() * 10)) + ' mm')
            indsheet.write((l*len(rad_iter)+r) + 1, 1, L)
            indsheet.write((l * len(rad_iter) + r) + 1, 2, R+circuitResistance)
            print("Radius Iteration:", r, "\tLayers:", numLayers, "\t Turns:", numTurns, '\tCoil Length:', round(projectile.getLength(), 6), '[cm]', '\tCurrent:', round(coilCurrent, 6), '[A]\tIR:', round(projectile.getRadius(), 6), '[cm]', '\tOR:', round(outerRad, 6), '[cm]', '\tWire Length:', wireLength, '[m]', '\tWire Resistance:' + str(round(R,4)) + '[ohm]', '\tInductance', L, '[uH]')

            for p in range(len(pos_iter)):
                femm.mi_analyze()
                femm.mi_loadsolution()
                x, y = projectile.getXY()
                femm.mo_selectblock(x, y)  # select projectile block
                fz = femm.mo_blockintegral(19)  # calculate force applied to projectile
                z[l][r][p] = pos_iter[p]
                f[l][r][p] = fz
                w[l][r] += f[l][r][p]*pos_step/100 if f[l][r][p] > 0 else 0  # sum f x delta d for all positive values of force
                v[l][r] = np.sqrt(2*w[l][r]/projectile.getMass())
                # data capture out
                forcesheet.write(p + 1, 0, z[l][r][p])
                forcesheet.write(p + 1, (l*len(rad_iter)+r) + 1, f[l][r][p])

                projectile.moveZ(pos_step)  # move projectile forward by pos_step cm

            projectile.moveZ(-len(pos_iter)*pos_step)  # move projectile back to start

    femm.closefemm()
    workbook.close()
    # save data
    np.save(dataDir + '\\z.npy', z)
    np.save(dataDir + '\\f.npy', f)
    np.save(dataDir + '\\w.npy', w)
    np.save(dataDir + '\\v.npy', v)
    np.save(dataDir + '\\len.npy', len_iter)
    np.save(dataDir + '\\rad.npy', rad_iter)

    plotSurf(len_iter, rad_iter, w)
    plotSurf(len_iter, rad_iter, v)

def plotSurf(X, Y, Z):
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    X, Y = np.meshgrid(X, Y)
    # Plot the surface.
    surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    # Customize the z axis.
    ax.set_zlim(0, 5)
    ax.zaxis.set_major_locator(LinearLocator(10))
    ax.zaxis.set_major_formatter(FormatStrFormatter('%.02f'))
    # Add a color bar which maps values to colors.
    fig.colorbar(surf, shrink=0.5, aspect=5)
    plt.show()


if __name__ == "__main__":
    main()
