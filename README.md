# PDF Layout Converter

Aplikasi web untuk mengkonversi PDF dengan ukuran 128mm × 96mm menjadi format A4 dengan layout 2×2 grid.

## Fitur

- **Input**: PDF dengan ukuran 128mm × 96mm (portrait)
- **Output**: PDF A4 dengan layout 2×2 grid
- **Multiple Pages**: Setiap halaman A4 berisi maksimal 4 layout dari PDF asli
- **Automatic Scaling**: Mempertahankan aspect ratio dan center content
- **Web Interface**: Upload dan download yang mudah digunakan

## Contoh Konversi

- 1 halaman input → 1 halaman A4 (1 layout)
- 4 halaman input → 1 halaman A4 (4 layout)
- 5 halaman input → 2 halaman A4 (4 layout + 1 layout)
- 8 halaman input → 2 halaman A4 (masing-masing 4 layout)

## Instalasi

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Jalankan aplikasi:
```bash
python app.py
```

3. Buka browser dan akses: `http://localhost:5000`

## Struktur Project

```
pdf-converter/
├── app.py                 # Flask web application
├── pdf_processor.py       # PDF processing logic
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Web interface
├── uploads/              # Temporary upload folder
└── outputs/              # Temporary output folder
```

## Teknologi

- **Backend**: Python Flask
- **PDF Processing**: PyPDF2, ReportLab
- **Frontend**: HTML, CSS, JavaScript
- **Image Processing**: Pillow

## Cara Penggunaan

1. Upload file PDF dengan ukuran 128mm × 96mm
2. Klik "Convert PDF"
3. Tunggu proses konversi selesai
4. Download hasil konversi

## Catatan

- File input harus berformat PDF
- Ukuran maksimal file: 16MB
- Output akan otomatis terhapus setelah download
- Aplikasi akan mempertahankan aspect ratio dari PDF asli
# pdf-converter
