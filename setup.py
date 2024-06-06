from setuptools import setup, find_packages

setup(
    name='string_theory',
    version='0.0.1',
    packages=find_packages(include=['string_theory', 'string_theory.*']),
    license='GNU General Public License v3.0',
    author='Marko',
    author_email='m.a.vasylenko@student.utwente.nl',
    description='ISLa generative testing',
    install_requires=['isla-solver', 'islearn']
)
