#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tüm ürün fiyatlarına 1000 TL ekleyen script
"""

import pandas as pd

# Ayarlar
EXCEL_FILE = 'Technopolis_Tum_Urunler_20250917_164841_Brands_Translated_NoDuplicates (1).xlsx'
PRICE_INCREMENT = 1000  # Eklenecek tutar (TL)

def main():
    print("Excel dosyası okunuyor...")
    df = pd.read_excel(EXCEL_FILE)
    
    # Price sütununu kontrol et
    price_col = 'Price'
    
    if price_col not in df.columns:
        print(f"Hata: '{price_col}' sütunu bulunamadı!")
        print(f"Mevcut sütunlar: {df.columns.tolist()}")
        return
    
    # Fiyat istatistikleri
    before_prices = df[price_col].dropna()
    
    if len(before_prices) == 0:
        print("⚠️  Fiyat verisi bulunamadı!")
        return
    
    print(f"\nİşlem öncesi istatistikler:")
    print(f"  Toplam ürün sayısı: {len(df)}")
    print(f"  Fiyatı olan ürün sayısı: {len(before_prices)}")
    print(f"  Minimum fiyat: {before_prices.min():.2f} TL")
    print(f"  Maximum fiyat: {before_prices.max():.2f} TL")
    print(f"  Ortalama fiyat: {before_prices.mean():.2f} TL")
    
    # Fiyatlara 1000 TL ekle (sadece sayısal olanları)
    df[price_col] = df[price_col].apply(lambda x: x + PRICE_INCREMENT if pd.notna(x) and isinstance(x, (int, float)) else x)
    
    # İşlem sonrası istatistikler
    after_prices = df[price_col].dropna()
    
    print(f"\nİşlem sonrası istatistikler:")
    print(f"  Minimum fiyat: {after_prices.min():.2f} TL")
    print(f"  Maximum fiyat: {after_prices.max():.2f} TL")
    print(f"  Ortalama fiyat: {after_prices.mean():.2f} TL")
    
    # Örnek göster (ilk 5 ürün)
    print(f"\nİlk 5 ürünün yeni fiyatları:")
    for idx, row in df.head(5).iterrows():
        product_name = str(row.get('Product Name', 'N/A'))[:50]
        price = row[price_col]
        if pd.notna(price):
            print(f"  {product_name}... : {price:.2f} TL")
    
    # Excel dosyasını güncelle
    print(f"\n💾 Excel dosyası güncelleniyor...")
    df.to_excel(EXCEL_FILE, index=False)
    print(f"✅ Tüm fiyatlara {PRICE_INCREMENT} TL eklendi!")
    print(f"✅ Excel dosyası güncellendi: {EXCEL_FILE}")

if __name__ == '__main__':
    main()

