#include <iostream>
#include <vector>
#include <future>
#include <thread>
#include <queue>

#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#include <singles.h>

#include <Python.h>

static PyObject *acq_run(PyObject*, PyObject*);

static PyMethodDef acqMethods[] = {
    {"run", acq_run, METH_VARARGS, "Run an acquisition"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef acqmodule = {
    PyModuleDef_HEAD_INIT, "acq", NULL, -1, acqMethods, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_acq(void)
{
    return PyModule_Create(&acqmodule);
}

void process(std::atomic_bool &stop,

             std::mutex &acq_mux,
             std::queue<std::vector<uint8_t>> &acq_data,
             std::condition_variable_any &acq_cv,

             std::atomic_uint64_t &current_tt,
             std::atomic_uint64_t &next_tt)
{
    std::vector<uint8_t> current_data;

    while (!stop)
    {
        std::unique_lock<std::mutex> lck(acq_mux);
        acq_cv.wait(lck, [&]{ return !acq_data.empty(); });
        current_data = acq_data.front();
        acq_data.pop();
    }
}

void acq(std::string ip,
         uint16_t port,
         std::atomic_bool &stop,
         std::mutex &mux,
         std::queue<std::vector<uint8_t>> &data,
         std::condition_variable_any &cv)
{
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);

    if (inet_pton(AF_INET, ip.c_str(), &addr.sin_addr) < 0)
    {
        return;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);

    struct timeval to;
    to.tv_sec = 1;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &to, sizeof(to));

    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0)
    {
        // failed to connect
        std::cout << "failed to connect" << std::endl;
        return;
    }

    int sz = 4096, n = 0;
    std::vector<uint8_t> buf (sz);

    while (!stop)
    {
        int ret = recv(sock, buf.data() + n, sz - n, 0);

        if (ret < 0)
        {
            if (errno == EAGAIN)
            {
                std::cout << "timeout" << std::endl;
                continue;
            }
            else break;
        }
        
        n += ret;

        if (n == sz)
        {
            n = 0;
            {
                std::unique_lock<std::mutex> lck(mux);
                data.push(buf);
            }
            cv.notify_all();
        }
    }

    // provide final data at finish

    {
        std::unique_lock<std::mutex> lck(mux);
        data.push(std::vector<uint8_t>());
    }
    cv.notify_all();
}

/*
 * Helpers to load and store data
 */

char *py_to_str(PyObject *obj)
{
    if (!PyUnicode_Check(obj))
    {
        PyErr_SetString(PyExc_ValueError, "Object is not a unicode string");
        return NULL;
    }
    PyObject *utf8 = PyUnicode_AsUTF8String(obj);
    return PyBytes_AsString(utf8);
}

std::vector<std::string>
pylist_to_strings(PyObject *lst)
{
    std::vector<std::string> clst;
    int nfiles = PyList_Size(lst);
    for (int i = 0; i < nfiles; i++)
    {
        PyObject *item = PyList_GetItem(lst, i);
        clst.emplace_back(py_to_str(item));
    }
    return clst;
}

/*
 * Top level function, called from python
 */

static PyObject *
acq_run(PyObject *self, PyObject *args)
{
    PyObject *terminate, *py_ip_list;
    if (!PyArg_ParseTuple(args, "OO", &terminate,
                                       &py_ip_list)) return NULL;

    // Parse the input files
    auto ip_list = pylist_to_strings(py_ip_list);
    if (PyErr_Occurred()) return NULL;

    uint16_t port_num = 5555;
    std::atomic_bool stop = false;

    std::vector<std::future<void>> acq_thread;
    for (auto ip : ip_list)
        acq_thread.push_back(std::async(std::launch::async,
                    &acq, ip, port_num, std::ref(stop)));

    std::this_thread::sleep_for(std::chrono::seconds(10));

    stop = true;
    for (auto &fut : acq_thread)
        fut.get();

    Py_RETURN_NONE;
}
