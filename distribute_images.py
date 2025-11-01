#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diğer görseller sütunundaki virgülle ayrılmış linkleri Image 1-5 sütunlarına dağıtan script
"""

import pandas as pd

# Ayarlar
EXCEL_FILE = 'Technopolis_Tum_Urunler_20250917_164841_Brands_Translated_NoDuplicates (1).xlsx'

def main():
    print("Excel dosyası okunuyor...")
    df = pd.read_excel(EXCEL_FILE)
    
    # Gerekli sütunları kontrol et
    other_images_col = 'Diğer görseller'
    
    if other_images_col not in df.columns:
        print(f"Hata: '{other_images_col}' sütunu bulunamadı!")
        print(f"Mevcut sütunlar: {df.columns.tolist()}")
        return
    
    # Image 1-5 sütunlarını ekle (eğer yoksa)
    for i in range(1, 6):
        image_col = f'Image {i}'
        if image_col not in df.columns:
            df[image_col] = ''
    
    # "Diğer görseller" sütunundaki verileri işle
    print(f"\n'{other_images_col}' sütunundaki veriler işleniyor...")
    processed_count = 0
    total_images = 0
    
    for index, row in df.iterrows():
        other_images_str = row.get(other_images_col, '')
        
        # Boş değerleri atla
        if pd.isna(other_images_str) or not str(other_images_str).strip():
            continue
        
        # Virgülle ayrılmış linkleri parse et
        image_urls = [url.strip() for url in str(other_images_str).split(',') if url.strip()]
        
        if len(image_urls) > 0:
            # İlk 5 görseli Image 1-5 sütunlarına dağıt
            for i, img_url in enumerate(image_urls[:5], 1):
                df.at[index, f'Image {i}'] = img_url
                total_images += 1
            
            processed_count += 1
            
            if processed_count % 100 == 0:
                print(f"  İşlenen satır: {processed_count}...")
    
    # Excel dosyasını güncelle
    print(f"\n✅ {processed_count} satırdaki görseller işlendi")
    print(f"✅ Toplam {total_images} görsel Image 1-5 sütunlarına dağıtıldı")
    
    print("\nExcel dosyası güncelleniyor...")
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Excel dosyası güncellendi: {EXCEL_FILE}")
    
    # Özet
    print("\n" + "="*60)
    print("ÖZET")
    print("="*60)
    print(f"İşlenen satır sayısı: {processed_count}")
    print(f"Toplam görsel sayısı: {total_images}")
    print(f"Ortalama görsel/satır: {total_images/processed_count if processed_count > 0 else 0:.2f}")

if __name__ == '__main__':
    main()

