import datetime
import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import os

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swIronThickness"
pos_start = -2
pos_stop = 14
pos_step = 1
iron_start = 0.1
iron_stop = 2
iron_step = 0.2

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
iron_iter = int((iron_stop - iron_start) / iron_step) + 1

z = [[0 for n in range(pos_iter)] for i in range(iron_iter)]
f = [[0 for n in range(pos_iter)] for i in range(iron_iter)]
for i in range(iron_iter):
    print("Iron Iteration: " + str(i))
    worksheet.write(0, i + 1, str(round((iron_start + i * iron_step)*10)) + ' mm Force [N]')

    for n in range(pos_iter):
        print("Position Iteration: " + str(n))
        femm.mi_analyze()
        femm.mi_loadsolution()
        femm.mo_groupselectblock(1)  # select group 1 (projectile)
        fz = femm.mo_blockintegral(19)  # calculate force applied to projectile
        z[i][n] = pos_start + n*pos_step
        f[i][n] = fz

        # data capture out
        worksheet.write(n+1, 0, z[i][n])
        worksheet.write(n+1, i + 1, f[i][n])

        # move projectile forward by pos_step cm
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(0, pos_step)

    # move projectile back to start
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, - pos_iter*pos_step)

    # # step iron washer thickness
    # femm.mi_selectgroup(5)
    # femm.mi_movetranslate(0, iron_step)
    # femm.mi_selectgroup(6)
    # femm.mi_movetranslate(0, iron_step)
    # femm.mi_selectgroup(7)
    # femm.mi_movetranslate(0, -iron_step)
    # femm.mi_selectgroup(8)
    # femm.mi_movetranslate(0,  -iron_step)

    # # step iron wrap thickness
    # femm.mi_selectgroup(6)
    # femm.mi_movetranslate(iron_step, 0)
    # femm.mi_selectgroup(7)
    # femm.mi_movetranslate(iron_step, 0)
    #
    # step washer and wrap thickness
    femm.mi_selectgroup(5)
    femm.mi_movetranslate(0, iron_step)
    femm.mi_selectgroup(6)
    femm.mi_movetranslate(iron_step, iron_step)
    femm.mi_selectgroup(7)
    femm.mi_movetranslate(iron_step, -iron_step)
    femm.mi_selectgroup(8)
    femm.mi_movetranslate(0, -iron_step)

femm.closefemm()
workbook.close()