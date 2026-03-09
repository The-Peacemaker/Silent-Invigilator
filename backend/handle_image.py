import sys
try:
    from PIL import Image
    import os

    source = r"C:\Users\bened\.gemini\antigravity\brain\3b500057-4211-4e57-a8bb-c2052503e9bf\silent_invigilator_logo_1772885247667.png"
    dest_ico = r"c:\Users\bened\Documents\MINI-PROJECT\silent-invigilator\static\favicon.ico"
    dest_png = r"c:\Users\bened\Documents\MINI-PROJECT\silent-invigilator\static\logo.png"

    img = Image.open(source)
    img_rgba = img.convert("RGBA")
    
    # Save as PNG
    img_rgba.save(dest_png)
    
    # Save as ICO
    img_rgba.save(dest_ico, format='ICO')
    print("Success")
except Exception as e:
    print("Error:", e)
