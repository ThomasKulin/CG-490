import datetime
import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import math
import os

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
dataFileName = "40uH_Dimensions"
inductance = 40  # coil inductance [uH]
wireDia = 1.06  # coil wire diameter [mm]
# projectile position (front) [cm]
pos_start = -2
pos_stop = 8
pos_step = 1
# projectile length [cm]
len_start = 3
len_stop = 5
len_step = 1
# projectile radius [cm] (also changes the inner radius of the coil)
rad_start = 0.32
rad_stop = 0.5
rad_step = 0.1

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
    os.makedirs(dataDir)
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
            outerRad, exactLayers, numLayers, numTurns, L = coil.calculateDimensions(projectile.getRadius(), projectile.getLength(), inductance, wireDia / 10)
            coil.setDimensions(projectile.getRadius(), outerRad, projectile.getLength())
            # set coil turns and approximate current
            femm.mi_setcurrent('Coil', 156)
            femm.mi_selectgroup(15)
            femm.mi_setblockprop('18 AWG', 1, 0, 'Coil', 0, 13, 100)

            worksheet.write(0, (l*len(rad_iter)+r) + 1, 'len = ' + str(round(projectile.getLength() * 10)) + ' mm rad = ' + str(round(projectile.getRadius() * 10)) + ' mm Force [N]')

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
                print()

            projectile.moveZ(-len(pos_iter)*pos_step)  # move projectile back to start

    femm.closefemm()
    workbook.close()


class Coil:
    def __init__(self, nodes):
        #            N: 10 (r, z), N 11,     N 12,        N 13
        self.groups = [10, 11, 12, 13]
        self.nodes = nodes

    def getLength(self):
        return self.nodes[0][1] - self.nodes[3][1]

    def getIR(self):
        return self.nodes[0][0]

    def getOR(self):
        return self.nodes[1][1]

    def setDimensions(self, rInner, rOuter, len):
        femm.mi_selectgroup(10)
        femm.mi_movetranslate(rInner - self.nodes[0][0], len - (self.nodes[0][1] - self.nodes[3][1]))
        self.nodes[0][0] = rInner
        self.nodes[0][1] = len + self.nodes[3][1]
        femm.mi_selectgroup(11)
        femm.mi_movetranslate(rOuter - self.nodes[1][0], len - (self.nodes[1][1] - self.nodes[2][1]))
        self.nodes[1][0] = rOuter
        self.nodes[1][1] = len + self.nodes[2][1]
        femm.mi_selectgroup(15)  # block label
        femm.mi_movetranslate(rInner - self.nodes[3][0], 0)
        femm.mi_selectgroup(13)
        femm.mi_movetranslate(rInner - self.nodes[3][0], 0)
        self.nodes[3][0] = rInner
        femm.mi_selectgroup(12)
        femm.mi_movetranslate(rOuter - self.nodes[2][0], 0)
        self.nodes[2][0] = rOuter

    def calculateDimensions(self, r1, length, inductance, wireDia):
        # Wheeler's approx for multilayer inductors is L [uH] = 31.6 * N^2 * r1^2 / (6*r1 + 9*x + 10*(r2-r1))
        # N is number of turns, r1 is inner radius [m], r2 is outer radius [m], x is length [m]
        # rearranging this we can calculate the dimensions of a coil for a specific inductance

        # convert units to inches
        r1 /= 2.54
        length /= 2.54
        wireDia /= 2.54

        turnsPerLayer = length / wireDia  # convert length to mm before dividing by mm
        for numLayers in range(10):
            r2 = wireDia * numLayers + r1
            a = (r1 + r2) / 2
            b = length
            c = r2 - r1
            N = np.sqrt(inductance * (6 * a + 9 * b + 10 * c) / (0.8 * a * a))
            if int(math.ceil(N / turnsPerLayer)) == numLayers:
                L = 0.8 * N * N * a * a / (6 * a + 9 * b + 10 * c)
                return r2 * 2.54, N / turnsPerLayer, numLayers, N, L
                break
        return -1


class Projectile:
    def __init__(self, nodes):
        self.groups = [1, 2, 3, 4]
        self.nodes = nodes

    def getLength(self):
        return self.nodes[0][1] - self.nodes[3][1]

    def getRadius(self):
        return self.nodes[1][0]

    def getXY(self):
        r = (self.nodes[1][0]+self.nodes[0][0])/2
        z = (self.nodes[0][1]+self.nodes[3][1])/2
        return r, z

    def setDimensions(self, rad, len):
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(0, 0)
        femm.mi_selectgroup(2)
        femm.mi_movetranslate(rad - self.nodes[1][0], 0)
        self.nodes[1][0] = rad
        femm.mi_selectgroup(3)
        femm.mi_movetranslate(rad - self.nodes[2][0], -(len + self.nodes[2][1]))
        self.nodes[2][0] = rad
        self.nodes[2][1] = -len
        femm.mi_selectgroup(4)
        femm.mi_movetranslate(0, -(len + self.nodes[3][1]))
        self.nodes[3][1] = -len

    def moveZ(self, mIter):
        if mIter > 0:  # the order you move the points matters for some unknown reason..
            femm.mi_selectgroup(1)
            femm.mi_movetranslate(0, mIter)
            femm.mi_selectgroup(2)
            femm.mi_movetranslate(0, mIter)
            femm.mi_selectgroup(3)
            femm.mi_movetranslate(0, mIter)
            femm.mi_selectgroup(4)
            femm.mi_movetranslate(0, mIter)
        elif mIter < 0:
            femm.mi_selectgroup(4)
            femm.mi_movetranslate(0, mIter)
            femm.mi_selectgroup(3)
            femm.mi_movetranslate(0, mIter)
            femm.mi_selectgroup(2)
            femm.mi_movetranslate(0, mIter)
            femm.mi_selectgroup(1)
            femm.mi_movetranslate(0, mIter)
        # update node coordinate list
        for n in range(len(self.nodes)):
            self.nodes[n][1] += mIter

    def incrementLength(self, lIter):
        femm.mi_selectgroup(3)
        femm.mi_movetranslate(0, -lIter)
        femm.mi_selectgroup(4)
        femm.mi_movetranslate(0, -lIter)
        self.nodes[2][1] -= lIter
        self.nodes[3][1] -= lIter

    def incrementRadius(self, rIter):
        femm.mi_selectgroup(2)
        femm.mi_movetranslate(rIter, 0)
        femm.mi_selectgroup(3)
        femm.mi_movetranslate(rIter, 0)
        self.nodes[1][0] += rIter
        self.nodes[2][0] += rIter

if __name__ == "__main__":
    main()
    # print(calculateCoil(0.0045, 0.032, 40, 0.00106))


