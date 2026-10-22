# Changelog

## v0.2.1

- Memperbaiki fokus keyboard dan pemfilteran langsung pada pencarian antrean.
- Mencari nama file, judul, dan artis dari metadata FLAC, termasuk lagu di luar 100 hasil yang tampil.
- Mendukung beberapa kata, perbedaan kapitalisasi, tanda baca, dan aksen.
- Menyamakan judul/artis yang ditampilkan dengan metadata pencarian; Enter memutar hasil pertama.
- Menambahkan pengujian regresi pencarian, dengan total 30 tes.

## v0.2.0

- Menambahkan pemilihan Wayland native melalui GTK layer-shell untuk compositor yang mendukungnya, dengan fallback X11/XWayland.
- Mempertahankan perilaku GNOME/Zorin serta menyediakan override `NOTCH_GDK_BACKEND`.
- Menambahkan paket native Arch/CachyOS, launcher, dan pengujian build/instalasi dalam container Arch.
- Menyertakan GTK layer-shell pada AppImage release dan panduan CachyOS.
- Menyediakan installer integrasi logo AppImage untuk menu desktop dan ikon file.

## v0.1.1

Paket publik pertama yang telah melewati build serta pemeriksaan otomatis GitHub Actions.

- Memperbaiki pemasangan dependensi Ubuntu untuk pembuat AppImage.
- Menguji source dan paket pada runner Ubuntu 24.04 sebelum publikasi.
- Menyertakan AppImage, checksum SHA-256, dan informasi build pada release.

## v0.1.0

Rilis awal Notch Music untuk Linux x86_64.

- Pemutar desktop GTK berbentuk notch dengan kontrol musik dan volume awal 30%.
- Antrean menyatu, pencarian, cover thumbnail, hapus per lagu, dan Clear.
- File/folder lokal, shuffle, repeat satu/semua, dan mute dengan pemulihan volume.
- Cover serta lirik embedded FLAC, highlight kalimat berdasarkan timestamp, dan LRC pendamping.
- Tema Dark, Light, dan Blur transparan dengan pilihan tersimpan.
- Ikon aplikasi baru dan paket AppImage dengan dependensi utama bawaan.

Target paket: Zorin OS 18 / Ubuntu 24.04 atau lebih baru, x86_64, glibc ≥ 2.39.
