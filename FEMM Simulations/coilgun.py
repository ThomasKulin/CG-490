import femm
import matplotlib.pyplot as plt
import xlsxwriter as xl

#TEST PARAMS
filename = "3.2mmCoil_100T_165A"
iter = 100
step = 0.1

femm.openfemm()
femm.opendocument(filename + ".fem")
femm.mi_saveas("temp.fem")
femm.mi_seteditmode("group")

z=[]
f=[]
for n in range(0, iter):
	print("Iteration: " + str(n))
	femm.mi_analyze()
	femm.mi_loadsolution()
	femm.mo_groupselectblock(1)
	fz=femm.mo_blockintegral(19)
	z.append(n*step)
	f.append(fz)
	femm.mi_selectgroup(1)
	femm.mi_movetranslate(0, step)
femm.closefemm()

# Plot Data
plt.plot(z,f)
plt.ylabel('Force, N')
plt.xlabel('Offset, cm')
plt.show()

# Save Data to Excel
z.insert(0, 'Position [cm]')
f.insert(0, 'Force [N]')
workbook = xl.Workbook(filename + ".xlsx")
worksheet = workbook.add_worksheet()
for row in range(0, iter):
	worksheet.write(row, 0, z[row])
	worksheet.write(row, 1, f[row])
workbook.close()