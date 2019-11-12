import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter

def main():
    dataDir = 'Data\\DimensionSweep 2019_11_03 15_24'

    z = np.load(dataDir + '\\z.npy')
    f = np.load(dataDir + '\\f.npy')
    w = np.load(dataDir + '\\w.npy')
    v = np.load(dataDir + '\\v.npy')
    len_iter = np.load(dataDir + '\\len.npy')
    rad_iter = np.load(dataDir + '\\rad.npy')

    plotSurf(len_iter, rad_iter, w, v)


def plotSurf(X, Y, Z1, Z2):
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    X, Y = np.meshgrid(X, Y)
    # Plot the surface.
    surf = ax.plot_surface(X, Y, Z1, cmap=cm.coolwarm, linewidth=0, antialiased=False)
    surf = ax.plot_surface(X, Y, Z2, cmap=cm.YlOrRd, linewidth=0, antialiased=False)
    # Customize the z axis.
    # ax.set_zlim(0, 5)
    # ax.zaxis.set_major_locator(LinearLocator(10))
    # ax.zaxis.set_major_formatter(FormatStrFormatter('%.02f'))
    # Add a color bar which maps values to colors.
    fig.colorbar(surf, shrink=0.5, aspect=5)
    plt.show()

if __name__ == '__main__':
    main()