# Expanded media format support — development candidate

## Images (both applications)

Import and drag-and-drop accept: PNG, JPG/JPEG, BMP, WebP, GIF, TIFF/TIF, HEIC/HEIF, AVIF.

Images are loaded via Qt `QImageReader`; availability depends on the actual Qt image
plugins bundled on the target system. Animated GIF is displayed as a **static first frame**.
HEIC/HEIF and AVIF are **best effort**: the extension is allowed, but without an
installed Qt decoder the image cannot open. The Insert Image dialog now reports
read failures instead of silently doing nothing. Drag-drop may still silently reject.

## Videos (Studio only)

Import and drag-and-drop accept: MP4, MOV, MKV, AVI, WebM, WMV, M4V, MPG/MPEG.
Playback and poster generation use the existing Qt multimedia/FFmpeg system;
actual decodability depends on the audio/video codec inside the container.
The existing player controls display a playback error on decode failure.

Existing linked and portable project formats are unchanged. Extensions are
preserved in portable packages; no media is transcoded.

## Required validation before Windows release

1. Test each format on the user's actual packaged Windows installer.
2. Test import via dialog and drag/drop, playback, seeking, audio, and A/B loops
   (Studio) as well as thumbnails, linked save/reopen, portable save/reopen.
3. For HEIC/AVIF check whether the bundled Qt image plugins decode them; if not,
   choose a vetted optional decoder/library, assess installer impact, then re-test.
4. Test invalid/corrupt media and check for crashes and informative errors.
5. Test on macOS separately before describing that platform as supported.

**This package is not a verified release.** Configuration/source checks alone
cannot establish the availability of target Windows multimedia codecs.
