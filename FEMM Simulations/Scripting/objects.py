import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import numpy as np
import math
from tempfile import mkstemp
from shutil import move
from subprocess import call

import ltspice
import matplotlib.pyplot as plt
import numpy as np
import os


class Coil:
    def __init__(self, nodes, groups=[10, 11, 12, 13], name='Coil', propGroup=15):
        #            N: 10 (r, z), N 11,     N 12,        N 13
        self.nodes = nodes
        self.groups = groups
        self.name = name
        self.propGroup = propGroup
        self.exactLayers = None
        self.numLayers = None
        self.wireLength = None
        self.numTurns = None
        self.resistance = None
        self.inductance = None
        self.triggerPosition = -0.5

    def getLength(self):
        return self.nodes[0][1] - self.nodes[3][1]

    def getIR(self):
        return self.nodes[0][0]

    def getOR(self):
        return self.nodes[1][1]

    def getTriggerPosition(self):
        return self.nodes[3][1]+self.triggerPosition

    def setDimensions(self, rInner, rOuter, len):
        if self.nodes[3][0] <= rInner:
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
        else:
            femm.mi_selectgroup(10)
            femm.mi_movetranslate(rInner - self.nodes[0][0], len - (self.nodes[0][1] - self.nodes[3][1]))
            self.nodes[0][0] = rInner
            self.nodes[0][1] = len + self.nodes[3][1]
            femm.mi_selectgroup(13)
            femm.mi_movetranslate(rInner - self.nodes[3][0], 0)
            femm.mi_selectgroup(15)  # block label
            femm.mi_movetranslate(rInner - self.nodes[3][0], 0)
            self.nodes[3][0] = rInner
            femm.mi_selectgroup(11)
            femm.mi_movetranslate(rOuter - self.nodes[1][0], len - (self.nodes[1][1] - self.nodes[2][1]))
            self.nodes[1][0] = rOuter
            self.nodes[1][1] = len + self.nodes[2][1]
            femm.mi_selectgroup(12)
            femm.mi_movetranslate(rOuter - self.nodes[2][0], 0)
            self.nodes[2][0] = rOuter

    def setCoilCurrent(self, current):
        femm.mi_setcurrent(self.name, current)
        femm.mi_selectgroup(self.propGroup)
        femm.mi_setblockprop('18 AWG', 1, 0, self.name, 0, 15, self.numTurns)
        femm.mi_movetranslate(0, 0)  # solves a bug where group 15 doesn't deselect until a movetranslate

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
                self.exactLayers = N / turnsPerLayer
                self.numLayers = numLayers
                self.wireLength = wireLength
                self.numTurns = N
                self.resistance = wireResistance
                self.inductance = L
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
        self.exactLayers = N / turnsPerLayer
        self.numLayers = numLayers
        self.wireLength = wireLength
        self.numTurns = N
        self.resistance = R
        self.inductance = L
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

    def getMass(self):
        D = 8050  # [Kg/m^3]
        V = np.pi * (self.getRadius()/100)**2 * self.getLength()/100  # [m^3]
        return D*V

    def setDimensions(self, rad, len):
        z_correction = len-self.getLength()
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(0, 0)
        femm.mi_selectgroup(2)
        femm.mi_movetranslate(rad - self.nodes[1][0], 0)
        self.nodes[1][0] = rad
        femm.mi_selectgroup(3)
        femm.mi_movetranslate(rad - self.nodes[2][0], -z_correction)
        self.nodes[2][0] = rad
        self.nodes[2][1] -= z_correction
        femm.mi_selectgroup(4)
        femm.mi_movetranslate(0, -z_correction)
        self.nodes[3][1] -= z_correction

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

    def setPosition(self, z):
        z_pos = self.nodes[0][1]
        z_correction = z - z_pos
        self.moveZ(z_correction)

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


class LTSpice:
    def __init__(self, asc_filepath, raw_filepath, exe_path):
        self.asc_filepath = asc_filepath  # circuit definition file
        self.raw_filepath = raw_filepath  # simulation output file
        self.exe_path = exe_path  # path to LT Spice exe
        self.data = None

    def set_param(self, param, param_val, overwrite=True):
        f, abs_path = mkstemp()
        with open(abs_path, 'w') as new_file:
            with open(self.asc_filepath) as old_file:
                for line in old_file:
                    line_list = line.split(' ')
                    if line_list[0] == 'TEXT':
                        for element_num, element in enumerate(line_list):
                            if element.split('=')[0] == param:
                                line_list[element_num] = param + '=' + str(param_val)
                        if line_list[-1][-1] != '\n':
                            line_list[-1] = line_list[-1] + '\n'
                        new_file.write(' '.join(line_list))
                    else:
                        new_file.write(line)
        os.close(f)
        if overwrite:
            os.remove(self.asc_filepath)
            move(abs_path, self.asc_filepath)
        else:
            move(abs_path, self.asc_filepath[:-4] + '_generated.asc')

    def simulate(self):
        # run SPICE simulation
        file_path = self.asc_filepath[:-4]  # Use .asc file, but remove file ending
        file_name = str(file_path.split('\\')[-1])
        print('Simulation starting: ' + file_name + '.asc')
        call('"' + self.exe_path + '" -netlist "' + file_path + '.asc"')
        call('"' + self.exe_path + '" -b "' + file_path + '.net"')
        size = os.path.getsize(file_path + '.raw')
        print('Simulation finished: ' + file_name + '.raw created (' + str(size / 1000) + ' kB)')

        # get SPICE simulation output
        self.data = ltspice.Ltspice('SPICE Dependencies\\offTime.raw')
        # Make sure that the .raw file is located in the correct path
        self.data.parse()

    def getTime(self):
        return self.data.getTime()

    def getNearestTime(self, time):
        return min(self.data.getTime(), key=lambda x: abs(x - time))

    def getData(self, param):
        return self.data.getData(param)