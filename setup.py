import ukcpUpdater
from cx_Freeze import setup, Executable

install_requires = []
setup_requires = []
#tests_require = ["pytest"]

#os.add_dll_directory(os.getcwd())

base = "ukcpUpdater-" + ukcpUpdater.__version__

# http://msdn.microsoft.com/en-us/library/windows/desktop/aa371847(v=vs.85).aspx
shortcut_table = [
    (
        "DesktopShortcut",  # Shortcut
        "DesktopFolder",  # Directory_
        "UKCP Updater",  # Name
        "TARGETDIR",  # Component_
        f"[TARGETDIR]{base}.exe",  # Target
        None,  # Arguments
        None,  # Description
        None,  # Hotkey
        None,  # Icon
        None,  # IconIndex
        None,  # ShowCmd
        "TARGETDIR",  # WkDir
    )
]

# Now create the table dictionary
msi_data = {"Shortcut": shortcut_table}

# Change some default MSI options and specify the use of the above defined tables
bdist_msi_options = {"data": msi_data}

with open("requirements.txt") as f:
    install_requires = f.read()[1:].splitlines()[1:]

setup(
    packages=["ukcpUpdater"],
    name="VATSIM UK Controller Pack Updater",
    version=ukcpUpdater.__version__,
    description="VATSIM UK Controller Pack Updater",
    long_description="..\README.md",
    long_description_content_type="text/markdown",
    url="https://vatsim.uk",
    author="Chris Parkinson",
    author_email="@chssn",
    license="MIT",
    classifiers=["Programming Language :: Python :: 3.9"],
    python_requires=">=3.9.0",
    executables=[
        Executable(
            "ukcpUpdater\__main__.py",
            target_name=base,
            icon="ukcpu.ico",
            shortcut_name="UKCP Updater",
            shortcut_dir="DesktopFolder",
            copyright="2023, SNET Technical Solutions Ltd",
        )
    ],
    options={
        "build_exe": {
            "include_files": ["local\\"]
        },
        "bdist_msi": {
            "data": msi_data,
            "upgrade_code": "{339b458f-2a3f-4e69-bb62-42c7e63cb35a}",
            "target_name": base,
            "install_icon": "ukcpu.ico",
            "summary_data": {"author": "SNET Technical Solutions Ltd"},
        },
    },
    include_package_data=True,
)
