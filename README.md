# Project Body Tracking Vtuber

Project ini tentang gimana ngetracking Sebuah Karakter(Avatar) dengan menggunakan Opencv dan mediapipe, dan visualisasinya menggunakan Unity. Cara kerjanya yaitu dari Python ke avatar di Unity menggunakan UDP networking. Sistem ini memungkinkan untuk menggerakkan tubuh avatar secara real-time dengan input dari webcam.

# Fitur Utama
* Real-time body: tracking pose menggunakan OpenCV dan MediaPipe.

* Unity avatar visualization: menampilkan dan menggerakkan avatar berdasarkan data tracking.

* UDP networking bridge: komunikasi Python → Unity lewat UDP untuk data pose secara real-time.

# Komponen dan Fungsi
| Komponen | Fungsi |
|-------------|--------------|
| Python capture module | Mendeteksi pose dari webcam |
| UDP bridge | Mengirimkan data pose ke Unity |
|Unity avatar scene |	Menerjemahkan data menjadi animasi avatar |

# requirements
* Python 3.8
* OpenCV
* MediaPipe
* Unity 2021+ atau kompatibel
* UDP networking permission

# Cara Pakai
1. Clone repository dan buka folder Python.

2. Pasang dependensi Python: pip install '-r requirements.txt' pada folder Python.

3. Buka project Unity lalu import scene dan pastikan script C# untuk menerima UDP aktif. 

4. Jalankan Python dengan 'py main.py' jalankan scene Unity untuk melihat avatar merespons atau Buka Aplikasi pada BodyTracking.exe pada folder App.
