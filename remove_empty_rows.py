#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diğer görseller sütunu boş olan satırları silen script
"""

import pandas as pd

# Ayarlar
EXCEL_FILE = 'Technopolis_Tum_Urunler_20250917_164841_Brands_Translated_NoDuplicates (1).xlsx'

def main():
    print("Excel dosyası okunuyor...")
    df = pd.read_excel(EXCEL_FILE)
    
    original_count = len(df)
    print(f"Orijinal satır sayısı: {original_count}")
    
    # "Diğer görseller" sütununu kontrol et
    other_images_col = 'Diğer görseller'
    
    if other_images_col not in df.columns:
        print(f"Hata: '{other_images_col}' sütunu bulunamadı!")
        print(f"Mevcut sütunlar: {df.columns.tolist()}")
        return
    
    # Boş olan satırları bul (NaN, boş string, sadece boşluk)
    before_count = len(df)
    
    # Boş olanları filtrele
    df_filtered = df[
        df[other_images_col].notna() & 
        (df[other_images_col].astype(str).str.strip() != '') &
        (df[other_images_col].astype(str).str.strip() != 'nan')
    ].copy()
    
    removed_count = before_count - len(df_filtered)
    
    print(f"Silinen satır sayısı: {removed_count}")
    print(f"Kalan satır sayısı: {len(df_filtered)}")
    
    if removed_count > 0:
        # Excel dosyasını güncelle
        print("\nExcel dosyası güncelleniyor...")
        df_filtered.to_excel(EXCEL_FILE, index=False)
        print(f"✅ Excel dosyası güncellendi: {EXCEL_FILE}")
        print(f"✅ {removed_count} satır silindi, {len(df_filtered)} satır kaldı")
    else:
        print("\n⚠️  Silinecek boş satır bulunamadı.")

if __name__ == '__main__':
    main()

