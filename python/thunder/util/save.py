"""
Utilities for saving data
"""

import os
from scipy.io import savemat
from math import isnan
from numpy import array, squeeze, sum, shape, reshape, transpose, maximum, minimum, float16, uint8, savetxt, size
from PIL import Image

from thunder.util.load import getdims, subtoind, isrdd


def arraytoim(mat, filename):
    """Write a numpy array to a png image

    If mat is 3D will separately write each image
    along the 3rd dimension

    :param mat: Numpy array, 2d or 3d, dtype must be uint8
    :param filename: Base filename for writing
    """
    dims = shape(mat)
    if len(dims) > 2:
        for z in range(0, dims[2]):
            cdata = mat[:, :, z]
            Image.fromarray(cdata).save(filename+"-"+str(z)+".png")
    elif len(dims) == 2:
        Image.fromarray(mat).save(filename+".png")
    else:
        raise NotImplementedError('array must be 2 or 3 dimensions for image writing')


def rescale(data):
    """Rescale data to lie between 0 and 255 and convert to uint8

    For strictly positive data, subtract the min and divide by max
    otherwise, divide by the maximum absolute value and center

    If each element of data has multiple entries,
    they will be rescaled separately

    :param data: RDD of (Int, Array(Double)) pairs
    """
    data = data.mapValues(lambda x: map(lambda y: 0 if isnan(y) else y, x))
    mnvals = data.map(lambda (_, v): v).reduce(minimum)
    mxvals = data.map(lambda (_, v): v).reduce(maximum)
    if sum(mnvals < 0) == 0:
        data = data.mapValues(lambda x: uint8(255 * (x - mnvals)/(mxvals - mnvals)))
    else:
        mxvals = maximum(abs(mxvals), abs(mnvals))
        data = data.mapValues(lambda x: uint8(255 * ((x / (2 * mxvals)) + 0.5)))
    return data


def save(data, outputdir, outputfile, outputformat):
    """
    Save data to a variety of formats
    Automatically determines whether data is an array
    or an RDD and handles appropriately
    For RDDs, data are sorted and reshaped based on the keys

    :param data: RDD of key value pairs or array
    :param outputdir: Location to save data to
    :param outputfile: file name to save data to
    :param outputformat: format for data ("matlab", "text", or "image")
    """

    filename = os.path.join(outputdir, outputfile)

    if (outputformat == "matlab") | (outputformat == "text"):
        if isrdd(data):
            dims = getdims(data)
            data = subtoind(data, dims.max).sortByKey()
            nout = size(data.first()[1])
            if nout > 1:
                for iout in range(0, nout):
                    result = array(data.map(lambda (_, v): float16(v[iout])).collect())
                    if outputformat == "matlab":
                        savemat(filename+"-"+str(iout)+".mat",
                                mdict={outputfile+str(iout): squeeze(transpose(reshape(result, dims.num[::-1])))},
                                oned_as='column', do_compression='true')
                    if outputformat == "text":
                        savetxt(filename+"-"+str(iout)+".txt", result, fmt="%.6f")
            else:
                result = array(data.map(lambda (_, v): float16(v)).collect())
                if outputformat == "matlab":
                    savemat(filename+".mat", mdict={outputfile: squeeze(transpose(reshape(result, dims.num[::-1])))},
                            oned_as='column', do_compression='true')
                if outputformat == "text":
                    savetxt(filename+".txt", result, fmt="%.6f")

        else:
            if outputformat == "matlab":
                savemat(filename+".mat", mdict={outputfile: data}, oned_as='column', do_compression='true')
            if outputformat == "text":
                savetxt(filename+".txt", data, fmt="%.6f")

    if outputformat == "image":

        if isrdd(data):
            data = rescale(data)
            dims = getdims(data)
            data = subtoind(data, dims.max).sortByKey()
            nout = size(data.first()[1])
            if nout > 1:
                for iout in range(0, nout):
                    result = data.map(lambda (_, v): v[iout]).collect()
                    arraytoim(squeeze(transpose(reshape(result, dims.count[::-1]))), filename+"-"+str(iout))
            else:
                result = data.map(lambda (_, v): v).collect()
                arraytoim(squeeze(transpose(reshape(result, dims.count[::-1]))), filename)
        else:
            arraytoim(data, filename)



