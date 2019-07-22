from matplotlib import pyplot as plt
# import multiprocessing
import numpy as np
# from pathos.multiprocessing import ProcessingPool as Pool

from scipy.optimize import root, fsolve
from mpl_toolkits.mplot3d import Axes3D

# cores = multiprocessing.cpu_count()

D = 0.2  # meter
L, B = 0.5, 0.5

xRange = 0.305 * 2  # meter
yRange = 0.23 * 2  # meter
zUpperBound = D * 1.2 + 0.5  # meter
zLowerBound = D * 0.2

precision = 0.004  # meter
gravity = 9.8  # m/s^2
waterDensity = 997  # kg/m^3
hullDensity = 110  # kg/m^3
boatThick = 1e-2  # meter

hullMeshDensity = hullDensity * np.power(precision, 3)
waterMeshDensity = waterDensity * np.power(precision, 3)


def axis2MeshPositionZ(axis):
    return list(map(int, (np.array(axis) + zLowerBound) / precision))


class ballast():
    weight = 0.6  # kg
    axisPosition = np.array([0, 0, 0])  # meter
    meshPosition = axis2MeshPositionZ(axisPosition)
    axisShape = np.array([0.06, 0.025, 0.025])  # meter
    meshShape = list(map(int, axisShape / precision))
    meshVolume = meshShape[0] * meshShape[1] * meshShape[2]
    meshDensity = weight / meshVolume


ballast1 = ballast()

MidIndexX = int(xRange / precision + 1)
MidIndexY = int(yRange / precision + 1)
MidIndexZ = int(zLowerBound / precision + 1)

maxZIndex = int((D + zLowerBound) / precision)

xLen = int(2 * xRange / precision + 1)
yLen = int(2 * yRange / precision + 1)
zLen = int((zLowerBound + zUpperBound) / precision + 1)

xArray = np.linspace(-xRange, xRange, xLen)
yArray = np.linspace(-yRange, yRange, yLen)

xGrid, yGrid = np.meshgrid(xArray, yArray)
zGrid = D * (np.power(2 * xGrid / L, 4) + np.power(2 * yGrid / B, 2))

hullMesh = np.zeros((xLen, yLen, zLen))

minZIndexMat = ((np.transpose(zGrid) + zLowerBound) / precision).astype(np.int)

for i in range(xLen):
    for j in range(yLen):
        # minZIndex = int((zGrid[j, i] + zLowerBound) / precision)
        hullMesh[i, j, minZIndexMat[i, j]:maxZIndex] = 1
        # hullMesh[i, j, minZIndex:minZIndex + int(boatThick / precision)] = 1
        # hullMesh[i, j, maxZIndex - int(boatThick / precision):maxZIndex] = 1


def caculWeight(weightMat):
    M = np.sum(weightMat)
    return M


def calculCOM(weightMat):
    M = caculWeight(weightMat)
    xCOMPre = np.linspace(1, xLen, xLen).dot(np.sum(weightMat, axis=(2, 1)))
    yCOMPre = np.linspace(1, yLen, yLen).dot(np.sum(weightMat, axis=(0, 2)))
    zCOMPre = np.linspace(1, zLen, zLen).dot(np.sum(weightMat, axis=(1, 0)))
    xCOM, yCOM, zCOM = [xCOMPre, yCOMPre, zCOMPre] / M
    return np.array([xCOM, yCOM, zCOM]).astype(np.int)


def addBallast(weightMat, ballast1):
    xCOM, yCOM, zCOM = calculCOM(weightMat)
    shape = ballast1.meshShape
    weightMat[int(xCOM - shape[0] / 2):int(xCOM + shape[0] / 2 + 1),
              int(yCOM - shape[1] / 2):int(yCOM + shape[1] / 2 + 1),
              int(MidIndexZ):int(MidIndexZ + shape[2]) + 1] += ballast1.meshDensity
    return weightMat


hullMesh = hullMeshDensity * hullMesh

hullWeight = caculWeight(hullMesh)

xCOM, yCOM, zCOM = calculCOM(hullMesh)
print([xCOM, yCOM, zCOM])

hullMesh = addBallast(hullMesh, ballast1)


