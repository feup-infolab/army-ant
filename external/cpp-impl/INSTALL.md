```bash
cd /usr/lib/x86_64-linux-gnu && sudo ln -s libboost_python-py35.a libboost_python3.so
```

* Installed Boost 1.66.0 from sources and applied [this patch](https://gitlab.kitware.com/cmake/cmake/issues/17575) to correctly detect the new version of Boost.

```bash
./bootstrap.sh --with-python=$HOME/.pyenv/versions/3.6.3/bin/python3.6
export CPLUS_INCLUDE_PATH=$HOME/.pyenv/versions/3.6.3/include/python3.6m
./b2 -j4
sudo ./b2 install
```

```bash
env PYTHON_CFLAGS=-fPIC pyenv install -v 3.6.x
```
