# Changelog

## v0.6.1

- Menyamakan lebar mode notch normal, queue, lirik, dan strip auto-hide agar perubahan isi tidak menggeser sisi player.
- Menghilangkan border, shadow, background-image, overlap satu piksel, dan tumpang tindih busur yang membentuk garis menggantung di ujung lekukan notch.
- Memperbesar cover, teks informasi lagu, menu, dan kontrol transport serta merapatkan padding pada tampilan awal notch.
- Mengganti transisi buka/tutup queue dan lirik secara atomik agar isi player tidak tertekan pada ukuran antara, serta langsung menutup menu setelah pilihan ditekan.

## v0.6.0

- Mengubah auto-hide notch menjadi strip ringkas setinggi satu baris yang tetap menampilkan lirik sesuai timing; hover membuka player penuh sementara.
- Melebarkan notch normal menjadi 75% dari lebar mode lirik serta menyesuaikan ukuran cover dan ikon transport.

## v0.5.0

- Linux: menambahkan integrasi MPRIS untuk Play/Pause, Next, Previous, Stop, seek, volume, repeat, shuffle, dan metadata melalui headset/TWS, keyboard multimedia, atau kontrol media desktop.
- Windows: menambahkan Play/Pause, Next, Previous, dan Stop melalui tombol media sistem untuk headset/TWS yang mengirim media key Windows; memakai perilaku pemutaran yang sama dengan MPRIS Linux.
- Windows: menghilangkan jendela garis hitam selebar monitor saat docking; mempertahankan bahu notch dan animasinya.
- Windows: memperjelas teks dark/blur dan memakai antialias grayscale untuk mengurangi tepi huruf berwarna. Tampilan dan integrasi MPRIS Zorin/Linux tetap dipertahankan.
- Menambahkan pengujian pesan media Win32, pelepasan hotkey saat keluar, dan smoke test pause/resume pada paket portable.

## v0.4.1

- Menambahkan menu Playlist di bawah Browse, berisi Create Playlist dan Load Playlist.
- Editor playlist menyatu dengan player seperti queue, dengan tombol ＋, disket, play dan hapus per lagu; mendukung drag-drop lagu/folder dari file manager.
- Create langsung membuka daftar kosong tanpa input nama. Nama dan lokasi dipilih saat Save, lalu nama file tampil sebagai judul playlist setelah Save/Load.
- Menyimpan playlist lokal dalam format `.notchplaylist`, berisi direktori asli lagu tanpa menyalin audio. Load memakai filter khusus playlist.
- Lagu yang dipindahkan atau dihapus tetap terlihat dalam daftar; play menampilkan pesan dan lokasi yang tidak ditemukan tanpa menghentikan lagu yang sedang berjalan.
- Menyimpan file secara atomik agar playlist lama tetap aman jika penulisan gagal; dokumen rusak atau versi yang tidak didukung ditolak.
- Memperbaiki teks Minimize yang kosong saat mengambang; Minimize tetap disembunyikan pada mode notch.
- Memperbarui README, gitignore dan bundling AppImage, Arch/CachyOS, serta Windows untuk modul playlist.
- 55 tes otomatis, termasuk save/load, Unicode, file hilang, validasi format dan kegagalan penyimpanan; pemeriksaan paket Windows mendukung variasi separator path MSYS2.

## v0.3.1

- Menambahkan Minimize sebelum Close saat player mengambang; pemutaran tetap berjalan dan player dapat dipulihkan lewat taskbar.
- Menambahkan tombol segitiga di tengah bawah notch: ▲ mengaktifkan auto-hide, ▼ membuat player tetap terbuka.
- Hover tepi atas membuka notch sementara; keluar dari area player langsung memicu slide menutup. Hover tidak mengubah status auto-hide.
- Memperbaiki koordinat pointer yang tertahan pada XWayland setelah mouse pindah ke desktop atau aplikasi Wayland native.
- Mempertahankan notch terbuka saat menu atau dialog Browse digunakan, tanpa menghilangkan queue/lirik.
- Mengurutkan preview README: floating player menjadi screenshot pertama, diikuti queue, lirik, dan mode notch.
- Menambahkan pengujian minimize, hover berulang, pin/unpin, perlindungan menu, dan kasus XWayland; total 47 tes otomatis.

## v0.3.0

- Player mengambang seperti Dynamic Island, drag, snap ke notch dengan animasi halus, lengkungan dan garis atas mengikuti tema.
- Menu ⋯ yang padat, status Lirik (On/Off), volume awal 30%, serta pemilihan tema tanpa menutup menu.
- Queue menyatu di bawah player saat mengambang, hingga lima lagu dan pencarian; tombol play/hapus tidak tertutup scrollbar.
- Queue dan lirik bisa aktif bersamaan saat mengambang. Lirik mengikuti tinggi player + queue; mode notch tetap bergantian di kanan.
- Visualizer spektrum audio bersegmen dengan pantulan, warna mengikuti tema, serta decay saat pause/mute.
- Baris info format audio, bit depth sumber, sample rate, atau bitrate jika tersedia; titik tengah sebagai pemisah.
- Tema Dark hitam murni; Light lebih kontras; Blur tanpa lapisan latar ganda. Ukuran font dan kontrol diperbesar.
- Browse mempertahankan panel yang sedang terbuka; perbaikan warna teks hover queue.
- Paket native Arch/CachyOS, AppImage, dan jalur Windows x64 experimental dengan runtime GTK/GStreamer portable serta smoke test sebelum publikasi.
- README diperbarui dengan enam screenshot asli dan panduan platform. 41 tes otomatis.

## v0.2.2

- Mencegah file pertama otomatis terpilih saat membuka dialog tambah musik atau berpindah folder.
- Memastikan Select tanpa pilihan manual mengambil seluruh isi folder.
- Mempertahankan pilihan melalui klik file, Ctrl+klik, navigasi keyboard, dan Ctrl+A.
- Menambahkan pengujian regresi seleksi file; total 33 tes lolos, serta pengujian dialog GTK.

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
