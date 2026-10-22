# AppImage build

Build target: Linux x86_64, Zorin OS 18 / Ubuntu 24.04 (glibc 2.39 or newer). Compatibility with older distributions is not claimed.

The package includes Python 3.12, PyGObject, Pycairo, GTK 3, GStreamer plugins/codecs, image loaders, introspection data, icon assets, and library dependencies. The host supplies glibc, desktop/audio services, fonts, X11/XWayland, and graphics drivers.

Build from the project root:

```bash
mkdir -p packaging/tools
curl -fL https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64 -o packaging/tools/runtime-x86_64
sha256sum -c packaging/runtime.sha256
/usr/bin/python3 packaging/build_appimage.py
```

Requires the app's development/runtime dependencies, `mksquashfs`, `ldd`, and `dpkg-query`. The builder writes `dist/Notch-Music-x86_64.AppImage`, a SHA-256 checksum, and `build-info.json`. The latter records the downloaded runtime hash. The upstream continuous runtime may change between builds.

The official runtime comes from [AppImage/type2-runtime](https://github.com/AppImage/type2-runtime). Bundled Debian copyright notices are included in the payload.

Run:

```bash
chmod +x dist/Notch-Music-x86_64.AppImage
./dist/Notch-Music-x86_64.AppImage
```

The AppImage can be moved out of the project. It accepts music file paths as arguments. Settings remain in the user config directory; audio caches and the image loader cache use the user cache directory.

Headless verification (without opening a desktop window):

```bash
./dist/Notch-Music-x86_64.AppImage --appimage-extract-and-run --self-test
```

`--appimage-extract-and-run` also runs the app on systems that do not allow FUSE mounting.
