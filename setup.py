from setuptools import setup

setup(
    name='bitlyapi',
    version='0.0.2',
    description='Api for https://bit.ly',
    url='http://github.com/oman36/bitlyapi',
    author='Petrov Vladimir',
    author_email='neoman36@gmail.com',
    license='MIT',
    packages=['bitlyapi'],
    install_requires=[
        'aiohttp==3.5.4',
    ],
    zip_safe=False,
)
