#define PY_SSIZE_T_CLEAN

#include <iostream>
#include <cinttypes>
#include <cstdbool>
#include <cstring>
#include <vector>
#include <tuple>

#include <Python.h>
#include <numpy/arrayobject.h>

static PyObject *petmr_read(PyObject*, PyObject*);

static PyMethodDef petmrMethods[] = {
    {"read", petmr_read, METH_VARARGS, "read PET/MRI insert singles data"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef petmrmodule = {
    PyModuleDef_HEAD_INIT, "petmr", NULL, -1, petmrMethods, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_petmr(void)
{
    import_array();
    return PyModule_Create(&petmrmodule);
}

#define EV_SIZE 16
#define BYTE_IS_HEADER(byte) ((byte) & 0xF8)
#define DATA_FLAG(data) ((data[0] >> 2) & 0x1)
#define DATA_BLK(data) (((data[0] << 4) | (data[1] >> 4)) & 0x3F)
#define DATA_MOD(data) (((data[0] << 2) | (data[1] >> 6)) & 0xF)
#define BLOCK_TO_MODULE(block) ((block) >> 2)
#define CLK_PERIOD_PER_TT 800000ULL

uint64_t reader(FILE *f, uint8_t data[])
{
    if (fread(data, 1, EV_SIZE, f) != EV_SIZE)
        return 0;

    // ensure alignment of data stream
    while (!BYTE_IS_HEADER(data[0]))
    {
        size_t n = EV_SIZE;
        for (size_t i = 1; i < EV_SIZE; i++)
        {
            if (BYTE_IS_HEADER(data[i]))
            {
                std::cout << "Realign data stream\n";
                std::memmove(data, data + i, EV_SIZE - i);
                n = i;
                break;
            }
        }

        if (fread(data + (EV_SIZE - n), 1, n, f) != n)
            return 0;
    }

    return ftello(f);
}

static PyObject *
petmr_read(PyObject *self, PyObject *args)
{
    // parse arguments from python
    int find_rst = 1;
    const char *fname;
    if (!PyArg_ParseTuple(args, "s|p", &fname, &find_rst))
        return NULL;

    // Open file and determine length
    std::cout << "Reading file " << fname << "\n";
    FILE *file = fopen(fname, "rb");
    if (!file) 
    {
        PyErr_SetFromErrno(PyExc_IOError);
        return NULL;
    }
    else
    {
        uint64_t file_length, file_elems;
        fseek(file, 0L, SEEK_END);
        file_length = ftell(file);
        rewind(file);

        file_elems = file_length / EV_SIZE;
        std::cout << "Found " << std::to_string(file_elems) << " entries\n";
    } 

    uint64_t offset = 0;
    uint8_t data[EV_SIZE] = {0};

    // Scan for reset time tag
    while (find_rst && (offset = reader(file, data)))
    {
        if (!DATA_FLAG(data))
        {
            uint64_t upper = (data[10] << 16) | (data[11] << 8) | data[12];
            uint64_t lower = (data[13] << 16) | (data[14] << 8) | data[15];
            uint64_t tt = (upper << 24) | lower;
            if (tt == 0)
            {
                std::cout << "Found reset after " << std::to_string(offset / EV_SIZE) << " entries\n";
                break;
            }
        }
    }
    
    // Single event
    // CRC | f |    b   |   E1   |    E2   |   E3    |   E4   |   E5    |   E6   |   E7    |   E8   |       TT
    // { 5 , 1 , 2 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }
    //       0          1      2    3      4      5    6      7      8    9     10     11   12     13     14   15
    
    // Time tag
    // CRC | f |    b   |                     0's                    |             TT
    // { 5 , 1 , 2 }{ 4 , 4 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }
    //       0          1      2    3    4    5    6    7    8    9   10   11   12   13   14   15

    std::vector<std::vector<uint16_t>> energies (8, std::vector<uint16_t>{});
    std::vector<uint8_t> blk;
    std::vector<uint64_t> TT;

    // read file contents
    uint64_t last_tt[16] = {0};
    npy_intp n = 0;
    while ((offset = reader(file, data)))
    {
        int mod = DATA_MOD(data);

        if (DATA_FLAG(data))
        {
            n++;
            // Front energies
            energies[0].push_back(((data[1] << 8) | data[2]) & 0xFFF); // A
            energies[1].push_back((data[3] << 4) | (data[4] >> 4)); // B
            energies[2].push_back(((data[4] << 8) | data[5]) & 0xFFF); // C
            energies[3].push_back((data[6] << 4) | (data[7] >> 4)); // D

            // Rear energies
            energies[4].push_back(((data[7] << 8) | data[8]) & 0xFFF); // E
            energies[5].push_back((data[9] << 4) | (data[10] >> 4)); // F
            energies[6].push_back(((data[10] << 8) | data[11]) & 0xFFF); // G
            energies[7].push_back((data[12] << 4) | (data[13] >> 4)); // H

            blk.push_back(DATA_BLK(data));

            uint64_t time = ((data[13] << 16) | (data[14] << 8) | data[15]) & 0xFFFFF;
            TT.push_back(last_tt[mod] * CLK_PERIOD_PER_TT + time);
        }
        else
        {
            uint64_t upper = (data[10] << 16) | (data[11] << 8) | data[12];
            uint64_t lower = (data[13] << 16) | (data[14] << 8) | data[15];
            last_tt[mod] = (upper << 24) | lower;
        }
    }

    // clean up and return data as numpy array
    fclose(file);

    PyObject *lst = PyList_New(energies.size() + 2);
    PyObject *arr = NULL;

    if (!lst) goto cleanup;

    arr = PyArray_SimpleNew(1, &n, NPY_UINT8);
    if (!arr) goto cleanup;
    std::memcpy(PyArray_DATA(arr), blk.data(), n*sizeof(uint8_t));
    PyList_SetItem(lst, 0, arr);

    arr = PyArray_SimpleNew(1, &n, NPY_UINT64);
    if (!arr) goto cleanup;
    std::memcpy(PyArray_DATA(arr), TT.data(), n*sizeof(uint64_t));
    PyList_SetItem(lst, 1, arr);

    for (size_t i = 0; i < energies.size(); i++)
    {
        arr = PyArray_SimpleNew(1, &n, NPY_UINT16);
        if (!arr) goto cleanup;
        std::memcpy(PyArray_DATA(arr), energies[i].data(), n*sizeof(uint16_t));
        PyList_SetItem(lst, 2 + i, arr);
    }

    return lst;

cleanup:
    for (size_t i = 0; lst && (i < energies.size() + 1); i++)
        Py_XDECREF(PyList_GetItem(lst, i));
    Py_XDECREF(arr);
    Py_XDECREF(lst);
    PyErr_SetString(PyExc_Exception, "Failed to create numpy array");
    return NULL;
}
