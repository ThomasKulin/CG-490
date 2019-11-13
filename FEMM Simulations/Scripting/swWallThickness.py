import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import datetime
import os

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swWallThickness"
pos_start = -2
pos_stop = 14
pos_step = 1
dia_start = 0.635  # 1/4" is diameter of projectile (0 wall thickness)
dia_stop = 1.4
dia_step = 0.1

# set up FEMM stuff
femm.openfemm()
femm.opendocument('..\\'+filename + ".fem")
femm.mi_saveas('..\\'+"temp.fem")
femm.mi_seteditmode("group")

# set up data capture
DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
dataDir = '..\\'+'Data\\WallThickness ' + DateTime
os.makedirs(dataDir)
workbook = xl.Workbook(dataDir + '\\' + filename + ".xlsx")
worksheet = workbook.add_worksheet()
worksheet.write(0, 0, 'Position [cm]')

# Calculate required iterations
pos_iter = int((pos_stop-pos_start)/pos_step)
dia_iter = int((dia_stop - dia_start) / dia_step)

z = [[0 for n in range(pos_iter)] for i in range(dia_iter)]
f = [[0 for n in range(pos_iter)] for i in range(dia_iter)]
for i in range(dia_iter):
    print("Thickness Iteration: " + str(i))
    worksheet.write(0, i + 1, str(dia_start + i * dia_step) + ' cm Force [N]')

    for n in range(pos_iter):
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

        print("Position Iteration: " + str(n) + '\tz = ' + str(
            round(z[i][n], 6)) + '\tf = ' + str(round(f[i][n], 6)))

    # move projectile back to start
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, - pos_iter * pos_step)

    # move coil horizontally to increase diameter (ignores changes to inductance and resistance and assumes a constant current)
    femm.mi_selectgroup(2)
    femm.mi_movetranslate(dia_step/2, 0)

femm.closefemm()
workbook.close()