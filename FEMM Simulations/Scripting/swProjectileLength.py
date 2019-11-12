import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl
import datetime
import os

# TEST PARAMS --- Units in cm
filename = "7mmCoil_192T_156A_swProjectileLength"
pos_start = -2
pos_stop = 14
pos_step = 1
len_start = 1
len_stop = 14
len_step = 1

# set up FEMM stuff
femm.openfemm()
femm.opendocument(filename + ".fem")
femm.mi_saveas("temp.fem")
femm.mi_seteditmode("group")

# set up data capture
DateTime = datetime.datetime.now().strftime("%Y_%m_%d %H_%M").replace('.', '-')
dataDir = 'Data\\ProjectileLength ' + DateTime
os.makedirs(dataDir)
workbook = xl.Workbook(dataDir + '\\' + filename + ".xlsx")
worksheet = workbook.add_worksheet()
worksheet.write(0, 0, 'Position [cm]')

# Calculate required iterations
pos_iter = int((pos_stop-pos_start)/pos_step)
len_iter = int((len_stop-len_start)/len_step)

z = [[0 for n in range(pos_iter)] for i in range(len_iter)]
f = [[0 for n in range(pos_iter)] for i in range(len_iter)]
for i in range(len_iter):
    print("Length Iteration: " + str(i))
    worksheet.write(0, i+1, str(len_start + i*len_step) + ' cm Force [N]')

    for n in range(pos_iter):
        print("Position Iteration: " + str(n))
        femm.mi_analyze()
        femm.mi_loadsolution()
        femm.mo_groupselectblock(9)  # select group 9 (coil)
        fz = -femm.mo_blockintegral(19)  # calculate force applied to coil (assumes force on projectile is equal and opposite)
        z[i][n] = pos_start + n*pos_step
        f[i][n] = fz

        # data capture out
        worksheet.write(n+1, 0, z[i][n])
        worksheet.write(n+1, i + 1, f[i][n])

        # move projectile forward by pos_step cm
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(0, pos_step)
        femm.mi_selectgroup(3)
        femm.mi_movetranslate(0, pos_step)
        femm.mi_selectgroup(2)
        femm.mi_movetranslate(0, pos_step)

    # move projectile back to start and increment projectile length
    femm.mi_selectgroup(2)
    femm.mi_movetranslate(0, - pos_iter*pos_step - len_step)
    femm.mi_selectgroup(3)
    femm.mi_movetranslate(0, - pos_iter * pos_step)
    femm.mi_selectgroup(1)
    femm.mi_movetranslate(0, - pos_iter*pos_step)

femm.closefemm()
workbook.close()