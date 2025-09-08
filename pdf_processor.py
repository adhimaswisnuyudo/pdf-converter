import PyPDF2
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import io
import tempfile
import os
from pdf2image import convert_from_path

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
        # We need to rotate and scale
        self.scale_x = self.layout_width / self.source_width  # 96/128 = 0.75
        self.scale_y = self.layout_height / self.source_height  # 128/96 = 1.33
        self.scale = min(self.scale_x, self.scale_y)  # Use 0.75 to maintain aspect ratio
        
        # Calculate final scaled dimensions
        self.final_width = self.source_width * self.scale
        self.final_height = self.source_height * self.scale
        
        print(f"Page dimensions: {self.page_width/mm:.1f}mm x {self.page_height/mm:.1f}mm")
        print(f"Layout dimensions: {self.layout_width/mm:.1f}mm x {self.layout_height/mm:.1f}mm")
        print(f"Total grid area: {self.total_width/mm:.1f}mm x {self.total_height/mm:.1f}mm")
        print(f"Start position: ({self.start_x/mm:.1f}mm, {self.start_y/mm:.1f}mm)")
        print(f"Scale factor: {self.scale:.3f}")

    def merge_and_process_pdfs(self, input_paths, output_path):
        """Merge multiple PDFs into a single PDF and process with existing layout."""
        try:
            # Create temporary merged input
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_merged:
                merged_path = temp_merged.name

            merger = PyPDF2.PdfWriter()

            # Append pages from all inputs in order
            for path in input_paths:
                if not os.path.exists(path):
                    continue
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        merger.add_page(page)

            # Write merged PDF
            with open(merged_path, 'wb') as out_f:
                merger.write(out_f)

            # Process merged PDF using existing pipeline
            self.process_pdf(merged_path, output_path)

        finally:
            # Cleanup merged temp file
            try:
                if 'merged_path' in locals() and os.path.exists(merged_path):
                    os.remove(merged_path)
            except Exception:
                pass

    def process_pdf(self, input_path, output_path):
        """Process PDF and create A4 layout with 2x2 grid"""
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
                    
                    # Convert to image using pdf2image
                    try:
                        images = convert_from_path(temp_path, dpi=300, first_page=1, last_page=1)
                        
                        if images:
                            # Get the first (and only) image
                            img = images[0]
                            
                            # Convert PIL image to bytes
                            img_buffer = io.BytesIO()
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
                            print(f"    Successfully placed page {page_num + 1}")
                        else:
                            # Fallback: draw placeholder if image conversion fails
                            self._draw_placeholder(canvas, x, y, page_num)
                            
                    except Exception as img_error:
                        print(f"Image conversion error for page {page_num}: {img_error}")
                        # Fallback: draw placeholder
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

