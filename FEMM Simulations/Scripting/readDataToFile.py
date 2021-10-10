import numpy as np
import xlsxwriter as xl

def main():

    dataDir = r"D:\Users\Thomas\Documents\Projects\CG-490\FEMM Simulations\Data\TimeRLSweep 2020_01_30 12_34 (first stage L update)"

    # Set up Excel
    workbook = xl.Workbook(dataDir + "\\dataAnalysis.xlsx")

    # Load Data
    z = np.load(dataDir + '\\z.npy')
    f = np.load(dataDir + '\\f.npy')
    a = np.load(dataDir + '\\a.npy')
    v = np.load(dataDir + '\\v.npy')
    I = np.load(dataDir + '\\I.npy')
    var = np.load(dataDir + '\\var.npy')

    for i in range(len(var)):
        worksheet = initializeSheet(workbook, str(var[i]))




def initializeSheet(workbook, name):
    worksheet = workbook.add_worksheet(name=name)
    worksheet.write(0, 0, 'Time [s]')
    worksheet.write(0, 1, 'Stage #')
    worksheet.write(0, 2, 'Position wrt. Stage [cm]')
    worksheet.write(0, 3, 'Position [cm]')
    worksheet.write(0, 4, 'Velocity [m/s]')
    worksheet.write(0, 5, 'Acceleration [m/s^2]')
    worksheet.write(0, 6, 'Force [N]')
    worksheet.write(0, 7, 'Current [A]')
    return worksheet


if __name__ == "__main__":
    main()