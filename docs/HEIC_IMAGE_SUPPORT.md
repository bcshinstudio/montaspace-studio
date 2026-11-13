# HEIC/HEIF image support — Windows testing required

The image import and drag/drop routes share `app/imaging.py` and use
Pillow + `pillow-heif` as a fallback when Qt cannot decode HEIC, HEIF or AVIF.
Images are displayed as bounded previews without changing original files.
Linked projects reference the originals; portable projects embed the originals.

## Install or update dependencies (in each application environment)

```bat
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Important:** Copying new source files into a project does NOT install these
new packages. An existing installed EXE also does not get new codecs until
repackaged with them. Do not build or publish without testing the new EXE.

## Run the HEIC test with a real photo

```bat
.venv\Scripts\python.exe tools\check_image_codecs.py "C:\path\to\real_photo.HEIC"
```

The script must say PASS and report nonzero preview dimensions. Then run
`.venv\Scripts\python.exe main.py`, test Insert Image and Explorer
Drag & Drop for that HEIC, and save/reopen both linked and portable projects.
Repeat in both MontaSpace and MontaSpace Studio. Verify a rotated iPhone image,
a large image, and mixed valid/invalid files in a single drop.

## Regression and packaging

Run `run_regression_tests.bat`; follow with the application's installer build.
Install that installer on a clean Windows PC (without your development venv),
and repeat HEIC and AVIF tests there. Also check macOS separately when building
its native application: `pillow-heif` contains compiled platform-specific code.

This candidate has not passed actual Windows Qt/HEIC/installer testing here.
