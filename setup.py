import setuptools


with open("requirements.txt") as fp:
    install_requires = fp.read().splitlines()

setuptools.setup(
    name="escraper",
    version="0.0.3",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    include_package_data=True,
)
