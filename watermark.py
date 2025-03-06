import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
import math
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

def get_default_font():
    try:
        # Try system fonts first
        system_fonts = [
            "arial.ttf",
            "Arial.ttf",
            "DejaVuSans.ttf",
            "calibri.ttf",
            "Calibri.ttf"
        ]
        for font in system_fonts:
            try:
                return ImageFont.truetype(font, 36)
            except:
                continue
        
        # Fallback to default
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

async def add_image_watermark(image_path, watermark_text):
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Convert to RGBA to support transparency
            img = img.convert('RGBA')
            
            # Create a temporary file path
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f'watermarked_{os.path.basename(image_path)}')
            
            # Create watermark layer
            txt = Image.new('RGBA', img.size, (255, 255, 255, 0))
            font = get_default_font()
            
            # Calculate text size and angle
            draw = ImageDraw.Draw(txt)
            text_width = draw.textlength(watermark_text, font=font)
            text_height = font.size
            
            # Calculate diagonal placement
            angle = math.atan2(img.size[1], img.size[0])
            diagonal_length = math.sqrt(img.size[0]**2 + img.size[1]**2)
            
            # Calculate number of repetitions
            spacing = diagonal_length / 3  # Show watermark roughly 3 times across diagonal
            num_repeats = int(diagonal_length / spacing)
            
            # Rotate and place watermark multiple times
            txt = txt.rotate(math.degrees(angle), expand=True)
            draw = ImageDraw.Draw(txt)
            
            for i in range(num_repeats):
                position = (i * spacing - text_width/2, -text_height/2)
                draw.text(position, watermark_text, fill=(128, 128, 128, 128), font=font)
            
            # Rotate back and resize
            txt = txt.rotate(-math.degrees(angle), expand=True)
            txt = txt.resize(img.size)
            
            # Composite the watermark with the image
            watermarked = Image.alpha_composite(img, txt)
            watermarked = watermarked.convert('RGB')
            
            # Save the watermarked image
            watermarked.save(output_path, quality=95)
            return output_path
            
    except Exception as e:
        print(f"Error adding image watermark: {e}")
        return None

async def add_pdf_watermark(pdf_path, watermark_text):
    try:
        # Create temporary files
        temp_dir = tempfile.gettempdir()
        watermark_pdf = os.path.join(temp_dir, 'watermark.pdf')
        output_path = os.path.join(temp_dir, f'watermarked_{os.path.basename(pdf_path)}')
        
        # Create watermark PDF
        c = canvas.Canvas(watermark_pdf, pagesize=letter)
        width, height = letter
        
        # Set transparency and rotation
        c.setFillColorRGB(0.5, 0.5, 0.5, 0.3)  # Gray with 30% opacity
        c.translate(width/2, height/2)
        c.rotate(45)
        
        # Add watermark text
        c.setFont("Helvetica", 36)
        text_width = c.stringWidth(watermark_text, "Helvetica", 36)
        x = -text_width/2
        y = -18  # Half of font size
        
        # Draw watermark multiple times
        for i in range(-2, 3):
            for j in range(-2, 3):
                c.drawString(x + i*200, y + j*200, watermark_text)
        
        c.save()
        
        # Apply watermark to PDF
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            writer = PdfWriter()
            
            # Get watermark page
            with open(watermark_pdf, 'rb') as watermark_file:
                watermark = PdfReader(watermark_file)
                watermark_page = watermark.pages[0]
                
                # Apply to each page
                for page in reader.pages:
                    page.merge_page(watermark_page)
                    writer.add_page(page)
            
            # Save result
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        
        # Clean up temporary watermark file
        os.remove(watermark_pdf)
        return output_path
        
    except Exception as e:
        print(f"Error adding PDF watermark: {e}")
        return None
