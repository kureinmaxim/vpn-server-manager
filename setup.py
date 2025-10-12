from setuptools import setup, find_packages
import os
import json

# Читаем версию из config.json
def get_version():
    try:
        with open("config.json", "r", encoding="utf-8") as fh:
            config = json.load(fh)
            return config.get('app_info', {}).get('version', '4.0.3')
    except:
        return '4.0.3'

# Читаем README файл
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Читаем requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="vpn-server-manager-clean",
    version=get_version(),
    author="Куреин М.Н.",
    author_email="",
    description="VPN Server Manager - Clean - Управление VPN серверами",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-flask>=1.2.0",
            "pytest-cov>=4.1.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "bandit>=1.7.0",
        ],
        "build": [
            "pyinstaller>=5.13.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vpn-manager=run:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["templates/*", "static/*", "translations/*"],
    },
    zip_safe=False,
)
