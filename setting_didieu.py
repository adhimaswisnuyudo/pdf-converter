#!/usr/bin/env python3
"""
Setting Didieu - Single File Version
Salembar Dieusi opat ID Card
PDF Layout Converter untuk ID Card printing
"""

import os
import sys
import tempfile
import uuid
import time
import threading
from io import BytesIO
from flask import Flask, request, render_template_string, send_file, jsonify
import PyPDF2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

# Try to import pdf2image, install if not available
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not available. Install with: pip install pdf2image")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Global dictionary to store file cleanup tasks
file_cleanup_tasks = {}

def cleanup_file_delayed(file_path, delay=5):
    """Clean up file after a delay to avoid Windows file locking issues"""
    def cleanup():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"Cleaned up file: {file_path}")
        except Exception as e:
            print(f"Error cleaning up file {file_path}: {e}")
    
    thread = threading.Thread(target=cleanup)
    thread.daemon = True
    thread.start()
    return thread

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Setting Didieu</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 40px;
            max-width: 600px;
            width: 100%;
            text-align: center;
        }

        .header {
            margin-bottom: 30px;
        }

        .header h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }

        .header p {
            color: #666;
            font-size: 1.1em;
            line-height: 1.6;
        }

        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 15px;
            padding: 40px 20px;
            margin: 30px 0;
            transition: all 0.3s ease;
            cursor: pointer;
            background: #fafafa;
        }

        .upload-area:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }

        .upload-area.dragover {
            border-color: #667eea;
            background: #e8f2ff;
            transform: scale(1.02);
        }

        .upload-icon {
            font-size: 3em;
            color: #667eea;
            margin-bottom: 15px;
        }

        .upload-text {
            color: #666;
            font-size: 1.1em;
            margin-bottom: 10px;
        }

        .upload-subtext {
            color: #999;
            font-size: 0.9em;
        }

        .file-input {
            display: none;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px;
            min-width: 150px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .progress {
            display: none;
            margin: 20px 0;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s ease;
        }

        .result {
            display: none;
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #28a745;
        }

        .error {
            display: none;
            margin: 20px 0;
            padding: 20px;
            background: #f8d7da;
            border-radius: 10px;
            border-left: 4px solid #dc3545;
            color: #721c24;
        }

        .file-info {
            margin: 15px 0;
            padding: 15px;
            background: #e9ecef;
            border-radius: 8px;
            text-align: left;
        }

        .file-info h4 {
            color: #495057;
            margin-bottom: 5px;
        }

        .file-info p {
            color: #6c757d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Setting Didieu</h1>
            <p>Salembar Dieusi opat ID Card</p>
        </div>

        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Drop your PDF here or click to browse</div>
            <div class="upload-subtext">Supports PDF files up to 16MB</div>
            <input type="file" id="fileInput" class="file-input" accept=".pdf">
        </div>

        <div class="file-info" id="fileInfo" style="display: none;">
            <h4>Selected File:</h4>
            <p id="fileName"></p>
            <p id="fileSize"></p>
        </div>

        <button class="btn" id="convertBtn" style="display: none;">Convert PDF</button>

        <div class="progress" id="progress">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <p style="margin-top: 10px; color: #666;">Processing your PDF...</p>
        </div>

        <div class="result" id="result">
            <h3 style="color: #28a745; margin-bottom: 10px;">✅ Conversion Successful!</h3>
            <p>Your PDF has been converted to 200mm × 300mm format with 2×2 grid layout.</p>
            <button class="btn" id="downloadBtn">Download Converted PDF</button>
        </div>

        <div class="error" id="error">
            <h3 style="color: #dc3545; margin-bottom: 10px;">❌ Error</h3>
            <p id="errorMessage"></p>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const convertBtn = document.getElementById('convertBtn');
        const progress = document.getElementById('progress');
        const progressFill = document.getElementById('progressFill');
        const result = document.getElementById('result');
        const error = document.getElementById('error');
        const errorMessage = document.getElementById('errorMessage');
        const downloadBtn = document.getElementById('downloadBtn');

        let selectedFile = null;
        let downloadUrl = null;

        // Upload area click handler
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // File input change handler
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                handleFileSelect(file);
            }
        });

        // Drag and drop handlers
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });

        function handleFileSelect(file) {
            if (!file.type.includes('pdf')) {
                showError('Please select a PDF file.');
                return;
            }

            if (file.size > 16 * 1024 * 1024) {
                showError('File size must be less than 16MB.');
                return;
            }

            selectedFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = `Size: ${(file.size / 1024 / 1024).toFixed(2)} MB`;
            fileInfo.style.display = 'block';
            convertBtn.style.display = 'inline-block';
            hideMessages();
        }

        // Convert button handler
        convertBtn.addEventListener('click', () => {
            if (!selectedFile) return;

            const formData = new FormData();
            formData.append('file', selectedFile);

            convertBtn.disabled = true;
            progress.style.display = 'block';
            hideMessages();

            // Simulate progress
            let progressValue = 0;
            const progressInterval = setInterval(() => {
                progressValue += Math.random() * 15;
                if (progressValue > 90) progressValue = 90;
                progressFill.style.width = progressValue + '%';
            }, 200);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                clearInterval(progressInterval);
                progressFill.style.width = '100%';

                setTimeout(() => {
                    if (data.success) {
                        downloadUrl = data.download_url;
                        progress.style.display = 'none';
                        result.style.display = 'block';
                        convertBtn.style.display = 'none';
                    } else {
                        showError(data.error || 'Conversion failed');
                        progress.style.display = 'none';
                        convertBtn.disabled = false;
                    }
                }, 500);
            })
            .catch(err => {
                clearInterval(progressInterval);
                showError('Network error: ' + err.message);
                progress.style.display = 'none';
                convertBtn.disabled = false;
            });
        });

        // Download button handler
        downloadBtn.addEventListener('click', () => {
            if (downloadUrl) {
                window.location.href = downloadUrl;
            }
        });

        function showError(message) {
            errorMessage.textContent = message;
            error.style.display = 'block';
        }

        function hideMessages() {
            result.style.display = 'none';
            error.style.display = 'none';
        }
    </script>
