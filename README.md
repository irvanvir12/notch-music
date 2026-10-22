<p align="center">
  <img src="assets/notch-music-logo-v2.png" width="144" alt="Notch Music logo">
</p>

<h1 align="center">Notch Music</h1>
<p align="center">Pemutar musik Linux berbentuk notch, selalu dekat di atas layar.</p>

Notch Music adalah aplikasi desktop dengan pemutar ringkas, lirik tersinkron, dan panel antrean yang menyatu. Dibuat dengan Python, GTK 3, dan GStreamer.

## Unduh dan jalankan

Unduh **Notch-Music-x86_64.AppImage** dari [GitHub Releases](https://github.com/irvanvir12/notch-music/releases/latest), lalu:

```bash
chmod +x Notch-Music-x86_64.AppImage
./Notch-Music-x86_64.AppImage
```

Target paket: **Linux x86_64 dengan glibc ≥ 2.39**, termasuk Zorin OS 18 / Ubuntu 24.04 dan CachyOS/Arch yang diperbarui. Python, GTK, GStreamer, dan codec utama disertakan. AppImage dapat dipindahkan ke folder lain tanpa membawa source proyek.

Jika FUSE tidak tersedia:

```bash
./Notch-Music-x86_64.AppImage --appimage-extract-and-run
```

## Ikon dan menu aplikasi Linux

Logo sudah disertakan di dalam AppImage. Untuk mendaftarkannya pada menu aplikasi dan memasang ikon khusus file di GNOME/Zorin, jalankan dari source:

```bash
/usr/bin/python3 packaging/install_desktop.py /path/ke/Notch-Music-x86_64.AppImage
```

Installer hanya bekerja pada akun pengguna: memasang ikon dalam beberapa ukuran ke `~/.local/share/icons`, menambahkan launcher ke `~/.local/share/applications`, dan mencoba mengatur ikon file melalui metadata GIO. Tidak membuka aplikasi atau mengubah asosiasi audio default. Jika AppImage dipindahkan, jalankan installer lagi dengan lokasi barunya. Ikon khusus file bergantung pada dukungan file manager; refresh folder jika ikon lama masih terlihat.

## Fitur

- Pemutar tanpa bingkai di tengah atas layar, dengan lengkungan yang menyatu ke sisi atas.
- Play/pause, sebelumnya/berikutnya, seek, dan volume awal **30%**.
- Mute menggeser slider ke nol; unmute mengembalikan posisi sebelumnya.
- Antrean menyatu dengan pencarian, thumbnail cover, hapus per lagu, dan **Clear**. File asli tidak dihapus.
- Shuffle dan repeat **mati → satu lagu → semua lagu**, dengan ikon merah saat aktif.
- Cover, judul, artis, dan lirik embedded FLAC; file `.lrc`/`.txt` pendamping juga didukung.
- Kalimat lirik aktif berwarna merah mengikuti timestamp; teks panjang turun baris dan rata tengah.
- Tema **Dark → Light → Blur** berganti lewat satu ikon dan tersimpan otomatis.

## Menambahkan musik

Klik **＋** untuk membuka dialog pemilih file terpisah. Pilih satu lagu, **Ctrl+klik** untuk beberapa lagu, atau **Ctrl+A** untuk seluruh file yang ditampilkan, lalu **Select**.

Untuk mengambil isi folder, buka folder lalu klik **Select** tanpa memilih file. Lagu dalam subfolder ikut dipindai di latar belakang. Anda juga bisa menyeret file musik ke notch.

Klik ikon antrean untuk membuka/menutup panel. Pencarian langsung memfilter nama file, judul, dan artis dari metadata FLAC di seluruh antrean, dengan maksimal 100 hasil ditampilkan sekaligus. Pencarian mengabaikan kapitalisasi dan mendukung beberapa kata dalam urutan berbeda. Tekan Enter untuk memutar hasil pertama. Klik lagu untuk memutarnya atau ikon tempat sampah untuk menghapusnya dari antrean.

| Kontrol | Fungsi |
| --- | --- |
| Space | Play/pause saat tidak mengetik pada pencarian |
| Esc | Lipat panel; jika panel sudah tertutup, keluar dari aplikasi |
| Ikon speaker | Mute/unmute |
| Ikon lirik | Tampilkan/sembunyikan lirik |
| Ikon tema | Dark → Light → Blur |
| × | Keluar |

## Jalankan dari source

```bash
git clone git@github.com:irvanvir12/notch-music.git
cd notch-music
sudo apt install python3 python3-gi python3-cairo python3-gi-cairo \
  gir1.2-gtk-3.0 gir1.2-gstreamer-1.0 \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-libav
./run.sh
# Langsung membuka lagu:
./run.sh ~/Music/lagu.flac
```

## CachyOS / Arch Linux

AppImage juga dapat dipakai di CachyOS x86_64 yang diperbarui. Jika FUSE tidak tersedia, gunakan `--appimage-extract-and-run` seperti di atas.

Paket native `.pkg.tar.zst` juga tersedia di [Releases](https://github.com/irvanvir12/notch-music/releases/latest):

```bash
sudo pacman -Syu
sudo pacman -U ./notch-music-0.2.1-1-x86_64.pkg.tar.zst
notch-music
```

Untuk menjalankan source dengan dependensi native:

```bash
sudo pacman -Syu --needed git python python-gobject python-cairo gtk3 gtk-layer-shell \
  gstreamer gst-plugins-base gst-plugins-good gst-libav adwaita-icon-theme
git clone https://github.com/irvanvir12/notch-music.git
cd notch-music
./run.sh
```

Alternatif paket native yang dikelola pacman (jalankan sebagai pengguna biasa, bukan root):

```bash
sudo pacman -Syu --needed base-devel
./packaging/arch/build-package.sh
```

Skrip membuat arsip dari checkout, menguji, membangun `.pkg.tar.zst`, lalu menawarkan instalasi melalui `makepkg -si`. Paket memasang perintah `notch-music` dan launcher menu aplikasi. Ini paket lokal, belum dipublikasikan ke AUR.

Pada Wayland dengan compositor yang mendukung layer-shell, aplikasi memilih Wayland native dan menempel di sisi atas layar. GNOME/Zorin tetap memakai XWayland. Untuk fallback pada CachyOS Wayland, pasang `xorg-xwayland`. Anda dapat memaksa backend:

```bash
NOTCH_GDK_BACKEND=x11 ./run.sh
NOTCH_GDK_BACKEND=wayland ./run.sh
```

Bila compositor tidak mendukung layer-shell, fallback XWayland dipakai jika tersedia. Dukungan posisi, transparansi, dan panel tetap bergantung pada compositor. CI menguji source, build, dan instalasi paket di container Arch; ini bukan pengujian visual pada desktop CachyOS asli.

## Build dan pengujian

Lihat [panduan packaging](packaging/README.md) untuk membangun AppImage. Folder `dist/`, runtime unduhan, cache, dan konfigurasi lokal diabaikan Git. Binary AppImage didistribusikan melalui aset release.

```bash
/usr/bin/python3 -m unittest discover -s tests -v
./dist/Notch-Music-x86_64.AppImage --appimage-extract-and-run --self-test
```

Workflow [Release AppImage](.github/workflows/release.yml) menguji, membangun, dan memublikasikan AppImage beserta checksum saat tag `v*` dikirim.

## Catatan desktop dan lirik

Pada GNOME Wayland, aplikasi memakai XWayland untuk posisi atas dan keep-above. Window manager menentukan posisi akhir; panel sistem dapat bertumpuk dengan notch. Area di luar notch tetap meneruskan klik, dan aplikasi tidak mengubah pengaturan panel desktop.

Tema **Blur** bersifat transparan; efek kabur sebenarnya bergantung pada compositor. Lirik tersinkron memerlukan timestamp; lirik tanpa timing menampilkan kalimat awal serta teks penuh pada tooltip. Highlight mengikuti **per baris/kalimat**, bukan per kata. Spotify/MPRIS, autostart, dan penyimpanan antrean antar-sesi belum tersedia.

Pengaturan tema disimpan di `$XDG_CONFIG_HOME/notch-music/settings.json` (default `~/.config/notch-music/settings.json`).