def addMast(weightMat):
    DiaMeter = 9.5e-3  # meter
    Radius = DiaMeter / 2  # meter
    RadiusMesh = int(Radius / precision)
    Length = 0.5  # meter
    Weight = 96.7e-3  # kg
    Volume = np.pi * Radius * Radius * Length
    Density = Weight / Volume
    DensityMesh = Density * np.power(precision, 3)

    xCOM, yCOM, zCOM = calculCOM(weightMat)

    iArray = np.linspace(- RadiusMesh, RadiusMesh, 2 *
                         RadiusMesh + 1).astype(np.int)
    jRadius = np.sqrt(RadiusMesh * RadiusMesh - iArray * iArray).astype(np.int)
    for i in range(iArray.shape[0]):
        weightMat[iArray[i] +
                  xCOM, yCOM -
                  jRadius[i]:yCOM +
                  jRadius[i], int(zLowerBound /
                                  precision):int((zLowerBound +
                                                  Length) /
                                                 precision)] = DensityMesh

    return weightMat


hullMesh = addMast(hullMesh)

xCOM, yCOM, zCOM = calculCOM(hullMesh)
print([xCOM, yCOM, zCOM], '\n')

hullWeight = caculWeight(hullMesh)

DisplacementVolumeReal = hullWeight / waterDensity
DisplacementVolumeMesh = DisplacementVolumeReal / pow(precision, 3)


def fliTrans(mat):
    return np.flipud(mat.transpose())


def calculDisplacementVolumeMesh(
        hullMesh,
        waterAngle,
        waterOffset,
        isFinal,
        needInverse):
    noWaterMesh = np.ones(
        [hullMesh.shape[0], hullMesh.shape[1], hullMesh.shape[2]])
    waterLineMesh = np.zeros(
        [hullMesh.shape[0], hullMesh.shape[1], hullMesh.shape[2]])

    rightXYArray = ((np.tan(waterAngle) *
                     (np.arange(yLen) *
                      precision -
                      xRange) +
                     yRange) /
                    precision +
                    waterOffset).astype(np.int)

    if needInverse:
        for i in range(yLen):
            rightXY = rightXYArray[i]
            noWaterMesh[:, i, rightXY:] = 0
    else:
        for i in range(yLen):
            rightXY = rightXYArray[i]
            noWaterMesh[:, i, :rightXY] = 0

    unSubmergedMesh = np.logical_and(noWaterMesh, hullMesh) * hullMesh
    DisplacedWaterWeight = np.sum(
        np.logical_and(
            np.logical_not(noWaterMesh),
            hullMesh)) * waterMeshDensity
    DisplacementVolume = np.sum(np.logical_and(
        np.logical_not(noWaterMesh), hullMesh)) * np.power(precision, 3)
    SubmergedVolume = np.sum(np.logical_and(
        np.logical_not(noWaterMesh),
        hullMesh)) * np.power(precision, 3)
    SubmergedMesh = np.logical_and(
        np.logical_not(noWaterMesh),
        hullMesh) * hullMesh

    if isFinal:
        print('\nSubmergedVolume: ', SubmergedVolume)
        print('Weight of Displaced Water: ', DisplacementVolume * waterDensity)
        print('Weight of Boat: ', hullWeight)

    return [
        unSubmergedMesh,
        SubmergedMesh,
        waterLineMesh,
        DisplacedWaterWeight]


