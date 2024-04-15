
import os
from fpdf import FPDF


class PdfCreator:
    def __init__(self, pdf_path):
        self.export_path = pdf_path
        self.pdf = FPDF()
        self.content = []
        
    def append_image(self, image_path):
        self.pdf.add_page()
        self.pdf.image(image_path)
   
    def export(self):
        self.pdf.output(self.export_path)
        return self.export_path