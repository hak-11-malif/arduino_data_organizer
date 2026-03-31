--------🚀 AERO-32 Data Organizer 🚀--------

AERO-32 Data Organizer adalah aplikasi Ground Control Station (GCS) berbasis Python yang dirancang untuk menerima, memproses, dan memvisualisasikan data telemetri dari mikrokontroler (seperti Arduino, ESP32, atau Teensy) secara real-time.
Aplikasi ini dikhususkan untuk penggunaan pada proyek roket amatir, uji statis (static test), atau sistem pemantauan sensor lainnya yang membutuhkan keandalan tinggi dan fleksibilitas konfigurasi.

![alt text](https://img.shields.io/badge/python-3.8+-blue.svg)

![alt text](https://img.shields.io/badge/PyQt-6-brightgreen.svg)

![alt text](https://img.shields.io/badge/license-MIT-blue.svg)


--------✨ Fitur Utama ✨--------

📡 Koneksi Serial Multi-Baud: Mendukung berbagai kecepatan baudrate hingga 921,600 untuk transmisi data cepat.

📊 Dynamic Graphing: Tambahkan modul grafik sebanyak yang Anda butuhkan secara dinamis.

🧮 Math Engine: Kalibrasi data mentah langsung di UI menggunakan rumus matematika (contoh: mengubah nilai ADC menjadi meter dengan rumus x * 0.1).

💾 Dual-Layer Logging:

Primary Log: Menyimpan data yang sudah diparse dalam format CSV siap pakai.
Redundant Log: Menyimpan data mentah (raw) dari serial untuk memastikan tidak ada data yang hilang jika terjadi kesalahan parsing.

🔄 Playback Mode: Putar kembali file log hasil peluncuran untuk analisis pasca-penerbangan dengan simulasi waktu nyata.

🛠️ Data Mapping System: Konfigurasikan urutan data (CSV index) dari mikrokontroler tanpa harus mengubah kode program Python.

🎮 Command Panel: Tombol kontrol kustom untuk mengirim perintah balik ke roket (seperti ARM_IGNITE).

📁 Profile Management: Simpan dan muat seluruh konfigurasi (grafik, rumus, mapping) dalam file JSON.


--------📸 Tampilan Aplikasi 📸--------

<img width="1365" height="714" alt="image" src="https://github.com/user-attachments/assets/38bd4172-b5d3-4b2c-a3da-88a7da26d9d2" />


--------🛠️ Instalasi 🛠️--------

1. Clone Repositori

git clone https://github.com/username/aero32-data-organizer.git
cd aero32-data-organizer

2. Instal Dependensi
   Pastikan Anda sudah menginstal Python 3.8 ke atas. Instal pustaka yang diperlukan menggunakan pip:

pip install PyQt6 pyqtgraph pyserial

3. Jalankan Aplikasi

python main.py


--------🚀 Cara Penggunaan 🚀--------

1. Konfigurasi Port: Pilih port serial mikrokontroler Anda dan tentukan baudrate.

2. Data Mapping: Klik "Konfigurasi Data Masuk", tentukan indeks kolom data dan berikan nama (contoh: Indeks 0 = Altitude, Indeks 1 = Pressure).

3. Tambah Grafik: Gunakan tombol "+ Tambah Modul Grafik" dan masukkan nama sensor yang sesuai dengan mapping.

4. Math Engine: Jika data mentah perlu dikalibrasi, klik "Math Engine" pada modul grafik dan masukkan rumus (misal: x + 10 atau x * 9.8).

5. Logging: Masukkan nama file untuk log Primary dan Redundant, lalu klik "START LOGGING" sebelum memulai misi.


--------📂 Struktur Proyek 📂--------

.

├── main.py              # Entry point aplikasi

├── gui/

│   ├── main_window.py   # Logika utama UI dan manajemen thread

│   └── graph_widget.py  # Komponen custom untuk grafik dan Math Engine

├── profiles/            # Folder penyimpanan konfigurasi JSON

└── logs/                # Folder default penyimpanan data telemetri


--------🛠️ Teknologi yang Digunakan 🛠️--------

Python 3: Bahasa pemrograman utama.

PyQt6: Framework untuk antarmuka pengguna (GUI).

PyQtGraph: Library grafik performa tinggi untuk data real-time.

PySerial: Komunikasi data melalui protokol serial UART.


--------🤝 Kontribusi 🤝--------

Kontribusi selalu terbuka! Jika Anda memiliki ide fitur baru atau menemukan bug:
Fork repositori ini.

Buat branch fitur baru (git checkout -b fitur/fiturMantap).

Commit perubahan Anda (git commit -m 'Menambah fitur Mantap').

Push ke branch tersebut (git push origin fitur/fiturMantap).

Buat Pull Request.


--------📄 Lisensi 📄--------

Distribusikan di bawah lisensi MIT. Lihat LICENSE untuk informasi lebih lanjut.
Dibuat dengan ❤️ untuk Komunitas Roket Indonesia.
Developed by hak11