def calculBestWaterOffsetMesh(hullMesh, waterAngle, hullWeight):
    lastLoss = - np.sum(hullMesh)
    maxIteration = 5000
    waterOffsetLowerBound = - 2 * zLen
    waterOffsetUpperBound = 3 * zLen
    waterOffset = int((waterOffsetLowerBound + waterOffsetUpperBound) / 2)

    if (waterAngle >= 0 and waterAngle < np.pi /
            2) or (waterAngle >= 1.5 * np.pi and waterAngle < 2 * np.pi):
        needInverse = 0
    else:
        needInverse = 1

    for i in range(maxIteration):
        print('Processed: ' + str((i + 1) / maxIteration * 100) +
              '%' + '     Loss: ' + str(lastLoss))
        unSubmergedMesh, SubmergedMesh, waterLineMesh, DisplacedWaterWeight = calculDisplacementVolumeMesh(
            hullMesh, waterAngle, waterOffset, False, needInverse)
        thisLoss = DisplacedWaterWeight - hullWeight

        if i >= maxIteration - \
                1 or abs(thisLoss / hullWeight * 100) < 1 or waterOffsetLowerBound >= waterOffsetUpperBound:
            unSubmergedMesh, SubmergedMesh, waterLineMesh, DisplacedWaterWeight = calculDisplacementVolumeMesh(
                hullMesh, waterAngle, waterOffset, True, needInverse)
            thisLoss = DisplacedWaterWeight - hullWeight
            print(
                '\nDone \nLoss= ',
                thisLoss /
                hullWeight *
                100,
                '%',
                '\nOffset = ',
                waterOffset)
            pass
            return [
                waterOffset,
                unSubmergedMesh,
                SubmergedMesh,
                waterLineMesh,
                thisLoss,
                thisLoss /
                np.sum(hullMesh)]
        else:
            if thisLoss < 0 and not(needInverse):
                waterOffsetLowerBound = waterOffset
                waterOffset = int((waterOffset + waterOffsetUpperBound) / 2)
            elif thisLoss < 0 and needInverse:
                waterOffsetUpperBound = waterOffset
                waterOffset = int((waterOffset + waterOffsetLowerBound) / 2)
            elif thisLoss > 0 and not(needInverse):
                waterOffsetUpperBound = waterOffset
                waterOffset = int((waterOffset + waterOffsetLowerBound) / 2)
            else:
                waterOffsetLowerBound = waterOffset
                waterOffset = int((waterOffset + waterOffsetUpperBound) / 2)
            lastLoss = thisLoss


degreeAngle = 30  # degree

waterAngle = np.deg2rad(degreeAngle)

waterOffset, unSubmergedMesh, SubmergedMesh, waterLineMesh, Loss, lossPercent = calculBestWaterOffsetMesh(
    hullMesh, waterAngle, hullWeight)

[xCOB, yCOB, zCOB] = map(int, calculCOM(SubmergedMesh))

FBuoyancy = FGravity = hullWeight * gravity

buoyancyTorqueVector = np.cross([(yCOB - yCOM) * precision,
                                 (zCOB - zCOM) * precision,
                                 0],
                                [-FBuoyancy * np.sin(waterAngle),
                                 FBuoyancy * np.cos(waterAngle), 0])

buoyancyTorque = -buoyancyTorqueVector[2]

print(
    '\nBuoyancy Torque under ',
    degreeAngle,
    ' degrees: ',
    buoyancyTorque,
    ' N * M\n')

print('COM: ', [xCOM, yCOM, zLen - zCOM])
print('COB: ', [xCOB, yCOB, zLen - zCOB])

if(buoyancyTorque > 0):
    print('\nIt can recover\n')

plt.figure(1)
# plt.matshow(fliTrans(hullMesh[MidIndexX, :, :]))
plt.matshow(fliTrans(SubmergedMesh[MidIndexX, :, :] > 0))
plt.title('Submerged_yz ' + str(degreeAngle))
plt.show()

plt.figure(2)
# plt.matshow(fliTrans(hullMesh[MidIndexX, :, :]))
plt.matshow(fliTrans(hullMesh[MidIndexX, :, :] > 0))
plt.title('yz ' + str(degreeAngle))
plt.show()

plt.figure(3)
plt.matshow(fliTrans(hullMesh[:, MidIndexY, :] > 0))
plt.title('xz')
plt.show()

plt.figure(4)
plt.matshow(fliTrans(hullMesh[:, :, MidIndexZ] > 0))
plt.title('xy')
plt.show()

# fig1 = plt.figure(1)
# ax = Axes3D(fig1)
#
# ax.plot_surface(
#     xGrid,
#     yGrid,
#     zGrid,
#     rstride=1,
#     cstride=1,
#     cmap='rainbow')
# # ax.plot_surface(xGrid, yGrid, DPlane, rstride=1, cstride=1, cmap='rainbow')
#
# plt.show()

pass
