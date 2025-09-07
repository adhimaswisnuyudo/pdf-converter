from flask import Flask, request, render_template, send_file, jsonify
import os
import tempfile
from pdf_processor import PDFProcessor
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'

# Create directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

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
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Save uploaded file
        file.save(input_path)
        
        # Process PDF
        processor = PDFProcessor()
        processor.process_pdf(input_path, output_path)
        
        # Clean up input file
        os.remove(input_path)
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{file_id}',
            'filename': f"converted_{file.filename}"
        })
        
    except Exception as e:
        # Clean up files on error
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/download/<file_id>')
def download_file(file_id):
    output_filename = f"{file_id}_output.pdf"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    if not os.path.exists(output_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(output_path, as_attachment=True, download_name=f"converted_layout_{file_id}.pdf")
    finally:
        # Clean up output file after download
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
