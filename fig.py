# importing the necessary libraries
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt
import numpy as np
# Creating random dataset
# z = 4 * np.tan(np.random.randint(10, size =(500))) + np.random.randint(100, size =(500))
# x = 4 * np.cos(z) + np.random.normal(size = 500)
# y = 4 * np.sin(z) + 4 * np.random.normal(size = 500)

z = [1,0,4]
x = [2,4,4]
y = [5,8,4]
# Creating figure
fig = plt.figure(figsize = (16, 12))
ax = plt.axes(projection ="3d")
# Add x, and y gridlines for the figure
ax.grid(b = True, color ='blue',linestyle ='-.', linewidth = 0.5,alpha = 0.3)
# Creating the color map for the plot
my_cmap = plt.get_cmap('hsv')
# Creating the 3D plot
sctt = ax.scatter3D(x, y, z,alpha = 0.8,marker ='^')
plt.title("3D scatter plot in Python")
ax.set_xlabel('X-axis', fontweight ='bold')
ax.set_ylabel('Y-axis', fontweight ='bold')
ax.set_zlabel('Z-axis', fontweight ='bold')
fig.colorbar(sctt, ax = ax, shrink = 0.6, aspect = 5)
# display the plot
plt.show()