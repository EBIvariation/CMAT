import os

from setuptools import setup, find_packages


# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

version = open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bin', 'cmat', 'VERSION')).read().strip()


def get_requires():
    requires = []
    with open("requirements.txt", "rt") as req_file:
        for line in req_file:
            requires.append(line.rstrip())
    return requires


# More classifiers to be added (https://pypi.org/classifiers/ - e.g. Operating System)
classifiers = [
    "Natural Language :: English",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3"
]

# Extract the markdown description. Supported by PyPi in its native format
with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='cmat',
      version=version,
      author_email='opentargets-clinvar@ebi.ac.uk',
      url='https://github.com/EBIvariation/CMAT',
      packages=find_packages(),
      install_requires=get_requires(),
      package_data={
          'cmat': ['OT_SCHEMA_VERSION', 'pipelines/*']
      },
      description='ClinVar Mapping and Annotation Toolkit',
      long_description=long_description,
      long_description_content_type="text/markdown",
      tests_require=get_requires(),
      setup_requires=get_requires(),
      test_suite='tests',
      classifiers=classifiers,
      scripts=[os.path.join(os.path.dirname(__file__), 'bin', 'upload_to_gcloud.py')]
      )
