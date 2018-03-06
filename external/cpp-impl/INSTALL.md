In most cases, you should be find by simply using system libraries when compiling. Otherwise, you must configure the following variables:

* `BOOST_ROOT`
* `PYTHON_INCLUDE_DIR`
* `PYTHON_LIBRARY`
* `PYTHON_EXECUTABLE`

We also require that HyperGraphLib is installed: https://github.com/alex-87/HyperGraphLib. This will be added to CMakeLists.txt later on.

In order to ensure `python3` component is detected, you usually need to symlink the correct version:

```bash
cd /usr/lib/x86_64-linux-gnu && sudo ln -s libboost_python-py35.a libboost_python3.so
```

You can install the latest version of Boost (currently 1.66.0) from sources and then apply [this patch](https://gitlab.kitware.com/cmake/cmake/issues/17575) to correctly detect the new version of Boost in cmake. Make sure you compile Boost with the python version you want to use. For example:

```bash
./bootstrap.sh --with-python=$HOME/.pyenv/versions/3.6.3/bin/python3.6
export CPLUS_INCLUDE_PATH=$HOME/.pyenv/versions/3.6.3/include/python3.6m
./b2 -j4
sudo ./b2 install
```

Also, Python must be compiled with `-fPIC`:

```bash
env PYTHON_CFLAGS=-fPIC pyenv install -v 3.6.x
```
