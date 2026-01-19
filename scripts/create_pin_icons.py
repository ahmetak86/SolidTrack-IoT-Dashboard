import os
from PIL import Image, ImageDraw, ImageOps

# --- AYARLAR ---
ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "icons")

# Renkler
SOLIDUS_YELLOW = "#f1c232"
HKM_BLUE = "#225d97"

# Boyutlar
PIN_SIZE = (64, 86)       # Pinin Dış Boyutu
INNER_ICON_SIZE = (55, 55) # İçeri Girecek Mavi İkon (Biraz nefes payı bıraktım, 50 çok sıkışabilir)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_pin_shape(size, color_rgb):
    """Sarı damla (pin) şeklini çizer"""
    W, H = size
    # Dairenin yarıçapı
    R = W // 2 
    
    # Şeffaf tuval
    pin_img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(pin_img)
    
   # GÜVENLİK PAYI (PADDING): 
    # Kenarlardan 1 piksel içeriden çiz ki kesilmesin.
    pad = 1 
    
    # 1. Alttaki Üçgen (Sivri Uç)
    # Üçgeni de daraltıyoruz
    triangle_coords = [
        (4 + pad, R),          
        (W - 4 - pad, R),      
        (R, H - pad)           
    ]
    draw.polygon(triangle_coords, fill=color_rgb)

    # 2. Üstteki Daire (Kenarlardan 1px içeride)
    draw.ellipse((pad, pad, W - pad, W - pad), fill=color_rgb)
    
    return pin_img

def create_pin_icons():
    print(f"📍 Modern Pin İkonları Oluşturuluyor...")
    print(f"📂 Hedef Klasör: {ICONS_DIR}")
    
    if not os.path.exists(ICONS_DIR):
        print("❌ HATA: İkon klasörü bulunamadı!")
        return

    yellow_rgb = hex_to_rgb(SOLIDUS_YELLOW)
    count = 0

    for filename in os.listdir(ICONS_DIR):
        # Sadece PNG'leri al, ama zaten pin olmuşları tekrar işleme! (Dosya adına bakarak koruma)
        if filename.lower().endswith(".png") and not filename.startswith("marker-"):
            
            file_path = os.path.join(ICONS_DIR, filename)
            
            try:
                # Resmi aç
                inner_icon = Image.open(file_path).convert("RGBA")
                
                # --- KORUMA MEKANİZMASI ---
                # Eğer resim zaten 64x86 ise muhtemelen işlenmiştir, atla!
                if inner_icon.size == PIN_SIZE:
                    print(f"   ⚠️ Zaten işlenmiş görünüyor, atlanıyor: {filename}")
                    continue
                # --------------------------

                # 1. Mavi İkonu Boyutlandır
                inner_icon = inner_icon.resize(INNER_ICON_SIZE, Image.Resampling.LANCZOS)
                
                # 2. Sarı Pin Şeklini Oluştur
                pin_base = create_pin_shape(PIN_SIZE, yellow_rgb)
                
                # 3. Mavi İkonu Ortala
                # Daire 64x64, İkon 44x44. 
                # (64-44)/2 = 10px kenar boşluğu kalır.
                paste_x = (PIN_SIZE[0] - INNER_ICON_SIZE[0]) // 2
                paste_y = (PIN_SIZE[0] - INNER_ICON_SIZE[1]) // 2 
                
                # Yapıştır
                pin_base.paste(inner_icon, (paste_x, paste_y), mask=inner_icon)
                
                # 4. Kaydet
                pin_base.save(file_path, "PNG")
                print(f"   ✅ Pin'e Dönüştürüldü: {filename}")
                count += 1

            except Exception as e:
                print(f"   ❌ Hata ({filename}): {e}")

    print(f"🎉 Toplam {count} ikon başarıyla dönüştürüldü.")

if __name__ == "__main__":
    create_pin_icons()