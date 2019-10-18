import datetime
import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import math
import os

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
inductance = 40  # coil inductance [uH]
wireDia = 1.06  # coil wire diameter [mm]
# projectile position (front) [cm]
pos_start = -2
pos_stop = 14
pos_step = 1
# projectile length [cm]
len_start = 1
len_stop = 7
len_step = 1
# projectile radius [cm] (also changes the inner radius of the coil)
rad_start = 0.32
rad_stop = 0.5
rad_step = 0.025

def main():
    # set up FEMM stuff
    femm.openfemm()
    femm.opendocument(filename + ".fem")
    femm.mi_saveas("temp.fem")
    femm.mi_seteditmode("group")

    # set up data capture
    DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
    dataDir = 'Data\\IronThickness ' + DateTime
    os.makedirs(dataDir)
    workbook = xl.Workbook(dataDir + '\\' + filename + ".xlsx")
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, 'Position [cm]')

    # Calculate required iterations
    pos_iter = int((pos_stop-pos_start)/pos_step) + 1
    len_iter = int((len_stop - len_start) / len_step) + 1
    rad_iter = int((rad_stop - rad_start) / rad_step) + 1

    z = [[0 for n in range(pos_iter)] for i in range(len_iter)]
    f = [[0 for n in range(pos_iter)] for i in range(len_iter)]
    for l in range(len_iter):
        print("Length Iteration: " + str(l))
        currentLength = len_start + l * len_step

        for r in range(rad_iter):
            currentRad = rad_start+r*rad_iter
            worksheet.write(0, (l*len(r)+r) + 1, 'len = '+str(round(currentLength * 10)) + ' mm rad = '+ str(round(currentRad*10)) +' mm Force [N]')

            for p in range(pos_iter):
                print("Position Iteration: " + str(p))
                femm.mi_analyze()
                femm.mi_loadsolution()
                femm.mo_groupselectblock(1)  # select group 1 (projectile)
                fz = femm.mo_blockintegral(19)  # calculate force applied to projectile
                z[l][p] = pos_start + p * pos_step
                f[l][p] = fz

                # data capture out
                worksheet.write(p + 1, 0, z[l][p])
                worksheet.write(p + 1, l + 1, f[l][p])

                moveProjectile(pos_step)  # move projectile forward by pos_step cm

            moveProjectile(-pos_iter*pos_step)  # move projectile back to start

            if r != len(rad_iter)-1:  # on last iteration don't increment the radius (this results in a radius that doesnt get run and propagates to next length loop)
                projectileRadius(rad_iter)  # increment projectile radius
                coilRadius(rad_iter)  # increment coil radius
                calculateCoil(currentRad/100, currentLength/100, inductance, wireDia/1000)

        projectileRadius(-rad_iter*rad_step)  # reset projectile radius
        coilRadius(-rad_iter*rad_step)  # reset coil radius

        projectileLength(len_step)  # increment projectile length

    femm.closefemm()
    workbook.close()


def moveProjectile(mIter):
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, mIter)
    femm.mi_selectgroup(2)
    femm.mi_movetranslate(0, mIter)
    femm.mi_selectgroup(3)
    femm.mi_movetranslate(0, mIter)
    femm.mi_selectgroup(4)
    femm.mi_movetranslate(0, mIter)


def projectileLength(lIter):
    femm.mi_selectgroup(3)
    femm.mi_movetranslate(0, -lIter)
    femm.mi_selectgroup(4)
    femm.mi_movetranslate(0, -lIter)


def projectileRadius(rIter):
    femm.mi_selectgroup(2)
    femm.mi_movetranslate(rIter, 0)
    femm.mi_selectgroup(3)
    femm.mi_movetranslate(rIter, 0)


def coilRadius(rIter):
    print("not done")


def calculateCoil(r1, length, inductance, wireDia):
    # Wheeler's approx for multilayer inductors is L [uH] = 31.6 * N^2 * r1^2 / (6*r1 + 9*x + 10*(r2-r1))
    # N is number of turns, r1 is inner radius [m], r2 is outer radius [m], x is length [m]
    # rearranging this we can calculate the dimensions of a coil for a specific inductance
    turnsPerLayer = length / wireDia  # convert length to mm before dividing by mm
    for numLayers in range(10):
        r2 = wireDia*numLayers + r1
        N = np.sqrt(inductance*(6*r1 + 9*length + 10*(r2-r1))/(31.6*math.pow(r1, 2)))
        if int(math.ceil(N/turnsPerLayer)) == numLayers:
            L = 31.6 * N*N * r1*r1 / (6*r1 + 9*length + 10*(r2-r1))
            return r2, numLayers, N, L
            break
    return -1

if __name__ == "__main__":
    # main()
    print(calculateCoil(0.0045, 0.032, 40, 0.00106))

