# Advanced build instructions

If you are running the pipeline on the EBI LSF cluster, it already includes a local installation of the pipeline and its dependencies, so these instructions do not to be run again in this case. Refer to [instructions on setting up the common environment](environment.md).

## Python 3.8 installation
The pipeline requires Python 3.8 to run. The instructions in this section will be useful:
* If you have a different version of Python and want to install Python 3.8 without replacing your default `python` / `python3` executables;
* If you are running the pipeline on the `ebi-cli` cluster, which currently only supports Python 3.4.

### Common commands

Run the commands below and adjust `VERSION` and `INSTALL_PATH` if needed:

```bash
VERSION=3.8.1
INSTALL_PATH=/nfs/production3/eva/software/python-${VERSION}
mkdir -p ${INSTALL_PATH}
cd ${INSTALL_PATH}
wget https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tgz
tar zxfv Python-${VERSION}.tgz
mv Python-${VERSION}/* .
rmdir Python-${VERSION}
```

### Root installation
This way is easier as it doesn't require you to set up any paths manually. Package installation is also less likely to go wrong if you're using this way.

You need to have zlib development headers installed. Command for Debian/Ubuntu is `sudo apt-get -y install zlib1g-dev`.

```bash
./configure --with-zlib=/usr/include --enable-optimizations
make -j `nproc` altinstall
```

You can now invoke the new installation as `python3.8`.

### Non-root installation
This is the only way which will work on the `ebi-cli` cluster. It is also useful if you need to have more than one minor version installed simultaneously, e. g. Python 3.8.0 and 3.8.1.
```bash
./configure --prefix=${INSTALL_PATH}
make -j `nproc`
make -j `nproc` install
ln -s python python3
chmod a+x python python3
```

You can invoke this installation by using a direct path, `${INSTALL_PATH}/python`. In order to temporarily set it as default (and invoke simply as `python`), configure the paths:
```bash
export PATH=${INSTALL_PATH}:${INSTALL_PATH}/bin:$PATH
export PYTHONPATH=${INSTALL_PATH}
```

The installed Python version can then be called with either `python` or `python3`. You can also use either `pip` or `pip3` to install packages into this local distribution.

## Nextflow installation

The evidence string generation pipeline uses Nextflow, which itself relies on Java. You can install in the current directory as follows:
```bash
wget -qO- https://get.nextflow.io | bash
```
You can then include this in your `$PATH` variable if necessary, or invoke the executable directly.  For more details on installing Nextflow, see the [documentation](https://www.nextflow.io/docs/latest/getstarted.html).

## Deploying local OLS installation
During the preparation of 2019_04 release, which had to be synchronized with EFO v3, OLS had to be deployed locally because the production deployment of OLS on www.ebi.ac.uk/ols only supported EFO v2 at the time. This can be done using the following command (substitute the image version as appropriate):

```bash
sudo docker run -p 8080:8080 simonjupp/efo3-ols:3.4.0
```

To use the local deployment, uncomment the configuration section at the top of `/eva_cttv_pipeline/trait_mapping/ols.py` to specify the URL of the local installation. If you have deployed OLS on the different machine than the one you're using to run the pipeline, substitute the correct IP address of the machine where the OLS installation is deployed.

Please contact the semantic data integration team at [SPOT](https://www.ebi.ac.uk/about/spot-team) if you have questions about local OLS installation.

## Pipeline installation

Before proceeding with the installation, make sure to make the default Python 3.8 or later by running the `export PATH` commands described above.

```bash
git clone https://github.com/EBIvariation/eva-opentargets.git
cd eva-opentargets
python3 -m venv env
source env/bin/activate
python3 -m pip -q install --upgrade setuptools pip
python3 -m pip -q install -r requirements.txt
```

And then one of:
* To install: `python3 setup.py install`
* To install to develop: `python3 setup.py develop`
* To build a source distribution: `python3 setup.py sdist`

## JQ Installation
``jq`` is a lightweight and flexible command-line JSON processor, used to parse the evidence strings and extract specific fields to check for duplicates.

To install it you can:
* Either run the specific installation command (e.g. ``sudo apt-get install jq`` for Ubuntu) for your operating system (search for yours [here](https://stedolan.github.io/jq/download/)).
* Directly download it (since it has no runtime dependencies) and export its path:
````bash
JQ_INSTALL_PATH="/nfs/production3/eva/software/jq/1.6"
JQ_DOWNLOAD_VERSION="https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64"
mkdir -p ${JQ_INSTALL_PATH}
wget -O ${JQ_INSTALL_PATH}/jq ${JQ_DOWNLOAD_VERSION}
export PATH="${JQ_INSTALL_PATH}:$PATH"
````

## Tests
You can run all tests with: `python3 setup.py test`