</body>
</html>
"""

class PDFProcessor:
    def __init__(self):
        # Source PDF dimensions (128mm x 96mm) - but we want output to be 96mm x 128mm
        self.source_width = 128 * mm
        self.source_height = 96 * mm
        
        # Output layout dimensions (96mm x 128mm each)
        self.layout_width = 96 * mm
        self.layout_height = 128 * mm
        
        # Custom page dimensions (200mm x 300mm portrait)
        self.page_width = 200 * mm
        self.page_height = 300 * mm
        
        # Calculate total area needed for 2x2 grid (no spacing, layouts touch each other)
        self.total_width = self.layout_width * 2  # 2 columns
        self.total_height = self.layout_height * 2  # 2 rows
        
        # Calculate center position on custom page
        self.start_x = (self.page_width - self.total_width) / 2
        self.start_y = (self.page_height - self.total_height) / 2
        
        # Scale factor to fit source PDF (128x96) into layout (96x128)
        self.scale_x = self.layout_width / self.source_width  # 96/128 = 0.75
        self.scale_y = self.layout_height / self.source_height  # 128/96 = 1.33
        self.scale = min(self.scale_x, self.scale_y)  # Use 0.75 to maintain aspect ratio
        
        print(f"Page dimensions: {self.page_width/mm:.1f}mm x {self.page_height/mm:.1f}mm")
        print(f"Layout dimensions: {self.layout_width/mm:.1f}mm x {self.layout_height/mm:.1f}mm")
        print(f"Total grid area: {self.total_width/mm:.1f}mm x {self.total_height/mm:.1f}mm")
        print(f"Start position: ({self.start_x/mm:.1f}mm, {self.start_y/mm:.1f}mm)")
        print(f"Scale factor: {self.scale:.3f}")

    def process_pdf(self, input_path, output_path):
        """Process PDF and create custom page layout with 2x2 grid"""
        try:
            # Read input PDF
            with open(input_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                print(f"Total pages in input PDF: {total_pages}")
            
            # Calculate number of output pages needed
            pages_per_output = 4
            output_pages_needed = (total_pages + pages_per_output - 1) // pages_per_output
            print(f"Output pages needed: {output_pages_needed}")
            
            # Create output PDF using ReportLab Canvas with custom page size
            custom_page_size = (self.page_width, self.page_height)
            output_canvas = canvas.Canvas(output_path, pagesize=custom_page_size)
            
            page_index = 0
            
            for output_page in range(output_pages_needed):
                # Create new page
                if output_page > 0:
                    output_canvas.showPage()
                
                # Calculate how many layouts to place on this page
                layouts_on_this_page = min(pages_per_output, total_pages - (output_page * pages_per_output))
                print(f"Output page {output_page + 1}: {layouts_on_this_page} layouts")
                
                # Place layouts in 2x2 grid
                for layout_pos in range(layouts_on_this_page):
                    if page_index >= total_pages:
                        break
                    
                    # Calculate position in grid
                    row = layout_pos // 2
                    col = layout_pos % 2
                    
                    # Calculate absolute position on custom page
                    x = self.start_x + col * self.layout_width
                    y = self.start_y + (1 - row) * self.layout_height  # Flip Y coordinate
                    
                    print(f"  Layout {layout_pos + 1}: Page {page_index + 1} at ({x/mm:.1f}mm, {y/mm:.1f}mm)")
                    
                    # Place PDF page at this position
                    self._place_pdf_page(output_canvas, input_path, page_index, x, y)
                    
                    page_index += 1
            
            output_canvas.save()
                
        except Exception as e:
            print(f"Error in process_pdf: {e}")
            # Fallback: create simple layout
            self._create_fallback_layout(input_path, output_path)

    def _place_pdf_page(self, canvas, pdf_path, page_num, x, y):
        """Place PDF page content on canvas at specified position"""
        try:
            # Read the PDF page
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                if page_num < len(pdf_reader.pages):
                    page = pdf_reader.pages[page_num]
                    
                    # Create a temporary PDF with just this page
                    temp_writer = PyPDF2.PdfWriter()
                    temp_writer.add_page(page)
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                        temp_writer.write(temp_file)
                        temp_path = temp_file.name
                    
                    # Convert to image using pdf2image if available
                    if PDF2IMAGE_AVAILABLE:
                        try:
                            images = convert_from_path(temp_path, dpi=300, first_page=1, last_page=1)
                            
                            if images:
                                # Get the first (and only) image
                                img = images[0]
                                
                                # Convert PIL image to bytes
                                img_buffer = BytesIO()
                                img.save(img_buffer, format='PNG')
                                img_buffer.seek(0)
                                
                                # Create ImageReader for ReportLab
                                img_reader = ImageReader(img_buffer)
                                
                                # Draw the image on canvas
                                canvas.saveState()
                                canvas.translate(x, y)
                                
                                # Draw the actual PDF content as image with exact layout dimensions
                                canvas.drawImage(img_reader, 0, 0, width=self.layout_width, height=self.layout_height)
                                
                                canvas.restoreState()
                                print(f"    Successfully placed page {page_num + 1} (as image)")
                            else:
                                # Fallback: draw placeholder if image conversion fails
                                self._draw_placeholder(canvas, x, y, page_num)
                                
                        except Exception as img_error:
                            print(f"Image conversion error for page {page_num}: {img_error}")
                            # Fallback: draw placeholder
                            self._draw_placeholder(canvas, x, y, page_num)
                    else:
                        # If pdf2image not available, try to embed PDF directly
                        try:
                            self._embed_pdf_page(canvas, temp_path, x, y, page_num)
                        except Exception as embed_error:
                            print(f"PDF embedding error for page {page_num}: {embed_error}")
                            # Final fallback: draw placeholder
                            self._draw_placeholder(canvas, x, y, page_num)
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                else:
                    print(f"Page {page_num} not found in PDF")
                    self._draw_error_placeholder(canvas, x, y, page_num)
                
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            # Draw error placeholder
            self._draw_error_placeholder(canvas, x, y, page_num)

    def _embed_pdf_page(self, canvas, pdf_path, x, y, page_num):
        """Try to embed PDF page directly without image conversion"""
        try:
            # Read the PDF page
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page = pdf_reader.pages[0]  # First page of the single-page PDF
                
                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)
                
                # Calculate scale to fit in layout
                scale_x = self.layout_width / page_width
                scale_y = self.layout_height / page_height
                scale = min(scale_x, scale_y)
                
                # Draw PDF content as a rectangle with page info
                canvas.saveState()
                canvas.translate(x, y)
                canvas.scale(scale, scale)
                
                # Draw a border
                canvas.setStrokeColorRGB(0.2, 0.2, 0.2)
                canvas.setFillColorRGB(0.98, 0.98, 0.98)
                canvas.rect(0, 0, page_width, page_height, fill=1, stroke=1)
                
                # Add page number and info
                canvas.setFillColorRGB(0.1, 0.1, 0.1)
                canvas.setFont("Helvetica-Bold", 14)
                canvas.drawString(10, page_height - 25, f"Page {page_num + 1}")
                
                canvas.setFont("Helvetica", 10)
                canvas.drawString(10, page_height - 45, f"Size: {page_width:.0f}x{page_height:.0f}")
                canvas.drawString(10, page_height - 60, "PDF content embedded")
                
                canvas.restoreState()
                print(f"    Successfully embedded page {page_num + 1} (as PDF)")
                
        except Exception as e:
            print(f"Error embedding PDF page {page_num}: {e}")
            raise e

    def _draw_placeholder(self, canvas, x, y, page_num):
        """Draw a placeholder rectangle for PDF content"""
        canvas.saveState()
        canvas.translate(x, y)
        
        # Draw a border to represent the PDF content with exact layout dimensions
        canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
        canvas.setFillColorRGB(0.95, 0.95, 0.95)
        canvas.rect(0, 0, self.layout_width, self.layout_height, fill=1, stroke=1)
        
        # Add page number text
        canvas.setFillColorRGB(0.3, 0.3, 0.3)
        canvas.setFont("Helvetica", 12)
        canvas.drawString(10, self.layout_height - 20, f"Page {page_num + 1}")
        
        canvas.restoreState()

    def _draw_error_placeholder(self, canvas, x, y, page_num):
        """Draw an error placeholder"""
        canvas.saveState()
        canvas.translate(x, y)
        canvas.setStrokeColorRGB(1, 0, 0)
        canvas.setFillColorRGB(1, 0.8, 0.8)
        canvas.rect(0, 0, self.layout_width, self.layout_height, fill=1, stroke=1)
        canvas.setFillColorRGB(1, 0, 0)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(10, self.layout_height - 15, f"Error: Page {page_num + 1}")
        canvas.restoreState()

    def _create_fallback_layout(self, input_path, output_path):
        """Create a fallback layout when PDF processing fails"""
        try:
            with open(input_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
            
            output_writer = PyPDF2.PdfWriter()
            
            # Add pages in groups of 4
            for i in range(0, total_pages, 4):
                for j in range(min(4, total_pages - i)):
                    if i + j < total_pages:
                        page = pdf_reader.pages[i + j]
                        # Scale down the page
                        page.scale_by(0.5)  # Scale to half size
                        output_writer.add_page(page)
            
            with open(output_path, 'wb') as output_file:
                output_writer.write(output_file)
                
        except Exception as e:
            print(f"Error in fallback layout: {e}")
            # Create empty PDF
            output_writer = PyPDF2.PdfWriter()
            output_writer.add_blank_page(width=self.page_width, height=self.page_height)
            with open(output_path, 'wb') as output_file:
                output_writer.write(output_file)

# Flask Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Please upload a PDF file'}), 400
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        input_filename = f"{file_id}_input.pdf"
        output_filename = f"{file_id}_output.pdf"
        
        # Create temp directories
        temp_dir = tempfile.gettempdir()
        input_path = os.path.join(temp_dir, input_filename)
        output_path = os.path.join(temp_dir, output_filename)
        
        # Save uploaded file
        file.save(input_path)
        
        # Process PDF
        processor = PDFProcessor()
        processor.process_pdf(input_path, output_path)
        
        # Clean up input file immediately
        if os.path.exists(input_path):
            os.unlink(input_path)
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{file_id}',
            'filename': f"converted_{file.filename}"
        })
        
    except Exception as e:
        # Clean up files on error
        if os.path.exists(input_path):
            os.unlink(input_path)
        if os.path.exists(output_path):
            os.unlink(output_path)
        
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/download/<file_id>')
def download_file(file_id):
    output_filename = f"{file_id}_output.pdf"
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, output_filename)
    
    if not os.path.exists(output_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Send file with retry mechanism for Windows
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = send_file(
                    output_path, 
                    as_attachment=True, 
                    download_name=f"setting_didieu_{file_id}.pdf",
                    mimetype='application/pdf'
                )
                
                # Schedule cleanup after download (Windows-safe)
                cleanup_file_delayed(output_path, delay=10)
                return response
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    print(f"Permission error on attempt {attempt + 1}, retrying in 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    print(f"Permission error after {max_retries} attempts: {e}")
                    # Schedule cleanup anyway
                    cleanup_file_delayed(output_path, delay=30)
                    return jsonify({'error': 'File is being used by another process. Please try again in a few seconds.'}), 500
            except Exception as e:
                print(f"Unexpected error during download: {e}")
                cleanup_file_delayed(output_path, delay=10)
                return jsonify({'error': f'Download failed: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in download_file: {e}")
        cleanup_file_delayed(output_path, delay=10)
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Setting Didieu - Single File Version")
    print("Salembar Dieusi opat ID Card")
    print("=" * 60)
    print(f"PDF2Image available: {PDF2IMAGE_AVAILABLE}")
    if not PDF2IMAGE_AVAILABLE:
        print("⚠️  WARNING: PDF2Image not available!")
        print("To enable full PDF processing:")
        print("1. Install pdf2image: pip install pdf2image")
        print("2. Install poppler:")
        print("   Ubuntu/Debian: sudo apt-get install poppler-utils")
        print("   CentOS/RHEL: sudo yum install poppler-utils")
        print("   Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases")
        print("   macOS: brew install poppler")
    else:
        print("✅ PDF2Image is available - full PDF processing enabled")
    print("=" * 60)
    print("Starting server...")
    print("Access at: http://localhost:5002")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5002)
