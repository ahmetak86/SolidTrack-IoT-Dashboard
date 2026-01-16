# backend/paint_icons.py
from PIL import Image
import os

def paint_icons_red():
    # Dosya: backend/paint_icons.py
    # 1. backend klasörü
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    # 2. ROOT klasörü (backend'in bir üstü)
    root_dir = os.path.dirname(backend_dir)
    
    # Hedef: ROOT/static/icons
    icons_dir = os.path.join(root_dir, 'static', 'icons')
    
    # HEDEF RENK: PARLAK KIRMIZI (RGB)
    TARGET_COLOR = (231, 76, 60) # #E74C3C
    
    print(f"🎨 İkon Boyama İşlemi Başlıyor...")
    print(f"📂 Hedef Klasör: {icons_dir}")

    if not os.path.exists(icons_dir):
        print("❌ HATA: İkon klasörü bulunamadı!")
        print(f"   Aranan yol: {icons_dir}")
        return

    files = [f for f in os.listdir(icons_dir) if f.lower().endswith('.png')]
    
    if not files:
        print("❌ Klasör boş veya png dosyası yok.")
        return

    count = 0
    for filename in files:
        filepath = os.path.join(icons_dir, filename)
        try:
            img = Image.open(filepath).convert("RGBA")
            r, g, b, alpha = img.split()
            
            # Yeni Kırmızı Zemin
            colored_bg = Image.new("RGB", img.size, TARGET_COLOR)
            # Eski şeffaflığı maske olarak kullan
            colored_bg.putalpha(alpha)
            
            colored_bg.save(filepath)
            print(f"✅ Boyandı: {filename}")
            count += 1
        except Exception as e:
            print(f"⚠️ Hata ({filename}): {e}")

    print(f"\n🎉 Tamamlandı! {count} ikon kırmızıya boyandı.")

if __name__ == "__main__":
    # PIL yüklü değilse uyarı ver
    try:
        paint_icons_red()
    except ImportError:
        print("❌ HATA: 'Pillow' kütüphanesi eksik.")
        print("👉 Lütfen şunu çalıştır: pip install Pillow")