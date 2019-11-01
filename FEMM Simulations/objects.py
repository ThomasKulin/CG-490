import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import math


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


    def fixedInductance(self, r1, length, inductance, wireDia, wireRes):
        # Wheeler's approx for multilayer inductors is L [uH] = 31.6 * N^2 * r1^2 / (6*r1 + 9*x + 10*(r2-r1))
        # N is number of turns, r1 is inner radius [m], r2 is outer radius [m], x is length [m]
        # rearranging this we can calculate the dimensions of a coil for a specific inductance

        # convert units to inches
        r1_inches = r1/2.54
        length_inches = length/2.54
        wireDia_inches = wireDia/2.54

        turnsPerLayer = length_inches / wireDia_inches
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


    def fixedResistance(self, r1, length, resistance, wireDia, wireRes):
        # Wheeler's approx for multilayer inductors is L [uH] = 31.6 * N^2 * r1^2 / (6*r1 + 9*x + 10*(r2-r1))
        # N is number of turns, r1 is inner radius [m], r2 is outer radius [m], x is length [m]
        # rearranging this we can calculate the dimensions of a coil for a specific inductance

        # convert units to inches
        r1_inches = r1/2.54
        length_inches = length/2.54
        wireDia_inches = wireDia/2.54
        turnsPerLayer = length_inches / wireDia_inches
        wireLength = resistance/wireRes  # wire length in meters
        remainingWire = wireLength
        numLayers = 1
        N = 0
        while remainingWire > 2 * np.pi * (r1/100 + numLayers*wireDia/200) *turnsPerLayer:  # determine number of layers
            remainingWire -= 2 * np.pi * (r1/100 + numLayers*wireDia/200) *turnsPerLayer
            N += turnsPerLayer
            numLayers += 1
        if remainingWire > 0:
           N += remainingWire/(2 * np.pi * (r1/100 + (numLayers-1)*wireDia/200))
           remainingWire =0
        r2_inches = wireDia_inches * numLayers + r1_inches
        a = (r1_inches + r2_inches) / 2
        b = length_inches
        c = r2_inches - r1_inches
        L = 0.8 * N * N * a * a / (6 * a + 9 * b + 10 * c)  # calculate final coil inductance
        R = wireLength * wireRes

        return r2_inches * 2.54, N / turnsPerLayer, numLayers, R, resistance/wireRes, N, L

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