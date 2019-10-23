import datetime
import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import math
import os

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swDimensions"
dataFileName = "60uH_Dimensions"
# coil params
inductance = 60  # coil inductance [uH]
wireDiameter = 1.06  # coil wire diameter [mm]
wireResistivity = 20.9 / 1000  # coil wire resistance per length [ohm/m]
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
            outerRad, exactLayers, numLayers, wireLength, wireResistance, numTurns, L = coil.calculateProperties(projectile.getRadius(), projectile.getLength(), inductance, wireDiameter / 10, wireResistivity)
            coil.setDimensions(projectile.getRadius(), outerRad, projectile.getLength())
            # set coil turns and approximate current
            coilCurrent = 50 / (wireResistance + circuitResistance)
            femm.mi_setcurrent('Coil', coilCurrent)
            femm.mi_selectgroup(15)
            femm.mi_setblockprop('18 AWG', 1, 0, 'Coil', 0, 15, numTurns)
            femm.mi_movetranslate(0, 0)  # solves a bug where group 15 doesn't deselect until a movetranslate

            worksheet.write(0, (l*len(rad_iter)+r) + 1, 'len = ' + str(round(projectile.getLength() * 10)) + ' mm rad = ' + str(round(projectile.getRadius() * 10)) + ' mm Force [N]')

            print("Radius Iteration:", r, "\tLayers:", numLayers, "\t Turns:", numTurns, '\tCoil Length:', round(projectile.getLength(), 6), '[cm]', '\tCurrent:', round(coilCurrent, 6), '[A]\tIR:', round(projectile.getRadius(), 6), '[cm]', '\tOR:', round(outerRad, 6), '[cm]', '\tWire Length:', wireLength, '[m]', '\tWire Resistance:', wireResistance, '[ohm]', )

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
        femm.mi_selectgroup(11)
        femm.mi_movetranslate(rOuter - self.nodes[1][0], len - (self.nodes[1][1] - self.nodes[2][1]))
        self.nodes[1][0] = rOuter
        self.nodes[1][1] = len + self.nodes[2][1]
        femm.mi_selectgroup(12)
        femm.mi_movetranslate(rOuter - self.nodes[2][0], 0)
        self.nodes[2][0] = rOuter
        femm.mi_selectgroup(15)  # block label
        femm.mi_movetranslate(rInner - self.nodes[3][0], 0)
        femm.mi_selectgroup(10)
        femm.mi_movetranslate(rInner - self.nodes[0][0], len - (self.nodes[0][1] - self.nodes[3][1]))
        self.nodes[0][0] = rInner
        self.nodes[0][1] = len + self.nodes[3][1]
        femm.mi_selectgroup(13)
        femm.mi_movetranslate(rInner - self.nodes[3][0], 0)
        self.nodes[3][0] = rInner


    def calculateProperties(self, r1, length, inductance, wireDia, wireRes):
        # Wheeler's approx for multilayer inductors is L [uH] = 31.6 * N^2 * r1^2 / (6*r1 + 9*x + 10*(r2-r1))
        # N is number of turns, r1 is inner radius [m], r2 is outer radius [m], x is length [m]
        # rearranging this we can calculate the dimensions of a coil for a specific inductance

        # convert units to inches
        r1_inches = r1/2.54
        length_inches = length/2.54
        wireDia_inches = wireDia/2.54

        turnsPerLayer = int(length_inches / wireDia_inches)  # convert length to mm before dividing by mm
        for numLayers in range(100):
            r2_inches = wireDia_inches * numLayers + r1_inches
            a = (r1_inches + r2_inches) / 2
            b = length_inches
            c = r2_inches - r1_inches
            N = np.sqrt(inductance * (6 * a + 9 * b + 10 * c) / (0.8 * a * a))
            if int(math.ceil(N / turnsPerLayer)) <= numLayers:
                L = 0.8 * N * N * a * a / (6 * a + 9 * b + 10 * c)  # calculate final coil inductance
                wireLength = 0
                remainingTurns = N
                for n in range(numLayers):
                    if remainingTurns >= turnsPerLayer:
                        wireLength += 2 * np.pi * (r1/100 + wireDia/200 + n*wireDia/100) *turnsPerLayer
                        remainingTurns -= turnsPerLayer
                    else:
                        wireLength += 2 * np.pi * (r1 / 100 + wireDia / 2000) * remainingTurns
                        remainingTurns -= remainingTurns
                wireResistance = wireRes * wireLength
                return r2_inches * 2.54, N / turnsPerLayer, numLayers, wireLength, wireResistance, N, L
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
    # print(calculateProperties(0.0045, 0.032, 40, 0.00106))


