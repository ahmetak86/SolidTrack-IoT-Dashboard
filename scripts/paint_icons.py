import os
from PIL import Image, ImageOps

# Hedef Klasör ve Renk
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "icons")
HKM_BLUE = "#225d97"  # Hedef Renk

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def paint_icons():
    print(f"🎨 İkon Boyama İşlemi Başlıyor... Hedef: {HKM_BLUE}")
    print(f"📂 Klasör: {ICONS_DIR}")

    if not os.path.exists(ICONS_DIR):
        print("❌ HATA: İkon klasörü bulunamadı!")
        return

    rgb_color = hex_to_rgb(HKM_BLUE)
    count = 0

    for filename in os.listdir(ICONS_DIR):
        if filename.lower().endswith(".png"):
            file_path = os.path.join(ICONS_DIR, filename)
            
            try:
                # Resmi aç ve RGBA (Şeffaf) moduna zorla
                img = Image.open(file_path).convert("RGBA")
                
                # Yeni boş bir resim yarat (Aynı boyutta, tamamen HKM Mavisi)
                blue_bg = Image.new("RGBA", img.size, rgb_color + (255,))
                
                # Orijinal resmin şeffaflık (Alpha) kanalını maske olarak kullan
                # Siyah olan yerleri Mavi yap, şeffaf yerleri şeffaf bırak
                final_img = Image.composite(blue_bg, Image.new("RGBA", img.size, (0,0,0,0)), img)
                
                # Üzerine kaydet
                final_img.save(file_path)
                print(f"   ✅ Boyandı: {filename}")
                count += 1
            except Exception as e:
                print(f"   ❌ Hata ({filename}): {e}")

    print(f"🎉 Toplam {count} ikon başarıyla HKM Mavisine boyandı.")

if __name__ == "__main__":
    paint_icons()